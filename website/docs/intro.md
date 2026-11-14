---
slug: /
sidebar_position: 1
title: Introduction
---

# Sentinela do Fogo

**Sentinela do Fogo** is an open-source IoT and cloud system for **detecting wildfires early in Brazil and alerting
the people who can respond**: landowners, fire brigades (brigadas) and Defesa Civil.

It combines three sources of information:

| Source | What it gives us | Needs hardware? |
|---|---|---|
| **INPE satellite hotspots** (BDQueimadas, every 10 min) | Active fires detected from orbit | No |
| **Weather for monitored areas** (Open-Meteo, hourly) | Temperature, humidity, wind and rain, which feed the **FMA+** fire-danger index | No |
| **ESP32 sensor nodes** | Flame, smoke/gas, temperature, humidity and GPS readings on site, every few minutes | Yes (optional) |

The system runs without any hardware. Each monitored area is a **virtual station**: we compute a daily
fire-danger level from real weather data, and the system raises an alert as soon as a satellite detects a hotspot inside the area.
Physical sensors, when added, provide faster ground-level detection on top of this.

## Goals

- **Early detection:** catch fires within minutes, not hours.
- **Instant, targeted alerts:** each recipient chooses the areas, alert types and channels (Telegram, WhatsApp, SMS, webhook) they want.
- **Low cost and open:** only open-source software and free, open data, and it runs on a single cheap server.
- **Built for Brazil:** Brazilian biomes, a fire-danger index developed in Brazil, Brazilian data sources, and LoRaWAN on Anatel's AU915 band.

## Where to go next

- [Getting started](getting-started.md) runs everything locally in a few minutes.
- [Architecture](architecture.md) shows how the pieces fit together.
- [Risk model](risk-model.md) explains how danger and detection are calculated.
- [Roadmap](roadmap.md) lists what's next.

:::info Origin
Inspired by [AK4007/wildfire-iot-monitoring](https://github.com/AK4007/wildfire-iot-monitoring), a Canadian
ESP32 + AWS project. See [ADR 0001](decisions/self-hosted-stack.md) for why we chose a self-hosted, open-source stack.
:::
