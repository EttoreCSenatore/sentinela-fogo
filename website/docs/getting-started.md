---
sidebar_position: 2
title: Getting started
---

# Getting started

You need **Python 3.12+**, **Node.js 20.19+ or 22+** and, optionally, **Docker** (for the MQTT broker).

## 1. Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q          # runs offline, all HTTP is mocked
SENTINELA_MQTT_ENABLED=false .venv/bin/python -m uvicorn app.main:app --reload --port 8100
```

On startup the backend:

1. creates `sentinela.db` (SQLite) and registers the pilot sites from `config/sites.json`;
2. downloads the last hour of INPE hotspots, then refreshes every 10 minutes;
3. backfills 30 days of hourly weather for each site, then refreshes every hour.

API docs are at [http://localhost:8100/docs](http://localhost:8100/docs).

## 2. Dashboard

```bash
cd dashboard
npm install
npm run dev        # http://localhost:5174, proxies /api to :8100
```

Clicking a sensor shows its latest reading and detection score:

![Sensor popup showing temperature, humidity, smoke, flame and FMA+](@site/static/img/screenshots/dashboard-node-popup.png)

The dashboard is responsive and works on a phone:

![Dashboard on a phone](@site/static/img/screenshots/dashboard-mobile.png)

## 3. (Optional) Simulated sensors over MQTT

```bash
docker compose -f infra/docker-compose.dev.yml up -d      # anonymous broker on :1883
# restart the backend without SENTINELA_MQTT_ENABLED=false, then:
backend/.venv/bin/python simulator/simulate.py --nodes 5 --fire-at 3
```

`--fire-at 3` makes node 0 "catch fire" after 3 cycles, so you can watch a fire alert being raised.

## Configuration

All settings are environment variables prefixed with `SENTINELA_` (or a `.env` file in `backend/`).
See `backend/.env.example` and `backend/app/config.py`. The most common ones:

| Variable | Default | Meaning |
|---|---|---|
| `SENTINELA_DATABASE_URL` | `sqlite:///./sentinela.db` | SQLAlchemy URL (Postgres: `postgresql+psycopg://...`) |
| `SENTINELA_MQTT_ENABLED` | `true` | Subscribe to the MQTT broker |
| `SENTINELA_INPE_ENABLED` | `true` | Poll INPE hotspots |
| `SENTINELA_WEATHER_ENABLED` | `true` | Poll Open-Meteo for the pilot sites |
| `SENTINELA_SITES_FILE` | `config/sites.json` | Monitored areas |
| `SENTINELA_RECIPIENTS_FILE` | `config/recipients.json` | Who receives which alerts ([Alerts](alerts.md)) |
