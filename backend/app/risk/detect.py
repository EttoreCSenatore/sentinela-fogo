"""Fast, per-reading fire detection score in [0, 1].

The score is deliberately simple and explainable so it can be tuned on pilot data.
Each signal adds weight, and the result is capped at 1.0.
"""

import math
import statistics
from dataclasses import dataclass, field

W_FLAME = 0.6
W_SMOKE_HIGH = 0.5  # smoke >= 4x baseline
W_SMOKE_MED = 0.3  # smoke >= 2x baseline
W_THERMAL = 0.2  # sudden temperature rise + humidity drop
W_HOTSPOT = 0.3  # INPE satellite hotspot nearby

TEMP_JUMP_C = 5.0
RH_DROP_PCT = 10.0
MIN_BASELINE_SAMPLES = 3


@dataclass
class Detection:
    score: float
    reasons: list[str] = field(default_factory=list)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def score_reading(
    *,
    temp_c: float,
    humidity_pct: float,
    smoke_ppm: float | None,
    flame: bool,
    history: list[tuple[float, float, float | None]],  # (temp, rh, smoke), oldest -> newest
    nearest_hotspot_km: float | None,
    hotspot_radius_km: float,
) -> Detection:
    det = Detection(score=0.0)

    if flame:
        det.score += W_FLAME
        det.reasons.append("sensor de chama ativado")

    smokes = [s for _, _, s in history if s is not None]
    if smoke_ppm is not None and len(smokes) >= MIN_BASELINE_SAMPLES:
        baseline = max(statistics.median(smokes), 1.0)
        ratio = smoke_ppm / baseline
        if ratio >= 4:
            det.score += W_SMOKE_HIGH
            det.reasons.append(f"fumaça {ratio:.1f}x acima da linha de base")
        elif ratio >= 2:
            det.score += W_SMOKE_MED
            det.reasons.append(f"fumaça {ratio:.1f}x acima da linha de base")

    if len(history) >= MIN_BASELINE_SAMPLES:
        # Compare with the rolling baseline, not just the previous reading, so a fire that
        # builds up over several samples is still caught.
        base_t = statistics.median(t for t, _, _ in history)
        base_rh = statistics.median(rh for _, rh, _ in history)
        if temp_c - base_t >= TEMP_JUMP_C and base_rh - humidity_pct >= RH_DROP_PCT:
            det.score += W_THERMAL
            det.reasons.append(
                f"temperatura +{temp_c - base_t:.1f}°C e umidade -{base_rh - humidity_pct:.0f}% vs. linha de base"
            )

    if nearest_hotspot_km is not None and nearest_hotspot_km <= hotspot_radius_km:
        det.score += W_HOTSPOT
        det.reasons.append(f"foco INPE a {nearest_hotspot_km:.1f} km")

    det.score = min(det.score, 1.0)
    return det
