"""INPE BDQueimadas 10-minute hotspot feed.

Directory listing: {base}/focos_10min_YYYYMMDD_HHMM.csv
CSV columns: lat,lon,satelite,data   (data = 'YYYY-MM-DD HH:MM:SS', UTC)
"""

import asyncio
import csv
import io
import logging
import re
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import service
from app.config import settings
from app.events import bus
from app.db import Hotspot, SessionLocal, upsert_ignore
from app.geo import boundaries_available, locate_uf

log = logging.getLogger(__name__)
FILE_RE = re.compile(r"focos_10min_(\d{8})_(\d{4})\.csv")


def latest_files(listing_html: str, n: int = 1) -> list[str]:
    names = sorted(set(m.group(0) for m in FILE_RE.finditer(listing_html)))
    return names[-n:]


def parse_csv(text: str, bbox=settings.bbox) -> list[dict]:
    lat_min, lat_max, lon_min, lon_max = bbox
    use_borders = boundaries_available()
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            lat, lon = float(row["lat"]), float(row["lon"])
            ts = datetime.strptime(row["data"].strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except (KeyError, ValueError):
            continue
        if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
            continue
        uf = locate_uf(lat, lon)
        if uf is None and use_borders:
            continue  # outside Brazil (IBGE boundaries)
        rows.append({"lat": lat, "lon": lon, "satellite": row["satelite"].strip(), "ts": ts, "uf": uf})
    return rows


def tag_existing(db: Session) -> tuple[int, int]:
    """Give stored hotspots without a state their UF, and delete those outside Brazil. Returns (tagged, deleted)."""
    if not boundaries_available():
        return 0, 0
    tagged = deleted = 0
    for h in db.scalars(select(Hotspot).where(Hotspot.uf.is_(None))).all():
        uf = locate_uf(h.lat, h.lon)
        if uf is None:
            db.delete(h)
            deleted += 1
        else:
            h.uf = uf
            tagged += 1
    db.commit()
    return tagged, deleted


def store(db: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    stmt = upsert_ignore(db, Hotspot, rows)
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0


async def fetch_latest(client: httpx.AsyncClient, n: int = 1) -> list[dict]:
    base = settings.inpe_base_url
    listing = await client.get(base)
    listing.raise_for_status()
    rows: list[dict] = []
    for name in latest_files(listing.text, n):
        resp = await client.get(base + name)
        resp.raise_for_status()
        rows.extend(parse_csv(resp.text))
    return rows


async def poll_once(client: httpx.AsyncClient, n: int) -> int:
    rows = await fetch_latest(client, n=n)
    with SessionLocal() as db:
        added = store(db, rows)
        if added:
            await service.check_hotspots_near_nodes(db)
            bus.publish("refresh", {"source": "inpe", "new": added})
    log.info("INPE: %d hotspots fetched, %d new", len(rows), added)
    return added


async def poll_forever() -> None:
    first = True
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            try:
                # Load the last hour on startup, then the two newest files per cycle.
                await poll_once(client, n=6 if first else 2)
                first = False
            except Exception:
                log.exception("INPE poll failed")
            await asyncio.sleep(settings.inpe_poll_seconds)
