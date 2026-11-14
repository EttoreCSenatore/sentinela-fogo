"""INPE Risco de Fogo (RF) per site: observed (daily NetCDF) and forecast for today + 3 days (GeoTIFF).

Both are 0.01° grids over South America with `rf` in 0..1 (-999 = no data):
  observed: .../riscofogo_meteorologia/observado/risco_fogo/INPE_FireRiskModel_<v>_FireRisk_YYYYMMDD.nc
  forecast: .../riscofogo_meteorologia/previsto/risco_fogo/RF.PREV.T0..T3.tif (overwritten every morning)
Classes (INPE): Mínimo < 0.15, Baixo 0.15-0.4, Médio 0.4-0.7, Alto 0.7-0.95, Crítico > 0.95.

Files are streamed to a temp dir, only the tiles/rows around each site are read, and the file is deleted.
Per site we keep the mean and max RF inside the site's radius.
"""

import asyncio
import logging
import math
import re
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Node, SessionLocal, SiteRisk
from app.events import bus

log = logging.getLogger(__name__)

BASE = "https://dataserver-coids.inpe.br/queimadas/queimadas/riscofogo_meteorologia/"
OBS_URL = BASE + "observado/risco_fogo/"
FCST_URL = BASE + "previsto/risco_fogo/"
OBS_FILE_RE = re.compile(r"INPE_FireRiskModel_[\d.]+_FireRisk_(\d{8})\.nc")
FCST_VALID_RE = re.compile(r"(?:hours|days) since (\d{4}-\d{2}-\d{2})")
FORECAST_LEADS = range(0, 4)  # T0 (today) .. T3

RF_CLASSES = ["minimo", "baixo", "medio", "alto", "critico"]
RF_LIMITS = [0.15, 0.4, 0.7, 0.95]
RF_LABEL = {"minimo": "Mínimo", "baixo": "Baixo", "medio": "Médio", "alto": "Alto", "critico": "Crítico"}


def rf_class(v: float) -> str:
    for limit, name in zip(RF_LIMITS, RF_CLASSES):
        if v < limit:
            return name
    return RF_CLASSES[-1]


@dataclass
class Sample:
    rf_center: float
    rf_mean: float
    rf_max: float


# ---------------------------------------------------------------- sampling helpers

def _site_window(site: dict) -> tuple[float, float, float, float]:
    r = site.get("radius_km") or settings.hotspot_radius_km
    dlat = r / 111.0
    dlon = dlat / max(math.cos(math.radians(site["lat"])), 0.1)
    return site["lat"] - dlat, site["lat"] + dlat, site["lon"] - dlon, site["lon"] + dlon


def _stats(block, lats, lons, site: dict) -> Sample | None:
    """Mean/max of valid cells within the site's radius; `block` is indexed [lat, lon]."""
    import numpy as np

    r = site.get("radius_km") or settings.hotspot_radius_km
    vals = np.ma.masked_invalid(np.asarray(block, dtype="f8"))
    vals = np.ma.masked_less(vals, 0)  # -999 = no data
    yy, xx = np.meshgrid(lats, lons, indexing="ij")
    dist = np.hypot((yy - site["lat"]) * 111.0, (xx - site["lon"]) * 111.0 * math.cos(math.radians(site["lat"])))
    inside = np.ma.masked_where(dist > r, vals)
    if inside.count() == 0:
        return None
    cy, cx = np.unravel_index(np.argmin(dist), dist.shape)
    c = vals[cy, cx]
    center = float("nan") if np.ma.is_masked(c) else float(c)
    return Sample(center, float(inside.mean()), float(inside.max()))


def sample_netcdf(path: Path, sites: list[dict]) -> dict[str, Sample]:
    import netCDF4
    import numpy as np

    out = {}
    with netCDF4.Dataset(path) as ds:
        lats, lons = np.asarray(ds["lat"][:]), np.asarray(ds["lon"][:])
        for s in sites:
            la0, la1, lo0, lo1 = _site_window(s)
            iy = np.where((lats >= la0) & (lats <= la1))[0]
            ix = np.where((lons >= lo0) & (lons <= lo1))[0]
            if len(iy) == 0 or len(ix) == 0:
                continue
            y0, y1, x0, x1 = iy.min(), iy.max() + 1, ix.min(), ix.max() + 1
            block = np.ma.filled(ds["rf"][0, y0:y1, x0:x1].astype("f8"), np.nan)
            st = _stats(block, lats[y0:y1], lons[x0:x1], s)
            if st:
                out[s["id"]] = st
    return out


