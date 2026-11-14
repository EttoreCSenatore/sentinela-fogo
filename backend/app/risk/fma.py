"""FMA+ (Fórmula de Monte Alegre Alterada) fire-danger index.

Nunes, Soares & Batista (2006). FMA+ = Σ (100 / H_i) · e^(0.04·v_i)
    H = relative humidity (%) at 13h, v = wind speed (m/s) at 13h.

Daily rainfall reduces or resets the accumulated value before the day's term is added.
TODO(validation): check the rain bands and class limits against the original paper
before using this in the field.
"""

import math
from dataclasses import dataclass

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


def fma_plus(days: list[DayObs]) -> float:
    """Compute FMA+ for the last day of a chronologically ordered series."""
    value = 0.0
    for d in days:
        factor = rain_factor(d.rain_mm)
        if factor is None:
            # Heavy rain: reset the sum and add nothing for this day.
            value = 0.0
            continue
        h = max(d.humidity_13h, 1.0)  # avoid division by zero from sensor glitches
        value = value * factor + (100.0 / h) * math.exp(0.04 * d.wind_13h)
    return value


def danger_class(value: float) -> str:
    for upper, name in CLASSES:
        if value <= upper:
            return name
    return "muito_alta"
