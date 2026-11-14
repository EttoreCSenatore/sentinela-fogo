---
sidebar_position: 9
title: Build a sensor node
---

# Build a sensor node

The system already works without hardware (satellite hotspots, weather and INPE risk). A **sensor node** adds the
one thing satellites can't: **ground-level detection within minutes**, right where fires tend to start. This guide
takes you from parts to a node reporting on the dashboard and sending Telegram alerts.

**Time:** an afternoon to assemble and flash, plus 1–2 days of sensor burn-in. **Cost:** roughly R$ 300–500 per node.
**Skills:** basic soldering, or a breadboard/jumper wires for the bench version, and copying commands into a terminal.

:::danger Safety first
- Never test with real fire near vegetation. Use an incense stick (smoke) and a lighter held briefly (flame), on a non-flammable surface.
- The MQ-2 heater gets hot (~50 °C on the case). Don't touch it while it's running.
- Use **protected** 18650 cells (with a BMS/DW01 protection board) and a charger made for lithium cells. Batteries in a closed box in the sun get very hot: shade the enclosure.
:::

## 1. Parts

Prices are rough 2026 estimates in reais from common sellers (Mercado Livre, local electronics shops, AliExpress).

| # | Part | Qty | ~R$ | Notes |
|---|---|---|---|---|
| 1 | **ESP32 DevKit v1** (ESP-WROOM-32, 30 or 38 pins) | 1 | 40–60 | The microcontroller. Any ESP32 with Wi-Fi works; pins below are for the DevKit v1 |
| 2 | **SHT31** temperature/humidity module (I2C) | 1 | 30–50 | Recommended. *Alternative:* DHT22 (R$ 25–40), cheaper but less reliable outdoors |
| 3 | **MQ-2** gas/smoke module | 1 | 10–20 | Board with AO (analog) output |
| 4 | **KY-026** IR flame sensor module | 1 | 8–15 | Optional. Only useful within ~1 m of where a fire could start |
| 5 | **GPS NEO-6M** (or NEO-M8N) module with antenna | 1 | 40–70 | Optional. You can type the position into the config instead |
| 6 | Logic-level N-MOSFET **AO3400** or **IRLZ44N** | 1 | 2–5 | Switches the MQ-2 heater on only while sampling |
| 7 | Resistors: 2× 100 kΩ, 1× 100 kΩ, 1× 10 kΩ, 1× 20 kΩ, 1× 100 Ω | 1 kit | 5–10 | Dividers, MOSFET gate, battery sense |
| 8 | Solar panel **6 V, 3–5 W** | 1 | 40–70 | Faces north (we're in the southern hemisphere) |
| 9 | **TP4056** charger module *with protection* (USB-C version with DW01 chip) | 1 | 5–10 | Charges the batteries from the panel |
| 10 | **18650** Li-ion cells, protected, + 2-cell **parallel** holder | 2 | 40–80 | ~6000 mAh total at 3.7 V |
| 11 | **MT3608** boost converter (set to 5.0 V) | 1 | 5–10 | Battery → 5 V for the ESP32 (VIN) and the MQ-2 |
| 12 | IP65 enclosure ~15×10×7 cm + cable glands | 1 | 30–60 | |
| 13 | Radiation shield for the SHT31 | 1 | 0–40 | DIY: 5–6 stacked white plastic plates with spacers, or buy one |
| 14 | Stainless mesh (insect screen), silicone, zip ties, pole/bracket | — | 20–40 | |

**Tools:** soldering iron, multimeter (essential: you'll set the boost to 5 V and check voltages), wire stripper, USB cable,
a computer with a USB port.

## 2. How it fits together

```text
 Solar 6V ──▶ TP4056 (charger+protection) ──▶ 2× 18650 in parallel (3.0–4.2 V)
                                   │ OUT+/OUT-
                                   ├──────────────▶ battery sense divider ──▶ GPIO35
                                   ▼
                          MT3608 boost → 5.0 V
                                   │
               ┌───────────────────┼────────────────────────┐
               ▼                   ▼                        ▼
         ESP32 VIN (5V)     MQ-2 VCC (5V)            GPS VCC (5V or 3.3V*)
         ESP32 3V3 ──▶ SHT31 VCC, KY-026 VCC
         MQ-2 GND ──▶ MOSFET drain │ source ──▶ GND │ gate ◀── 100Ω ◀── GPIO25
```

\* Check your GPS module's label: most NEO-6M boards accept 3.3–5 V.

## 3. Wiring

Connect all grounds (GND) together: battery −, boost GND, ESP32 GND, sensors' GND, MOSFET source.

### Power

| From | To |
|---|---|
| Solar panel + / − | TP4056 **IN+ / IN−** |
| 18650 holder + / − (cells in **parallel**) | TP4056 **B+ / B−** |
| TP4056 **OUT+ / OUT−** | MT3608 **VIN+ / VIN−** |
| MT3608 **VOUT+** (adjust to **5.0 V** with the multimeter *before* connecting the ESP32) | ESP32 **VIN**, MQ-2 **VCC** |
| TP4056 OUT+ → **100 kΩ** → **GPIO35** → **100 kΩ** → GND | battery voltage sense |

### Temperature and humidity

**SHT31 (recommended):**

| SHT31 | ESP32 |
|---|---|
| VIN / VCC | 3V3 |
| GND | GND |
| SDA | GPIO21 |
| SCL | GPIO22 |

**or DHT22:** VCC → 3V3, GND → GND, DATA → **GPIO4**, plus a **10 kΩ** resistor between DATA and 3V3 (many modules already have it).
Set `TH_SENSOR_SHT31 0` in `config.h`.

### MQ-2 smoke sensor (heater switched by the MOSFET)

The MQ-2 runs at 5 V and its AO output can reach 5 V, but the ESP32's input only tolerates 3.3 V: **always use the divider**.

| MQ-2 | Goes to |
|---|---|
| VCC | 5 V (MT3608 out) |
| GND | MOSFET **drain** |
| AO | **10 kΩ** → **GPIO34**, and GPIO34 → **20 kΩ** → GND |
| DO | not used |

| MOSFET (AO3400 / IRLZ44N) | Goes to |
|---|---|
| Gate | **100 Ω** → **GPIO25** (add 100 kΩ gate → GND so it stays off during boot) |
| Source | GND |
| Drain | MQ-2 GND |

With the 10 k/20 k divider, keep `MQ2_DIVIDER 1.5` in `config.h`. Without a divider (not recommended) use `1.0`.
Check the load resistor printed on your MQ-2 board (often "502" = 5 kΩ or "103" = 10 kΩ) and set `MQ2_RL_KOHM` to match.

### Flame sensor (optional)

| KY-026 | ESP32 |
|---|---|
| VCC (+) | 3V3 |
| GND (G) | GND |
| DO | **GPIO27** |

Most modules pull DO **LOW** when they see flame (`FLAME_ACTIVE_LOW 1`). If yours does the opposite, set it to 0.

### GPS (optional)

| GPS | ESP32 |
|---|---|
| VCC | 5 V or 3V3 (see the module) |
| GND | GND |
| TX | **GPIO16** (ESP32 RX) |
| RX | **GPIO17** (ESP32 TX) |

Set `USE_GPS 1`. On power-up the node waits up to 2 minutes for a good fix (outdoors, clear sky), then keeps that
position in memory across sleeps. Without GPS, set `NODE_LAT`/`NODE_LON` from your phone's map.

## 4. Software: configure, provision, flash

**4.1 Install PlatformIO** (once): either the *PlatformIO IDE* extension for VS Code, or on the command line:

```bash
python3 -m pip install --user platformio
```

**4.2 Get the code and create your secrets file:**

```bash
git clone https://github.com/EttoreCSenatore/sentinela-fogo.git
cd sentinela-fogo/firmware/esp32-node
cp src/secrets.example.h src/secrets.h
```

**4.3 Create the node's login on your server** (each node has its own MQTT user, which must equal its ID):

```bash
infra/provision.sh node cerrado-001        # run on the server, from the repository root
# cerrado-001  Xk3...   <- the password, shown once
```

**4.4 Edit the configuration:**

- `src/config.h`: `NODE_ID` (same as above), `NODE_LAT`/`NODE_LON`, and which sensors you installed (`TH_SENSOR_SHT31`,
  `USE_MQ2`, `USE_FLAME`, `USE_GPS`).
- `src/secrets.h`: Wi-Fi name and password, `MQTT_HOST` (your server), `MQTT_PASSWORD` (from 4.3).
  For an internet server with TLS, follow the comments in the file (port 8883 and the Let's Encrypt CA certificate).

**4.5 Flash** with the ESP32 connected by USB:

```bash
pio run -t upload
pio device monitor        # Ctrl+C to exit
```

You should see `published: {...}` followed by `sleeping 300 s`. The node now appears on the dashboard as a sensor.
If your computer doesn't detect the board, install the USB driver for its chip (CP2102 or CH340).

## 5. Calibrate (bench, before installing)

Cheap sensors vary from unit to unit. The backend compares each node with its **own** recent readings, so small offsets
don't cause false alarms, but calibrating makes the numbers meaningful.

1. **MQ-2 burn-in and R0.** Set `CALIBRATION_MODE 1` in `config.h`, flash, and leave the node powered **in clean air**
   (outdoors or a ventilated room, no cooking or cars nearby) for **24–48 h** the first time. The serial monitor prints
   `R0 (clean air) = X` every 2 s. Once it's stable, copy that value into `MQ2_R0_KOHM`, set `CALIBRATION_MODE 0`, and flash again.
2. **Temperature/humidity.** Put the node next to a trusted thermometer/hygrometer for a few hours. A difference of
   1 °C / 5 % RH is normal for these sensors. Note it, since a per-node offset setting is on the roadmap.
3. **Flame sensor.** In calibration mode, hold a lighter at the distance you plan to protect and turn the module's
   potentiometer until `flame 1` appears only with the flame, not with direct sunlight on the sensor.
4. **Battery.** Compare `batt` with a multimeter on the cells. If it's off by more than 0.1 V, adjust `BATT_DIVIDER`.

## 6. Test end to end

With the node in normal mode and the backend running:

1. Wait for 4–5 readings (about 20 min) so the node builds its baseline.
2. Hold a lit **incense stick** a few centimetres from the MQ-2 during a reading. The smoke value should jump several times above normal.
3. Optionally, hold a lighter in front of the flame sensor at the same time.
4. A `fire` alert should appear on the dashboard and arrive on Telegram:
   *"🔥 Possível incêndio no nó cerrado-001 … fumaça 6.9x acima da linha de base"*.

While smoke or flame is detected, the node wakes every minute instead of every 5 minutes.

## 7. Enclosure and installation

- **Enclosure:** ESP32, batteries and electronics go inside the IP65 box. Bring cables out through glands and seal them.
- **SHT31 outside, in the radiation shield.** Inside a box in the sun it would read 5–10 °C too high, which ruins FMA+
  and triggers false thermal alarms.
- **MQ-2 needs air:** mount it in a vented opening covered with stainless mesh (insects love these boxes), facing down so rain doesn't get in.
- **Flame sensor:** behind a small opening with mesh, aimed at the area to watch. It doesn't see through the box wall.
- **Solar panel:** facing **north**, tilted at roughly your latitude (e.g. ~15° in Brasília), without shade between 9 h and 15 h.
- **Height:** 1.5–2 m on a pole, above grass but below the canopy.
- **Where:** where fires usually *start*, such as roadsides, firebreaks, property edges and areas with dry grass, and
  where Wi-Fi reaches. Several cheap nodes along an edge beat one perfect node in the middle.
- **Lightning:** on open ground, ground the pole and keep cable runs short.

### Power budget

| Consumer | Average |
|---|---|
| MQ-2 heater (~150 mA for 20 s every 5 min) | ~10 mA |
| ESP32 awake + Wi-Fi (~100 mA for ~25 s every 5 min) | ~8 mA |
| ESP32 DevKit in deep sleep (USB chip and regulator stay on) | ~10 mA |
| **Total** | **~28 mA ≈ 0.7 Ah/day** |

Two 3000 mAh cells give **~8 days without sun**. A 3 W panel easily refills a day's use in a few hours of sun. To go
further, use a board with low sleep current (FireBeetle ESP32, LOLIN D32) or increase `SLEEP_SECONDS_NORMAL`.

## 8. Connectivity

| Option | Status |
|---|---|
| **Wi-Fi** | Supported. Near a farmhouse, a ranger station, or a 4G router with Wi-Fi |
| 4G modem (SIM7600) | Roadmap |
| LoRaWAN AU915 (long range, no internet at the node) | Roadmap: gateway + ChirpStack → `POST /api/readings` |

A practical setup today: a **4G Wi-Fi router** powered by its own solar kit at a high point, covering several nodes nearby.

## 9. Troubleshooting

| Serial monitor shows | Likely cause |
|---|---|
| `SHT31 not found` | SDA/SCL swapped, no 3V3, or the board uses address 0x45 (set `SHT31_ADDR`) |
| `temperature/humidity read failed` | Same as above, or for DHT22: missing pull-up, or wrong pin |
| `Wi-Fi connection failed` | Wrong SSID/password, weak signal, or a 5 GHz-only network (the ESP32 needs 2.4 GHz) |
| `MQTT connection failed (state -2)` | Server not reachable: wrong `MQTT_HOST`/port, firewall, or TLS settings |
| `MQTT connection failed (state 4 or 5)` | Wrong password, or `MQTT_USER` ≠ `NODE_ID`; run `provision.sh node <id>` again |
| Published, but nothing on the dashboard | `NODE_ID` differs from the provisioned user (the broker silently drops the message) |
| `smoke` missing or `nan` | MQ-2 not powered (check the MOSFET and 5 V), or AO not connected |
| `flame 1` all the time | Sensitivity too high or sunlight on the sensor: adjust the potentiometer, check `FLAME_ACTIVE_LOW` |
| `batt 0.00 V` | Battery sense divider not connected to GPIO35 |
| Node resets during Wi-Fi | Weak 5 V supply: check the MT3608 output under load, add a 470 µF capacitor at VIN |
