# 🔥 Sentinela do Fogo

**Open-source wildfire early-warning for Brazil:** INPE satellite hotspots, the FMA+ fire-danger index from real
weather data, and optional low-cost ESP32 sensor nodes. Alerts go to landowners, fire brigades and Defesa Civil
over Telegram, WhatsApp, SMS or webhooks.

**Monitoramento e alerta precoce de incêndios florestais no Brasil, em código aberto.**

📖 **Documentation / Documentação:** https://ettorecsenatore.github.io/sentinela-fogo/ (English · Português)

## Features

- Works **without hardware**: monitored areas are virtual stations driven by INPE hotspots and Open-Meteo weather
- **FMA+**, a fire-danger index developed in Brazil, computed for every area each day
- Sensor fire-detection score (flame, smoke, temperature/humidity anomaly, satellite confirmation)
- Per-recipient alert routing: areas × alert kinds × channels
- Live React + Leaflet dashboard (Server-Sent Events)
- Self-hosted with Docker Compose: Mosquitto with per-node ACLs, FastAPI, SQLite or Postgres
- Free and open data and software only

## Repository layout

```
backend/              FastAPI: MQTT/INPE/weather ingest, risk engine, alerts, REST + SSE API
dashboard/            React + Vite + Leaflet dashboard
firmware/esp32-node/  PlatformIO firmware for the sensor node
simulator/            Fake sensor nodes over MQTT
infra/                Docker Compose stack, Mosquitto config/ACL, provisioning script
website/              Docusaurus docs (en + pt-BR)
```

## Quick start

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q
SENTINELA_MQTT_ENABLED=false .venv/bin/python -m uvicorn app.main:app --reload --port 8100
# in another terminal
cd dashboard && npm install && npm run dev      # http://localhost:5174
```

Full guide: [Getting started](https://ettorecsenatore.github.io/sentinela-fogo/getting-started).
Docs run locally with `cd website && npm install && npm start` (`npm start -- --locale pt-BR` for Portuguese).

## Credits

Inspired by [AK4007/wildfire-iot-monitoring](https://github.com/AK4007/wildfire-iot-monitoring).
Hotspot data: [INPE Programa Queimadas](https://terrabrasilis.dpi.inpe.br/queimadas/). Weather data:
[Open-Meteo](https://open-meteo.com/) (CC BY 4.0). Map: © OpenStreetMap contributors.

## License

[MIT](LICENSE)
