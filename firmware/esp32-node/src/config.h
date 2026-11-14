#pragma once
// Per-node settings. Copy secrets.example.h to secrets.h (git-ignored) for Wi-Fi/MQTT credentials.
// Hardware guide: website/docs/hardware.md

#include "secrets.h"

// ---- Identity and position -------------------------------------------------------------------
// NODE_ID must match the MQTT user created with: infra/provision.sh node <NODE_ID>
#define NODE_ID        "cerrado-001"
// Fixed position, used when USE_GPS is 0 or the GPS has no fix yet.
#define NODE_LAT       -15.7939
#define NODE_LON       -47.8828

// ---- Sensors (1 = installed, 0 = not installed) ---------------------------------------------
#ifndef TH_SENSOR_SHT31
#define TH_SENSOR_SHT31 1   // 1 = SHT31 (I2C, recommended), 0 = DHT22
#endif
#ifndef USE_MQ2
#define USE_MQ2         1
#endif
#ifndef USE_FLAME
#define USE_FLAME       1
#endif
#ifndef USE_GPS
#define USE_GPS         0   // NEO-6M/NEO-M8N on UART2; position is cached across deep sleep
#endif

// ---- Pins (ESP32 DevKit v1) -------------------------------------------------------------------
#define PIN_I2C_SDA    21   // SHT31
#define PIN_I2C_SCL    22
#define SHT31_ADDR     0x44
#define PIN_DHT        4    // DHT22 data (with 10k pull-up to 3.3 V)
#define PIN_MQ2_AO     34   // ADC1 only (ADC2 can't be used while Wi-Fi is on)
#define PIN_MQ2_HEATER 25   // gate of the logic-level MOSFET that switches the MQ-2 heater
#define PIN_FLAME_DO   27   // KY-026 digital out (LOW = flame on most modules)
#define FLAME_ACTIVE_LOW 1
#define PIN_BATT       35   // battery through a 100k/100k divider
#define BATT_DIVIDER   2.0f
#define PIN_GPS_RX     16   // ESP32 RX  <- GPS TX
#define PIN_GPS_TX     17   // ESP32 TX  -> GPS RX
#define GPS_BAUD       9600

// ---- MQ-2 smoke sensor ---------------------------------------------------------------------
#define MQ2_VCC        5.0f    // module supply voltage (most boards: 5 V)
#define MQ2_DIVIDER    1.5f    // AO -> 10k -> GPIO34 -> 20k -> GND gives Vao/1.5; set 1.0 without a divider
#define MQ2_RL_KOHM    5.0f    // load resistor on the module (usually 5k or 10k; check the board)
#define MQ2_R0_KOHM    9.8f    // CALIBRATE: run CALIBRATION_MODE in clean air and copy the value it prints
#define MQ2_WARMUP_MS  20000   // heater preheat before each sample (longer = more stable)
#define SMOKE_FAST_PPM 300.0f  // above this, wake up more often

// ---- Timing ---------------------------------------------------------------------------------
#define SLEEP_SECONDS_NORMAL 300   // 5 min between readings
#define SLEEP_SECONDS_ALERT   60   // while smoke/flame is detected
#define WIFI_TIMEOUT_MS    15000
#define GPS_FIX_TIMEOUT_S    120   // first boot only; later wakes reuse the cached fix

// ---- Calibration / bench mode ---------------------------------------------------------------
// 1 = never sleep, no network; print readings and the MQ-2 R0 estimate every 2 s on the serial monitor.
#ifndef CALIBRATION_MODE
#define CALIBRATION_MODE 0
#endif
