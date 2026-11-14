"""Virtual stations: hourly weather for each pilot site from Open-Meteo (free, no API key).

Readings are stored like a sensor node's (no smoke/flame), so FMA+ fire danger works without hardware.
Note: Open-Meteo data is model output (reanalysis + forecast models), not a ground station. Its free
tier is for non-commercial use.
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import service
from app.config import settings
from app.events import bus
from app.db import Node, Reading, SessionLocal

log = logging.getLogger(__name__)
HOURLY = "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation"


async def fetch_hourly(client: httpx.AsyncClient, lat: float, lon: float, past_days: int) -> list[dict]:
    r = await client.get(settings.weather_base_url, params={
        "latitude": lat, "longitude": lon, "hourly": HOURLY, "wind_speed_unit": "ms",
        "timezone": "UTC", "past_days": past_days, "forecast_days": 1,
    })
    r.raise_for_status()
    h = r.json()["hourly"]
    rows = []
    for i, t in enumerate(h["time"]):
        temp, rh = h["temperature_2m"][i], h["relative_humidity_2m"][i]
        if temp is None or rh is None:
            continue
        rows.append({
            "ts": datetime.fromisoformat(t).replace(tzinfo=timezone.utc),
            "temp_c": temp, "humidity_pct": rh,
            "wind_ms": h["wind_speed_10m"][i], "rain_mm": h["precipitation"][i] or 0.0,
        })
    return rows


def store_new(db: Session, node: Node, rows: list[dict], now: datetime) -> int:
    """Insert hours newer than the node's latest reading and not in the future (drops forecast hours)."""
    latest = db.scalar(select(func.max(Reading.ts)).where(Reading.node_id == node.id))
    if latest is not None and latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    new = [r for r in rows if r["ts"] <= now and (latest is None or r["ts"] > latest)]
    for r in new:
        db.add(Reading(node_id=node.id, flame=False, smoke_ppm=None, score=0.0, **r))
    if new:
        node.last_seen = new[-1]["ts"]
    db.commit()
    return len(new)


async def poll_once(client: httpx.AsyncClient, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    total = 0
    with SessionLocal() as db:
        for node in db.scalars(select(Node).where(Node.kind == "virtual")).all():
            has_data = db.scalar(select(Reading.id).where(Reading.node_id == node.id).limit(1)) is not None
            past_days = 2 if has_data else settings.weather_backfill_days
            try:
                rows = await fetch_hourly(client, node.lat, node.lon, past_days)
            except httpx.HTTPError as e:
                log.warning("weather fetch failed for %s: %s", node.id, e)
                continue
            total += store_new(db, node, rows, now)
            await service.check_danger(db, node, now)
    if total:
        bus.publish("refresh", {"source": "weather", "new": total})
    return total


async def poll_forever() -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            try:
                n = await poll_once(client)
                log.info("weather: %d new hourly readings", n)
            except Exception:
                log.exception("weather poll failed")
            await asyncio.sleep(settings.weather_poll_seconds)
