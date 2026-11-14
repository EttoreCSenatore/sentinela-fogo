---
sidebar_position: 5
title: Validation (FMA+ vs INPE)
---

# Validation: FMA+ vs INPE Risco de Fogo

_Last run: 2026-11-14, covering 2026-10-15 → 2026-11-13 (30 days, 4 pilot sites, 112 site-days)._

We checked two things: that our FMA+ implementation matches the published method, and how it compares with
INPE's official fire-risk product.

## 1. Is the formula implemented correctly?

**Yes.** We checked the formula, the rain rules and the class limits against the tables from Nunes, Soares & Batista (2006),
as reproduced in Eugenio et al. (2022), *FMA+ Sisclass*, Floresta 52(1):131–139, doi:10.5380/rf.v52i1.78591:

| Item | Published | Ours |
|---|---|---|
| Formula | Σ (100/H) · e^(0.04·V), H = RH at 13:00, V = wind (m/s) at 13:00 | same |
| Rain < 2.4 mm | no change | same |
| 2.5–4.9 / 5.0–9.9 / 10–12.9 mm | subtract 30 % / 60 % / 80 % of the previous day's value, then add the day's term | × 0.7 / 0.4 / 0.2, then add |
| > 12.9 mm | interrupt (FMA+ = 0), start summing again the next day | same |
| Classes | Nula ≤ 3.0, Pequena 3.1–8.0, Média 8.1–14.0, Alta 14.1–24.0, Muito alta > 24 | same |

**Bug found and fixed:** "13:00" means local clock time. We were using Brasília time for every site, so in
Mato Grosso (UTC−4) we read the humidity at 12:00. Each site now has its own `timezone` in `sites.json`.

## 2. How does it compare with INPE?

INPE's **Risco de Fogo (RF)** is a different model. It runs from 0 to 1, uses 120 days of rain, the vegetation type,
temperature and humidity at 18 UTC, and topography, and it is published as a daily grid of about 1 km. Both use five classes:

| Level | FMA+ | INPE RF |
|---|---|---|
| 1 | Nula ≤ 3 | Mínimo < 0.15 |
| 2 | Pequena 3.1–8 | Baixo 0.15–0.4 |
| 3 | Média 8.1–14 | Médio 0.4–0.7 |
| 4 | Alta 14.1–24 | Alto 0.7–0.95 |
| 5 | Muito alta > 24 | Crítico > 0.95 |

For each site and day, we compared our FMA+ (from Open-Meteo weather) with the **average INPE RF inside the site's radius**:

| Site | Days | Same class | Within 1 class | Mean gap¹ | Rank correlation² |
|---|---|---|---|---|---|
| Chapada dos Veadeiros (Cerrado) | 28 | 68 % | 100 % | +0.1 | 0.54 |
| Pantanal, Poconé | 28 | 7 % | 68 % | +0.3 | 0.31 |
| Novo Progresso (Amazônia) | 28 | 46 % | 86 % | +0.1 | 0.70 |
| Chapada Diamantina (Caatinga) | 28 | 50 % | 89 % | +0.6 | 0.93 |
| **All** | **112** | **43 %** | **86 %** | **+0.3** | **0.75** |

¹ FMA+ class minus INPE class. Positive means FMA+ is more alarming.
² Spearman: 1 means both indices rank the days in the same order. Veadeiros' value is low only because almost every day there was "nula"/"mínimo".

### What we learned

1. **FMA+ follows INPE's drying and wetting cycles well.** In Chapada Diamantina the two rise and fall together
   (correlation 0.93): both peak on 15 Oct, both drop to zero after rain on 18 Oct, 27 Oct and 9 Nov.
2. **FMA+ is about one class more alarming during dry spells.** For example, 5 Nov in Diamantina: FMA+ 20.1 is
   *alta*, while INPE 0.59 is *médio*. This fits the literature: FMA+'s classes were calibrated for Paraná, and
   percentile-based calibrations for other regions (Eugenio et al. 2020) put "very high" well above 24.
3. **The heavy-rain reset is too abrupt.** In the Pantanal on 28 Oct, 13.1 mm of rain (just 0.2 mm over the
   12.9 mm limit) reset FMA+ from 38.9 (*muito alta*) to 0, while INPE stayed *alto* (0.70). INPE remembers
   120 days of rain, so one wet day after weeks of drought barely lowers it. FMA+ forgets everything.
4. **The rest is mostly differences in rain data and timing.** INPE dropped to *mínimo* on 7 Nov, but our weather
   point shows 0.4 mm that day and 8.2 mm the next. INPE uses its own rain analysis over the whole area and
   probably starts each day at a different hour, while we use a single model point.

### What this means for alerts

- Daily `danger` alerts based only on FMA+ will fire **more often than INPE would suggest**, and may stay quiet right
  after a single heavy rain in the middle of a drought.
- Recommended next steps (see the [roadmap](roadmap.md)):
  1. ✅ **Use INPE RF as a second danger input** for each site, including INPE's 0–3-day forecast. Done: INPE now
     drives `danger` alerts (see [Risk model](risk-model.md#danger-alerts-inpe-first-fma-alongside)).
  2. **Calibrate FMA+ classes per biome** with the percentile method from Eugenio et al. (2020), using each site's
     history of INPE hotspots.

## Re-run the comparison

```bash
cd backend
.venv/bin/python -m app.cli compare-inpe --days 30 --csv data/compare.csv
```

The command downloads one INPE grid per day (~12.5 MB each, deleted after use) and caches only the per-site
samples in `data/inpe_rf_samples.csv`, so later runs only fetch new days. INPE keeps the current year of daily grids.
Code: `backend/app/validation/inpe_risk.py`.
