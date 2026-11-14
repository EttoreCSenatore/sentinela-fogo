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
| Alert kind | `danger` (INPE Risco de Fogo + FMA+) | `fire` (sensor) and `hotspot` (satellite) |

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
13:00 in the site's local time (`timezone` in `sites.json`) and the total rain for each day. FMA+ *alta* and *muito alta* only trigger `danger` alerts when INPE data is
unavailable (see below).

:::info Validated
The formula, rain bands and class limits match the published method. Compared with INPE's *Risco de Fogo*, FMA+
follows the same drying and wetting cycles (rank correlation 0.75) but is about one class more alarming in dry
spells, and resets too abruptly after a single heavy rain. See [Validation](validation.md).
:::

The dashboard shows both indices side by side for every monitored area, with a three-day outlook:

![Monitored areas with INPE risk and FMA+ values](@site/static/img/screenshots/dashboard-areas.png)

## Danger alerts: INPE first, FMA+ alongside

Each monitored area also gets **INPE's official Risco de Fogo**: the observed value and INPE's forecast for today
and the next 3 days. Our [validation](validation.md) showed that FMA+ runs about one class too high and resets too
abruptly after rain, so INPE's index decides `danger` alerts:

| Situation | Alert? |
|---|---|
| INPE today is **Alto** or **Crítico** | Yes: "risco de fogo ALTO hoje em …" |
| INPE forecast is Alto/Crítico on one of the next 3 days | Yes, as an early warning: "Previsão: risco de fogo CRÍTICO em … em 17/11" |
| INPE is below Alto, even if FMA+ is *alta* | No |
| No INPE data for the area | Falls back to FMA+ *alta* / *muito alta* |

Messages always include the next days' INPE forecast and the current FMA+ value, and there's at most one `danger`
alert per area per day. The dashboard colors each area by INPE's level (FMA+ when INPE has no data), and the
Telegram `/status` command shows both indices.

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
(see [calibration](hardware.md#5-calibrate-bench-before-installing)). The rolling median (not the previous reading) is used so that a fire
building up gradually still stands out.

## Hotspot proximity

Every time new INPE hotspots arrive, each site and node is checked for hotspots inside its radius (`radius_km`
for sites, 5 km for sensors) from the last 3 hours. A match raises a `hotspot` alert, with a 3-hour cooldown per
area. It includes the number of hotspots and the distance to the nearest.

## Tuning

The weights and thresholds are in `backend/app/risk/detect.py` and `backend/app/config.py`. They are a starting
point. Pilot data (including false alarms from dust, vehicle exhaust and controlled burns) should be used to retune them.