def _read_tiff_window(tf, page, y0: int, y1: int, x0: int, x1: int):
    """Decode only the tiles that overlap rows y0:y1 and columns x0:x1 of a tiled TIFF page."""
    import numpy as np

    th, tw = page.tilelength, page.tilewidth
    tiles_across = math.ceil(page.imagewidth / tw)
    out = np.full((y1 - y0, x1 - x0), np.nan)
    fh = tf.filehandle
    for ty in range(y0 // th, (y1 - 1) // th + 1):
        for tx in range(x0 // tw, (x1 - 1) // tw + 1):
            idx = ty * tiles_across + tx
            fh.seek(page.dataoffsets[idx])
            data, _, _ = page.decode(fh.read(page.databytecounts[idx]), idx)
            tile = np.asarray(data).reshape(th, tw)
            ty0, tx0 = ty * th, tx * tw
            sy0, sy1 = max(y0, ty0), min(y1, ty0 + th)
            sx0, sx1 = max(x0, tx0), min(x1, tx0 + tw)
            out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = tile[sy0 - ty0:sy1 - ty0, sx0 - tx0:sx1 - tx0]
    return out


def tiff_valid_date(path: Path) -> date | None:
    """Forecast date from the GDAL metadata ("hours since 2026-11-15 18:00:00")."""
    import tifffile

    with tifffile.TiffFile(path) as tf:
        tag = tf.pages[0].tags.get(42112)
        m = FCST_VALID_RE.search(tag.value if tag else "")
    return date.fromisoformat(m.group(1)) if m else None


def sample_geotiff(path: Path, sites: list[dict]) -> dict[str, Sample]:
    import numpy as np
    import tifffile

    out = {}
    with tifffile.TiffFile(path) as tf:
        page = tf.pages[0]
        sx, sy = page.tags[33550].value[:2]          # ModelPixelScale
        lon0, lat0 = page.tags[33922].value[3:5]     # ModelTiepoint: top-left corner
        h, w = page.imagelength, page.imagewidth
        for s in sites:
            la0, la1, lo0, lo1 = _site_window(s)
            y0, y1 = max(0, int((lat0 - la1) / sy)), min(h, int(math.ceil((lat0 - la0) / sy)))
            x0, x1 = max(0, int((lo0 - lon0) / sx)), min(w, int(math.ceil((lo1 - lon0) / sx)))
            if y0 >= y1 or x0 >= x1:
                continue
            block = _read_tiff_window(tf, page, y0, y1, x0, x1)
            lats = lat0 - (np.arange(y0, y1) + 0.5) * sy   # pixel centres
            lons = lon0 + (np.arange(x0, x1) + 0.5) * sx
            st = _stats(block, lats, lons, s)
            if st:
                out[s["id"]] = st
    return out


# ---------------------------------------------------------------- download + store

async def _download(client: httpx.AsyncClient, url: str, dest: Path) -> None:
    async with client.stream("GET", url) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            async for chunk in r.aiter_bytes(1 << 20):
                f.write(chunk)


def store(db: Session, kind: str, valid: date, issued: date, samples: dict[str, Sample]) -> int:
    """Upsert one row per site for (kind, valid date); a newer forecast replaces an older one."""
    n = 0
    for node_id, s in samples.items():
        row = db.scalar(select(SiteRisk).where(
            SiteRisk.node_id == node_id, SiteRisk.kind == kind, SiteRisk.valid_date == valid))
        if row is None:
            row = SiteRisk(node_id=node_id, kind=kind, valid_date=valid)
            db.add(row)
        elif kind == "forecast" and row.issued_date and row.issued_date > issued:
            continue
        row.issued_date, row.rf_mean, row.rf_max = issued, s.rf_mean, s.rf_max
        row.fetched_at = datetime.now(timezone.utc)
        n += 1
    db.commit()
    return n


def _site_dicts(db: Session) -> list[dict]:
    return [{"id": n.id, "lat": n.lat, "lon": n.lon, "radius_km": n.radius_km}
            for n in db.scalars(select(Node).where(Node.kind == "virtual")).all()]


async def poll_observed(client: httpx.AsyncClient) -> int:
    """Sample the newest observed grid if we don't have it yet."""
    listing = await client.get(OBS_URL)
    listing.raise_for_status()
    files = sorted({m.group(1): m.group(0) for m in OBS_FILE_RE.finditer(listing.text)}.items())
    if not files:
        return 0
    day_s, name = files[-1]
    valid = datetime.strptime(day_s, "%Y%m%d").date()
    with SessionLocal() as db:
        sites = _site_dicts(db)
        have = {r for r in db.scalars(select(SiteRisk.node_id).where(
            SiteRisk.kind == "observed", SiteRisk.valid_date == valid))}
    if not sites or all(s["id"] in have for s in sites):
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        await _download(client, OBS_URL + name, path)
        samples = await asyncio.to_thread(sample_netcdf, path, sites)
    with SessionLocal() as db:
        return store(db, "observed", valid, valid, samples)


async def poll_forecast(client: httpx.AsyncClient) -> int:
    """Sample T0..T3 when INPE has published a new forecast run (checked via Last-Modified)."""
    head = await client.head(FCST_URL + "RF.PREV.T0.tif")
    head.raise_for_status()
    modified = head.headers.get("last-modified")
    issued = (datetime.strptime(modified, "%a, %d %b %Y %H:%M:%S GMT").date()
              if modified else datetime.now(timezone.utc).date())
    with SessionLocal() as db:
        sites = _site_dicts(db)
        latest = db.scalar(select(SiteRisk.issued_date).where(SiteRisk.kind == "forecast")
                           .order_by(SiteRisk.issued_date.desc()).limit(1))
    if not sites or (latest is not None and latest >= issued):
        return 0
    total = 0
    for lead in FORECAST_LEADS:
        name = f"RF.PREV.T{lead}.tif"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / name
            await _download(client, FCST_URL + name, path)
            valid = await asyncio.to_thread(tiff_valid_date, path) or issued + timedelta(days=lead)
            samples = await asyncio.to_thread(sample_geotiff, path, sites)
        with SessionLocal() as db:
            total += store(db, "forecast", valid, issued, samples)
    return total


async def poll_once(client: httpx.AsyncClient) -> int:
    from app import service

    n = 0
    for poll in (poll_forecast, poll_observed):
        try:
            n += await poll(client)
        except (httpx.HTTPError, OSError, ValueError, KeyError) as e:
            log.warning("INPE risk %s failed: %s", poll.__name__, e)
    if n:
        with SessionLocal() as db:
            for node in db.scalars(select(Node).where(Node.kind == "virtual")).all():
                await service.check_danger(db, node)
        bus.publish("refresh", {"source": "inpe_risk", "new": n})
    return n


async def poll_forever() -> None:
    async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
        while True:
            n = await poll_once(client)
            if n:
                log.info("INPE risk: %d site values updated", n)
            await asyncio.sleep(settings.inpe_risk_poll_seconds)
