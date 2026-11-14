"""Core pipeline: store a reading, score it, open alerts, compute fire danger."""

import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alerts import dispatch
from app.config import settings
from app.events import bus
from app.db import Alert, Hotspot, Node, Reading
from app.risk.detect import haversine_km, score_reading
from app.risk.fma import daily_observations, danger_class, fma_plus
from app.sites import site_timezone
from app.schemas import Telemetry

HISTORY_SIZE = 12
KM_PER_DEG = 111.0


def nearest_hotspot_km(db: Session, lat: float, lon: float, now: datetime) -> float | None:
    since = now - timedelta(hours=settings.hotspot_window_hours)
    d = settings.hotspot_radius_km / KM_PER_DEG * 2  # coarse pre-filter box
    q = select(Hotspot.lat, Hotspot.lon).where(
        Hotspot.ts >= since,
        Hotspot.lat.between(lat - d, lat + d),
        Hotspot.lon.between(lon - d, lon + d),
    )
    dists = [haversine_km(lat, lon, hl, hn) for hl, hn in db.execute(q)]
    return min(dists) if dists else None


def _as_utc(ts: datetime) -> datetime:
    return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)


async def process(db: Session, t: Telemetry) -> tuple[Reading, Alert | None]:
    now = _as_utc(t.ts) if t.ts else datetime.now(timezone.utc)

    node = db.get(Node, t.node_id)
    if node is None:
        node = Node(id=t.node_id, lat=t.lat, lon=t.lon)
        db.add(node)
    node.lat, node.lon, node.last_seen = t.lat, t.lon, now
    if t.battery_v is not None:
        node.battery_v = t.battery_v

    prev = db.scalars(
        select(Reading).where(Reading.node_id == t.node_id).order_by(Reading.ts.desc()).limit(HISTORY_SIZE)
    ).all()
    history = [(r.temp_c, r.humidity_pct, r.smoke_ppm) for r in reversed(prev)]

    det = score_reading(
        temp_c=t.temp_c,
        humidity_pct=t.humidity_pct,
        smoke_ppm=t.smoke_ppm,
        flame=t.flame,
        history=history,
        nearest_hotspot_km=nearest_hotspot_km(db, t.lat, t.lon, now),
        hotspot_radius_km=settings.hotspot_radius_km,
    )

    reading = Reading(
        node_id=t.node_id, ts=now, temp_c=t.temp_c, humidity_pct=t.humidity_pct,
        smoke_ppm=t.smoke_ppm, flame=t.flame, wind_ms=t.wind_ms, rain_mm=t.rain_mm, score=det.score,
    )
    db.add(reading)

    db.commit()

    bus.publish("reading", {"node_id": t.node_id, "score": det.score})

    alert = None
    if det.score >= settings.detection_threshold:
        msg = (
            f"🔥 Possível incêndio no nó {t.node_id} ({t.lat:.4f}, {t.lon:.4f}) - "
            f"score {det.score:.2f}: " + "; ".join(det.reasons)
        )
        alert = await raise_alert(db, t.node_id, "fire", det.score, msg, now, settings.alert_cooldown_minutes)
    return reading, alert


def _in_cooldown(db: Session, node_id: str, kind: str, now: datetime, minutes: int) -> bool:
    since = now - timedelta(minutes=minutes)
    return db.scalar(
        select(Alert.id).where(Alert.node_id == node_id, Alert.kind == kind, Alert.ts >= since).limit(1)
    ) is not None


async def raise_alert(
    db: Session, node_id: str, kind: str, score: float, message: str, now: datetime, cooldown_minutes: int
) -> Alert | None:
    """Store and deliver an alert unless one of the same kind for this node is still in cooldown."""
    if _in_cooldown(db, node_id, kind, now, cooldown_minutes):
        return None
    alert = Alert(node_id=node_id, ts=now, kind=kind, score=score, message=message)
    db.add(alert)
    db.commit()
    bus.publish("alert", {"id": alert.id, "node_id": node_id, "kind": kind, "message": message})
    alert.delivered = await dispatch.send_alert(node_id, kind, message, score)
    db.commit()
    return alert


async def check_hotspots_near_nodes(db: Session, now: datetime | None = None) -> list[Alert]:
    """Alert when recent INPE hotspots fall inside a node's/site's radius."""
    now = now or datetime.now(timezone.utc)
    alerts = []
    for node in db.scalars(select(Node)).all():
        radius = node.radius_km or settings.hotspot_radius_km
        since = now - timedelta(hours=settings.hotspot_window_hours)
        d_lat = radius / KM_PER_DEG
        d_lon = d_lat / max(math.cos(math.radians(node.lat)), 0.1)
        rows = db.execute(select(Hotspot.lat, Hotspot.lon).where(
            Hotspot.ts >= since,
            Hotspot.lat.between(node.lat - d_lat, node.lat + d_lat),
            Hotspot.lon.between(node.lon - d_lon, node.lon + d_lon),
        )).all()
        dists = [d for d in (haversine_km(node.lat, node.lon, la, lo) for la, lo in rows) if d <= radius]
        if not dists:
            continue
        label = node.name or node.id
        msg = (f"🛰️ {len(dists)} foco(s) de calor INPE a até {radius:.0f} km de {label} - "
               f"mais próximo a {min(dists):.1f} km (últimas {settings.hotspot_window_hours} h)")
        score = min(1.0, 0.5 + 0.1 * len(dists))
        a = await raise_alert(db, node.id, "hotspot", score, msg, now, settings.hotspot_alert_cooldown_minutes)
        if a:
            alerts.append(a)
    return alerts


async def check_danger(db: Session, node: Node, now: datetime | None = None) -> Alert | None:
    """At most one alert a day per node when FMA+ is alta or muito alta."""
    now = now or datetime.now(timezone.utc)
    value, cls, n = node_danger(db, node.id)
    if cls not in ("alta", "muito_alta") or n < 3:
        return None
    label = node.name or node.id
    msg = f"⚠️ Risco de incêndio {cls.replace('_', ' ').upper()} em {label}: FMA+ {value:.1f} ({n} dias de dados)"
    return await raise_alert(db, node.id, "danger", min(1.0, value / 24), msg, now, 20 * 60)


def node_danger(db: Session, node_id: str, days: int = 30) -> tuple[float, str, int]:
    """FMA+ from the node's own readings: the reading closest to 13h local time, plus daily rain."""
    tz = ZoneInfo(site_timezone(node_id))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(Reading.ts, Reading.humidity_pct, Reading.wind_ms, Reading.rain_mm)
        .where(Reading.node_id == node_id, Reading.ts >= since).order_by(Reading.ts)
    ).all()
    obs = [o for _, o in daily_observations(((_as_utc(ts), rh, w, r) for ts, rh, w, r in rows), tz)]
    value = fma_plus(obs)
    return value, danger_class(value), len(obs)
