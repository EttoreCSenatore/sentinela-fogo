---
sidebar_position: 6
title: Pilot sites
---

# Pilot sites

Without hardware, each monitored area is a **virtual station**: a point plus a radius. Hourly weather for the point
feeds FMA+, and any INPE hotspot inside the radius raises an alert.

The first four sites are in fire-prone areas across different biomes:

| ID | Area | Biome | Radius | Why |
|---|---|---|---|---|
| `chapada-veadeiros` | Chapada dos Veadeiros (GO) | Cerrado | 20 km | National park with recurring large fires (e.g. 2017) |
| `pantanal-pocone` | Transpantaneira, Poconé (MT) | Pantanal | 25 km | Hit hard in the 2020 and 2024 fire seasons |
| `novo-progresso` | Novo Progresso (PA) | Amazônia | 25 km | Arc of deforestation, where fire is used to clear land |
| `chapada-diamantina` | Chapada Diamantina (BA) | Caatinga/Cerrado | 20 km | Frequent dry-season fires in the national park |

Coordinates are approximate area centres. Refine them before relying on them.

Pilot areas are listed in the dashboard side panel with today's INPE class, the FMA+ value and the next three days:

![Pilot areas in the dashboard](@site/static/img/screenshots/dashboard-areas.png)

## Adding a site

Edit `backend/config/sites.json` and restart the backend:

```json
{"id": "jalapao", "name": "Jalapão (TO)", "biome": "cerrado", "lat": -10.40, "lon": -46.60, "radius_km": 25, "timezone": "America/Araguaina"}
```

`id` must be unique and may only contain letters, numbers, `-` and `_`. `timezone` is the area's local
legal time (IANA name), used for FMA+'s 13:00 reading; it defaults to `America/Sao_Paulo`. On the next start, the backend fetches 30 days of weather for the new site.
