"""Compare our FMA+ with INPE's official Risco de Fogo (RF) at each pilot site.

INPE publishes one observed RF grid per day (NetCDF, ~0.005°, ~12.5 MB, variable `rf` in 0..1) at
  https://dataserver-coids.inpe.br/queimadas/queimadas/riscofogo_meteorologia/observado/risco_fogo/
RF classes (INPE, "Risco de Fogo - Sucinto"): Mínimo < 0.15, Baixo 0.15-0.4, Médio 0.4-0.7, Alto 0.7-0.95,
Crítico > 0.95. RF uses 120 days of precipitation, vegetation type, 18 UTC temperature/humidity and
topography, so it is NOT expected to equal FMA+; we compare ranks and classes.

Each grid is downloaded to a temp file, sampled inside each site's radius, and deleted; only the
small samples are cached (data/inpe_rf_samples.csv), so re-runs only fetch new days.
"""

import csv
import logging
import math
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from app.config import settings
from app.ingest.weather import fetch_hourly
from app.risk.fma import daily_observations, danger_class, fma_series

log = logging.getLogger(__name__)

RF_BASE = "https://dataserver-coids.inpe.br/queimadas/queimadas/riscofogo_meteorologia/observado/risco_fogo/"
RF_FILE_RE = re.compile(r"INPE_FireRiskModel_[\d.]+_FireRisk_(\d{8})\.nc")
CACHE = Path("data/inpe_rf_samples.csv")
CACHE_FIELDS = ["date", "site", "rf_center", "rf_mean", "rf_max"]

FMA_CLASSES = ["nula", "pequena", "media", "alta", "muito_alta"]
RF_CLASSES = ["minimo", "baixo", "medio", "alto", "critico"]
RF_LIMITS = [0.15, 0.4, 0.7, 0.95]


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


def sample_grid(path: Path, sites: list[dict]) -> dict[str, Sample]:
    """Sample the RF grid inside each site's radius (mean and max of valid cells, plus the centre cell)."""
    import netCDF4
    import numpy as np

    out = {}
    with netCDF4.Dataset(path) as ds:
        lats, lons = ds["lat"][:], ds["lon"][:]
        for s in sites:
            r = s.get("radius_km", 10)
            dlat = r / 111.0
            dlon = dlat / max(math.cos(math.radians(s["lat"])), 0.1)
            iy = np.where((lats >= s["lat"] - dlat) & (lats <= s["lat"] + dlat))[0]
            ix = np.where((lons >= s["lon"] - dlon) & (lons <= s["lon"] + dlon))[0]
            if len(iy) == 0 or len(ix) == 0:
                continue
            block = np.ma.masked_invalid(ds["rf"][0, iy.min():iy.max() + 1, ix.min():ix.max() + 1])
            block = np.ma.masked_less(block, 0)  # -999 = missing
            # keep only cells inside the circle
            yy, xx = np.meshgrid(lats[iy.min():iy.max() + 1], lons[ix.min():ix.max() + 1], indexing="ij")
            dist = np.hypot((yy - s["lat"]) * 111.0, (xx - s["lon"]) * 111.0 * math.cos(math.radians(s["lat"])))
            block = np.ma.masked_where(dist > r, block)
            if block.count() == 0:
                continue
            cy = int(np.abs(lats - s["lat"]).argmin())
            cx = int(np.abs(lons - s["lon"]).argmin())
            c = ds["rf"][0, cy, cx]
            center = float("nan") if np.ma.is_masked(c) or float(c) < 0 else float(c)
            out[s["id"]] = Sample(center, float(block.mean()), float(block.max()))
    return out


def _read_cache() -> dict[tuple[str, str], Sample]:
    if not CACHE.exists():
        return {}
    with CACHE.open() as f:
        return {(r["date"], r["site"]): Sample(float(r["rf_center"]), float(r["rf_mean"]), float(r["rf_max"]))
                for r in csv.DictReader(f)}


def _append_cache(day: date, samples: dict[str, Sample]) -> None:
    new = not CACHE.exists()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    with CACHE.open("a", newline="") as f:
        w = csv.DictWriter(f, CACHE_FIELDS)
        if new:
            w.writeheader()
        for site, s in samples.items():
            w.writerow({"date": day.isoformat(), "site": site, "rf_center": s.rf_center,
                        "rf_mean": s.rf_mean, "rf_max": s.rf_max})


def fetch_rf_samples(client: httpx.Client, days: list[date], sites: list[dict],
                     progress=print) -> dict[tuple[str, str], Sample]:
    cache = _read_cache()
    listing = client.get(RF_BASE)
    listing.raise_for_status()
    files = {m.group(1): m.group(0) for m in RF_FILE_RE.finditer(listing.text)}
    for day in days:
        key = day.strftime("%Y%m%d")
        if all((day.isoformat(), s["id"]) in cache for s in sites):
            continue
        if key not in files:
            progress(f"  {day}: no INPE grid published")
            continue
        progress(f"  {day}: downloading {files[key]} ...")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / files[key]
            with client.stream("GET", RF_BASE + files[key]) as r:
                r.raise_for_status()
                with path.open("wb") as f:
                    for chunk in r.iter_bytes(1 << 20):
                        f.write(chunk)
            samples = sample_grid(path, sites)
        _append_cache(day, samples)
        cache.update({(day.isoformat(), k): v for k, v in samples.items()})
        time.sleep(1)  # be polite to INPE's server
    return cache


async def fma_by_day(site: dict, past_days: int = 92) -> dict[date, float]:
    async with httpx.AsyncClient(timeout=60) as client:
        rows = await fetch_hourly(client, site["lat"], site["lon"], past_days)
    tz = ZoneInfo(site.get("timezone", settings.timezone))
    obs = daily_observations(((r["ts"], r["humidity_pct"], r["wind_ms"], r["rain_mm"]) for r in rows), tz)
    values = fma_series([o for _, o in obs])
    return {d: v for (d, _), v in zip(obs, values)}


def spearman(x: list[float], y: list[float]) -> float:
    """Spearman rank correlation (average ranks for ties)."""
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    if len(x) < 3:
        return float("nan")
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


@dataclass
class Row:
    site: str
    day: date
    fma: float
    fma_class: str
    rf: float
    rf_class: str

    @property
    def class_gap(self) -> int:
        return FMA_CLASSES.index(self.fma_class) - RF_CLASSES.index(self.rf_class)


def build_rows(site_id: str, fma: dict[date, float], rf: dict[tuple[str, str], Sample],
               days: list[date]) -> list[Row]:
    rows = []
    for d in days:
        s = rf.get((d.isoformat(), site_id))
        if s is None or d not in fma or math.isnan(s.rf_mean):
            continue
        rows.append(Row(site_id, d, fma[d], danger_class(fma[d]), s.rf_mean, rf_class(s.rf_mean)))
    return rows


def summarize(rows: list[Row]) -> dict:
    if not rows:
        return {"n": 0}
    gaps = [r.class_gap for r in rows]
    return {
        "n": len(rows),
        "exact": sum(g == 0 for g in gaps) / len(rows),
        "within_one": sum(abs(g) <= 1 for g in gaps) / len(rows),
        "mean_gap": sum(gaps) / len(rows),  # > 0: FMA+ more alarming than INPE
        "spearman": spearman([r.fma for r in rows], [r.rf for r in rows]),
    }
