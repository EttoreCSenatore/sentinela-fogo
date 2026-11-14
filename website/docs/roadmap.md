---
sidebar_position: 10
title: Roadmap
---

# Roadmap

## Phase 0: Foundation ✅
- [x] Backend: MQTT, INPE and weather ingest, FMA+ and detection engine, REST + SSE API, tests
- [x] Virtual stations for pilot sites (no hardware needed)
- [x] Multi-recipient alerts: Telegram, webhook, WhatsApp, SMS
- [x] Dashboard: map, sites by danger level, alerts, live updates
- [x] Self-hosted Docker stack with an authenticated MQTT broker
- [x] Sensor simulator, ESP32 firmware skeleton
- [x] Bilingual docs (en / pt-BR)

## Phase 1: Without hardware (now)
- [x] Validate FMA+ constants against Nunes et al. (2006); compare with INPE *Risco de Fogo* ([results](validation.md))
- [x] Use INPE *Risco de Fogo* (observed + 0–3-day forecast) as a second danger input per site
- [ ] Calibrate FMA+ classes per biome (percentiles of FMA+ on days with nearby INPE hotspots)
- [x] Accurate Brazil boundary filtering (IBGE states): hotspots outside Brazil are dropped and tagged with their UF
- [ ] Biome boundaries (IBGE) for per-biome statistics
- [ ] Automatic sites from ICMBio conservation units
- [ ] Database migrations (Alembic)
- [ ] Public view vs. responder view: alert acknowledgement and notes for brigades
- [ ] History charts per site (FMA+ and weather over time)
- [ ] WhatsApp template messages
- [x] Production stack: HTTPS (Caddy), MQTT over TLS, backups, deployment guide
- [ ] Deploy to a real server; send a Telegram alert to a real group

## Phase 2: First physical node
- [ ] Assemble the BOM, calibrate MQ-2, field-test battery and solar
- [ ] Per-node calibration offsets in the backend
- [x] GPS support in the firmware (plus SHT31/DHT22 choice, calibration mode, MQTT over TLS)
- [x] Step-by-step build guide ([Build a sensor node](hardware.md))

## Phase 3: Pilot network
- [ ] LoRaWAN AU915 gateway + ChirpStack → HTTP ingest
- [ ] Postgres + PostGIS
- [ ] OTA firmware updates
- [ ] Camera nodes + open smoke-detection model
