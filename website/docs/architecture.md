---
sidebar_position: 3
title: Architecture
---

# Architecture

```text
 ┌──────────────┐ MQTT (Wi-Fi/4G)    ┌────────────┐       ┌────────────────────────────────┐
 │ ESP32 node   │ ─────────────────▶ │ Mosquitto  │ ────▶ │ backend (FastAPI)              │
 │ flame, smoke │ LoRaWAN AU915      │  broker    │       │  ├ ingest/mqtt.py    sensors   │
 │ temp/RH, GPS │ ─▶ gateway ─▶      └────────────┘       │  ├ ingest/inpe.py    hotspots  │──▶ Telegram / WhatsApp
 └──────────────┘    ChirpStack ── HTTP ──────────▶       │  ├ ingest/weather.py sites     │    SMS / webhook
                                                          │  ├ risk/  FMA+ & detection     │
   INPE BDQueimadas (10 min) ───────────────────────────▶ │  ├ alerts/ routing & delivery  │
   Open-Meteo (hourly) ─────────────────────────────────▶ │  └ REST + SSE  /api/...        │
                                                          │     SQLite → Postgres/PostGIS  │
                                                          └───────────────┬────────────────┘
                                                                          │ HTTP + Server-Sent Events
                                                                   ┌──────▼──────┐
                                                                   │ dashboard   │ React + Leaflet
                                                                   └─────────────┘
```

## Components

| Component | Tech | Role | AWS equivalent in the reference project |
|---|---|---|---|
| Broker | Mosquitto 2 | Receives sensor telemetry, per-node ACLs | IoT Core |
| Backend | Python, FastAPI, SQLAlchemy | Ingest, risk engine, alerts, API | Lambda + API Gateway |
| Storage | SQLite (WAL) → Postgres/PostGIS | Nodes, readings, hotspots, alerts | DynamoDB |
| Dashboard | React, Vite, Leaflet, OpenStreetMap | Live map, sites, alerts | React dashboard |
| Docs | Docusaurus (en, pt-BR) | This site | — |

## Repository layout

```text
backend/              FastAPI service + tests
  app/ingest/         mqtt.py, inpe.py, weather.py
  app/risk/           fma.py (FMA+), detect.py (sensor detection score)
  app/alerts/         dispatch.py (recipients x channels)
  config/             sites.json, recipients.example.json
dashboard/            React dashboard
firmware/esp32-node/  PlatformIO sensor firmware
simulator/            Fake sensor nodes over MQTT
infra/                docker-compose, Mosquitto config/ACL, provisioning script
website/              This documentation
```

## MQTT contract

Topic: `sentinela/v1/nodes/{node_id}/telemetry` (QoS 1). The **topic decides the `node_id`**. Any `node_id`
inside the payload is ignored, so a node can't write data as another node.

```json
{
  "ts": "2026-11-14T16:00:00Z",
  "lat": -15.79, "lon": -47.88,
  "temp_c": 34.2, "humidity_pct": 18.0,
  "smoke_ppm": 120.0,
  "flame": false,
  "wind_ms": 3.1,
  "rain_mm": 0.0,
  "battery_v": 3.92
}
```

`ts`, `smoke_ppm`, `wind_ms`, `rain_mm` and `battery_v` are optional. `lat`/`lon` come from the GPS module or a
fixed position in the firmware. `sentinela/v1/nodes/{node_id}/status` carries the retained `online`/`offline` message
(MQTT last will).

The same payload (with `node_id`) can be sent to `POST /api/readings`. LoRaWAN network servers and 4G gateways use this.

## HTTP API

| Method | Path | Description |
|---|---|---|
| GET | `/api/overview` | Every node/site with its latest reading and FMA+ danger (one call for the dashboard) |
| GET | `/api/stream` | Server-Sent Events: `alert` and `reading` events as they happen |
| GET | `/api/nodes` | Nodes and sites |
| GET | `/api/nodes/{id}/readings` | Recent readings |
| GET | `/api/nodes/{id}/danger` | FMA+ value and class |
| GET | `/api/hotspots?hours=24` | INPE hotspots |
| GET | `/api/alerts` | Latest alerts |
| POST | `/api/readings` | HTTP ingest |

## Data model

- `nodes`: id, name, kind (`sensor` / `virtual`), lat, lon, biome, radius_km, last_seen, battery_v
- `readings`: node_id, ts, temp_c, humidity_pct, smoke_ppm, flame, wind_ms, rain_mm, score
- `hotspots`: lat, lon, satellite, ts (unique on all four)
- `alerts`: node_id, ts, kind (`fire` / `hotspot` / `danger`), score, message, delivered
