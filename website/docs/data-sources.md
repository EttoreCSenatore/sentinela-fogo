---
sidebar_position: 5
title: Data sources
---

# Data sources

Everything we use is free and open.

## INPE BDQueimadas: satellite hotspots

- **What:** active-fire detections ("focos de calor") from several satellites (GOES-19, NOAA-20/21, Suomi-NPP, Aqua, Terra, METOP...),
  published by INPE's Programa Queimadas.
- **Feed:** `https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/10min/`, with a new CSV every 10 minutes
  named `focos_10min_YYYYMMDD_HHMM.csv`. Columns: `lat,lon,satelite,data` (UTC).
- **Coverage:** South America. We keep only points inside Brazil's bounding box. This is a rough rectangle and lets
  some points from neighbouring countries through; filtering by the real Brazil boundary is on the [roadmap](roadmap.md).
- **Limits:** geostationary detections (GOES) are frequent but coarse (~2 km pixel). Polar-orbit sensors are sharper
  but only pass a few times a day. Clouds and smoke can hide fires, and small fires may go undetected.
- **Code:** `backend/app/ingest/inpe.py`

## Open-Meteo: weather for monitored areas

- **What:** hourly temperature, relative humidity, wind and precipitation for any coordinate. No API key needed.
- **Used for:** virtual stations at each pilot site. This data drives the FMA+ danger index.
- **Notes:** this is **model data** (forecast and reanalysis), not a weather-station measurement. Open-Meteo's
  free API is for **non-commercial use**, and the data is CC BY 4.0, so credit it if you publish results.
- **Code:** `backend/app/ingest/weather.py`

## INPE Risco de Fogo: official fire risk (validation)

- **What:** INPE's daily fire-risk index (0–1, five classes), on a grid of about 1 km.
- **Feed:** `https://dataserver-coids.inpe.br/queimadas/queimadas/riscofogo_meteorologia/observado/risco_fogo/`
  (one NetCDF file per day, ~12.5 MB, current year). There's also a 0–3-day forecast in `.../previsto/risco_fogo/` (GeoTIFF).
- **Used for:** checking our FMA+ ([Validation](validation.md)). Using it as a live danger input is on the roadmap.
- **Code:** `backend/app/validation/inpe_risk.py`

## Candidates to add

| Source | Why |
|---|---|
| INMET automatic weather stations | Real measurements for validating Open-Meteo values |
| IBGE biome and state boundaries | Accurate Brazil filtering and per-biome statistics |
| ICMBio conservation units (UCs) | Monitor protected areas automatically |
| NASA FIRMS (VIIRS 375 m) | Sharper hotspots (needs a free map key) |
| MapBiomas Fogo | Historical burned area, to choose sites and validate results |
