---
sidebar_position: 9
title: Hardware & calibration
---

# Hardware & calibration

Hardware is **optional**. The system already works with satellite and weather data. Sensor nodes add ground-level
detection within minutes. The firmware lives in `firmware/esp32-node` (PlatformIO, Arduino framework).

## Bill of materials: node v1 (approx. R$ 250–400)

| Part | Purpose | Notes |
|---|---|---|
| ESP32 DevKit, or Heltec LoRa32 / LILYGO T-Beam for LoRa | Microcontroller | The T-Beam includes GPS and LoRa |
| SHT31 (preferred) or DHT22 | Temperature / humidity | SHT31 is more accurate and holds up better outdoors |
| MQ-2 | Smoke / combustible gas | Heater draws ~150 mA. Power it through a MOSFET only while sampling |
| IR flame sensor (KY-026) | Direct flame | Short range (~1 m). Only useful near likely ignition points |
| GPS (NEO-6M / NEO-M8N) | Position, time | Optional for fixed nodes: record the position once at installation |
| Anemometer, rain gauge (optional) | Wind/rain for FMA+ | Weather data can be used instead |
| 6 V 2–5 W solar panel + charger + 2× 18650 | Power | |
| IP65 enclosure + radiation shield | Protection | Direct sunlight makes temperature readings several °C too high |

### Wiring (defaults in `src/config.h`)

| Signal | ESP32 pin |
|---|---|
| DHT22 data | GPIO 4 |
| MQ-2 AO | GPIO 34 (ADC1) |
| MQ-2 heater MOSFET | GPIO 25 |
| Flame DO | GPIO 27 |
| Battery divider | GPIO 35 |
| GPS TX → ESP32 RX | GPIO 16 (UART2) |

:::danger 5 V on the ADC
Most MQ-2 boards run at 5 V, and their AO pin can reach 5 V. The ESP32 ADC accepts at most 3.3 V. Use a divider
(e.g. 10 kΩ / 20 kΩ) and correct for it in `readMq2Ppm()`.
:::

## Calibration

Outdoor sensors drift and vary from unit to unit, so calibrate before trusting the readings.

1. **MQ-2 burn-in:** run the heater for 24–48 h before the first calibration.
2. **MQ-2 R0:** in clean air, measure Rs and set `MQ2_R0_KOHM = Rs / 9.8` (the clean-air ratio from the datasheet).
   Repeat every few months. Humidity and temperature shift the curve.
3. **Treat smoke as relative:** cheap gas sensors can't give exact ppm values. The backend therefore compares each reading
   with the **node's own rolling median**, not with fixed ppm limits. This adjusts for the drift.
4. **Temperature/humidity:** before deployment, put all nodes next to a reference thermometer/hygrometer for 24 h, then
   record each node's offsets. (A per-node offsets table in the backend is on the roadmap.)
5. **Radiation shield:** without one, sunlight on the enclosure can add 5–10 °C. That causes false thermal alerts and a wrong FMA+.
6. **Flame sensor:** check its range and angle with a lighter at the planned distance, and adjust the
   potentiometer to avoid false triggers from direct sunlight.

## Connectivity

| Option | When |
|---|---|
| Wi-Fi | Next to a farmhouse or another building with internet |
| 4G modem (SIM7600) | Where there's cell coverage |
| **LoRaWAN AU915** | Remote areas: gateway with ChirpStack (self-hosted), up to ~10 km in open terrain |

AU915 is the LoRaWAN band plan used in Brazil (Anatel). Use sub-band 2 (channels 8–15), which matches The Things Network.
