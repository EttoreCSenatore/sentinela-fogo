"""Which Brazilian state (UF) a point is in, using IBGE's official boundaries (config/br_uf.geojson).

Pure Python point-in-polygon (ray casting) with a bounding-box pre-check per polygon. Fast enough for INPE's
~100 hotspots per poll; no GIS dependencies.
"""

import json
import logging
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config import settings

log = logging.getLogger(__name__)

Ring = list[tuple[float, float]]  # (lon, lat)


@dataclass
class Polygon:
    bbox: tuple[float, float, float, float]  # lon_min, lat_min, lon_max, lat_max
    outer: Ring
    holes: list[Ring]


@dataclass
class State:
    sigla: str
    nome: str
    bbox: tuple[float, float, float, float]
    polygons: list[Polygon]


def _ring_bbox(ring: Ring) -> tuple[float, float, float, float]:
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


def _in_bbox(b, lon: float, lat: float) -> bool:
    return b[0] <= lon <= b[2] and b[1] <= lat <= b[3]


def _in_ring(ring: Ring, lon: float, lat: float) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _in_polygon(p: Polygon, lon: float, lat: float) -> bool:
    return (_in_bbox(p.bbox, lon, lat) and _in_ring(p.outer, lon, lat)
            and not any(_in_ring(h, lon, lat) for h in p.holes))


def load_states(path: str | Path) -> list[State]:
    data = json.loads(Path(path).read_text())
    states = []
    for f in data["features"]:
        geom = f["geometry"]
        parts = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        polys = []
        for rings in parts:
            outer = [(float(x), float(y)) for x, y in rings[0]]
            holes = [[(float(x), float(y)) for x, y in r] for r in rings[1:]]
            polys.append(Polygon(_ring_bbox(outer), outer, holes))
        b = (min(p.bbox[0] for p in polys), min(p.bbox[1] for p in polys),
             max(p.bbox[2] for p in polys), max(p.bbox[3] for p in polys))
        states.append(State(f["properties"]["sigla"], f["properties"]["nome"], b, polys))
    return states


@lru_cache(maxsize=4)
def _states_cached(path: str) -> tuple[State, ...] | None:
    p = Path(path)
    if not p.exists():
        log.warning("boundaries file %s not found: hotspots are filtered by bounding box only", p)
        return None
    return tuple(load_states(p))


def boundaries_available() -> bool:
    return _states_cached(settings.boundaries_file) is not None


def _segment_km(lat: float, lon: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distance from the point to segment a-b in km (local equirectangular projection)."""
    kx = 111.32 * math.cos(math.radians(lat))
    ky = 110.57
    ax, ay = (a[0] - lon) * kx, (a[1] - lat) * ky
    bx, by = (b[0] - lon) * kx, (b[1] - lat) * ky
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
    return math.hypot(ax + t * dx, ay + t * dy)


def _expand(b, lat: float, km: float):
    dlat = km / 110.57
    dlon = km / (111.32 * max(math.cos(math.radians(lat)), 0.1))
    return b[0] - dlon, b[1] - dlat, b[2] + dlon, b[3] + dlat


def locate_uf(lat: float, lon: float, tolerance_km: float | None = None) -> str | None:
    """UF code (e.g. "GO") for a point in Brazil, or None outside (or when boundaries are missing).

    Points outside every state but within `tolerance_km` of a state's outline get the nearest state, so coastal
    and island fires aren't lost to the simplified coastline.
    """
    states = _states_cached(settings.boundaries_file)
    if not states:
        return None
    for s in states:
        if _in_bbox(s.bbox, lon, lat) and any(_in_polygon(p, lon, lat) for p in s.polygons):
            return s.sigla
    tol = settings.border_tolerance_km if tolerance_km is None else tolerance_km
    if tol <= 0:
        return None
    best, best_d = None, tol
    for s in states:
        if not _in_bbox(_expand(s.bbox, lat, tol), lon, lat):
            continue
        for p in s.polygons:
            if not _in_bbox(_expand(p.bbox, lat, tol), lon, lat):
                continue
            ring = p.outer
            for i in range(len(ring) - 1):
                d = _segment_km(lat, lon, ring[i], ring[i + 1])
                if d <= best_d:
                    best, best_d = s.sigla, d
    return best
