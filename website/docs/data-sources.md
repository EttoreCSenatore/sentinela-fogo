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
- **Coverage:** South America. We keep only points inside Brazil, using IBGE's official state boundaries (below), and tag
  each hotspot with its state (UF). Points up to 2 km outside the outline still count, so fires on the coast, on
  small islands and along border rivers aren't lost to the simplified coastline.
- **Limits:** geostationary detections (GOES) are frequent but coarse (~2 km pixel). Polar-orbit sensors are sharper
  but only pass a few times a day. Clouds and smoke can hide fires, and small fires may go undetected.
- **Code:** `backend/app/ingest/inpe.py`

## Open-Meteo: weather for monitored areas

- **What:** hourly temperature, relative humidity, wind and precipitation for any coordinate. No API key needed.
- **Used for:** virtual stations at each pilot site. This data drives the FMA+ danger index.
- **Notes:** this is **model data** (forecast and reanalysis), not a weather-station measurement. Open-Meteo's
  free API is for **non-commercial use**, and the data is CC BY 4.0, so credit it if you publish results.
- **Code:** `backend/app/ingest/weather.py`

## INPE Risco de Fogo: official fire risk

- **What:** INPE's daily fire-risk index (0–1, five classes), on a grid of about 1 km.
- **Feed:** `https://dataserver-coids.inpe.br/queimadas/queimadas/riscofogo_meteorologia/observado/risco_fogo/`
  (one NetCDF file per day, ~12.5 MB, current year). There's also a 0–3-day forecast in `.../previsto/risco_fogo/` (GeoTIFF).
- **Used for:** the main input for `danger` alerts, the dashboard colors and `/status`, plus checking our FMA+
  ([Validation](validation.md)). The backend checks for new files every 3 hours and samples each area's radius.
- **Traffic:** about 90 MB per day (four forecast files of ~20 MB plus one observed file of ~12.5 MB). Files are
  deleted after sampling. Set `SENTINELA_INPE_RISK_ENABLED=false` to turn it off.
- **Code:** `backend/app/ingest/inpe_risk.py`

## IBGE: state boundaries

- **What:** official boundaries of the 27 states (UFs), from IBGE's *Malhas territoriais* API (v3, intermediate detail).
- **File:** `backend/config/br_uf.geojson` (250 KB, shipped in the repository, so no download at runtime).
- **Used for:** dropping hotspots outside Brazil and tagging each one with its state (`/api/hotspots?uf=GO`).
- **Code:** `backend/app/geo.py`. Settings: `SENTINELA_BOUNDARIES_FILE`, `SENTINELA_BORDER_TOLERANCE_KM` (default 2).

## Candidates to add

| Source | Why |
|---|---|
| INMET automatic weather stations | Real measurements for validating Open-Meteo values |
| IBGE biome boundaries | Per-biome statistics and alerts |
| ICMBio conservation units (UCs) | Monitor protected areas automatically |
| NASA FIRMS (VIIRS 375 m) | Sharper hotspots (needs a free map key) |
| MapBiomas Fogo | Historical burned area, to choose sites and validate results |
