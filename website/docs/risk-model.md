---
sidebar_position: 4
title: Risk model
---

# Risk model

The system calculates two different things:

| | Fire **danger** | Fire **detection** |
|---|---|---|
| Question | How easily could a fire start and spread here? | Is something burning right now? |
| Speed | Daily | Every reading or hotspot |
| Inputs | Humidity, wind and rain | Flame, smoke, temperature/humidity anomalies, satellite hotspots |
| Alert kind | `danger` | `fire` (sensor) and `hotspot` (satellite) |

## Fire danger: FMA+

**FMA+** (Fórmula de Monte Alegre Alterada; Nunes, Soares & Batista, 2006) is a cumulative index developed and
calibrated in Brazil. It adds wind to the original Monte Alegre formula (Soares, 1972):

```text
FMA+ = Σ (100 / Hᵢ) · e^(0.04 · vᵢ)
```

- `Hᵢ` is the relative humidity (%) at 13:00 local time on day *i*.
- `vᵢ` is the wind speed (m/s) at 13:00.
- Rain on each day reduces the running sum before that day's term is added:

| Daily rain (mm) | Effect on the sum |
|---|---|
| ≤ 2.4 | none |
| 2.5 – 4.9 | × 0.7 |
| 5.0 – 9.9 | × 0.4 |
| 10.0 – 12.9 | × 0.2 |
| > 12.9 | reset to 0, and that day adds nothing |

| FMA+ | Class |
|---|---|
| ≤ 3.0 | Nula (none) |
| 3.1 – 8.0 | Pequena (low) |
| 8.1 – 14.0 | Média (medium) |
| 14.1 – 24.0 | Alta (high) |
| > 24.0 | Muito alta (very high) |

The backend calculates FMA+ over the last 30 days of each node's or site's readings. It uses the reading closest to
13:00 Brasília time and the total rain for each day. **Alta** and **muito alta** trigger a `danger` alert, at most
once a day per area.

:::caution To validate
The rain bands and class limits were transcribed from the literature. Before field use they must be checked against
the original paper and compared with INPE's own *Risco de Fogo* product. This is tracked in the [roadmap](roadmap.md).
:::

## Fire detection from sensors

Each sensor reading gets a score from 0 to 1. Each signal that fires adds to it, and the total is capped at 1:

| Signal | Weight |
|---|---|
| IR flame sensor triggered | 0.6 |
| Smoke ≥ 4× the node's rolling median | 0.5 |
| Smoke ≥ 2× the node's rolling median | 0.3 |
| Temperature +5 °C **and** humidity −10 points compared with the rolling median | 0.2 |
| INPE hotspot within 5 km in the last 3 h | 0.3 |

A score of **0.6 or more** raises a `fire` alert, with a 30-minute cooldown per node. Comparing each reading with
the node's own baseline, instead of fixed thresholds, adjusts automatically for each sensor and its surroundings
(see [calibration](hardware.md#calibration)). The rolling median (not the previous reading) is used so that a fire
building up gradually still stands out.

## Hotspot proximity

Every time new INPE hotspots arrive, each site and node is checked for hotspots inside its radius (`radius_km`
for sites, 5 km for sensors) from the last 3 hours. A match raises a `hotspot` alert, with a 3-hour cooldown per
area. It includes the number of hotspots and the distance to the nearest.

## Tuning

The weights and thresholds are in `backend/app/risk/detect.py` and `backend/app/config.py`. They are a starting
point. Pilot data (including false alarms from dust, vehicle exhaust and controlled burns) should be used to retune them.
