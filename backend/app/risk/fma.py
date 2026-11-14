"""FMA+ (Fórmula de Monte Alegre Alterada) fire-danger index.

Nunes, J. R. S.; Soares, R. V.; Batista, A. C. FMA+ - Um novo índice de perigo de incêndios florestais
para o Estado do Paraná. Floresta 36(1), 2006.

    FMA+ = Σ (100 / H_i) · e^(0.04·V_i)
    H = relative humidity (%) at 13:00 local time, V = wind speed (m/s) at 13:00.

Daily rainfall reduces or resets the accumulated value before the day's term is added.
Rain bands and class limits checked against the tables reproduced in Eugenio et al. (2022),
"FMA+ Sisclass", Floresta 52(1):131-139, doi:10.5380/rf.v52i1.78591 (Table 1 and Table 2).
The class limits were calibrated for Paraná; see website/docs/validation.md before trusting them
in other biomes.
"""

import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# (upper bound of daily rain in mm, multiplier applied to the accumulated value)
RAIN_RULES: list[tuple[float, float]] = [
    (2.4, 1.0),
    (4.9, 0.7),
    (9.9, 0.4),
    (12.9, 0.2),
]

CLASSES: list[tuple[float, str]] = [
    (3.0, "nula"),
    (8.0, "pequena"),
    (14.0, "media"),
    (24.0, "alta"),
]


@dataclass(frozen=True)
class DayObs:
    humidity_13h: float  # %
    wind_13h: float = 0.0  # m/s
    rain_mm: float = 0.0  # rain over the day


def rain_factor(rain_mm: float) -> float | None:
    """Multiplier for the accumulated index. Returns None when heavy rain resets it."""
    for upper, factor in RAIN_RULES:
        if rain_mm <= upper:
            return factor
    return None


def fma_series(days: list[DayObs]) -> list[float]:
    """FMA+ value at the end of each day of a chronologically ordered series."""
    out, value = [], 0.0
    for d in days:
        factor = rain_factor(d.rain_mm)
        if factor is None:
            # Heavy rain: reset the sum; accumulation restarts the next day.
            value = 0.0
        else:
            h = max(d.humidity_13h, 1.0)  # avoid division by zero from sensor glitches
            value = value * factor + (100.0 / h) * math.exp(0.04 * d.wind_13h)
        out.append(value)
    return out


def fma_plus(days: list[DayObs]) -> float:
    """Compute FMA+ for the last day of a chronologically ordered series."""
    series = fma_series(days)
    return series[-1] if series else 0.0


def daily_observations(
    points: Iterable[tuple[datetime, float, float | None, float | None]], tz: ZoneInfo
) -> list[tuple[date, DayObs]]:
    """Group (utc_ts, humidity, wind, rain) points into one DayObs per local day.

    Uses the point closest to 13:00 in `tz` (the site's local time) and the day's total rain.
    """
    by_day: dict[date, list] = defaultdict(list)
    for ts, rh, wind, rain in points:
        by_day[ts.astimezone(tz).date()].append((ts.astimezone(tz), rh, wind, rain))
    out = []
    for day in sorted(by_day):
        pts = by_day[day]
        target = datetime.combine(day, datetime.min.time(), tzinfo=tz) + timedelta(hours=13)
        _, rh, wind, _ = min(pts, key=lambda p: abs(p[0] - target))
        rain = sum(p[3] or 0.0 for p in pts)
        out.append((day, DayObs(humidity_13h=rh, wind_13h=wind or 0.0, rain_mm=rain)))
    return out


def danger_class(value: float) -> str:
    for upper, name in CLASSES:
        if value <= upper:
            return name
    return "muito_alta"
