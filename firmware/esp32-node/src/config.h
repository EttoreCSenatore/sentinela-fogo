#pragma once

// Copy secrets.example.h to secrets.h and fill in your values (secrets.h is git-ignored).
#include "secrets.h"

#define NODE_ID        "cerrado-001"
#define NODE_LAT       -15.7939
#define NODE_LON       -47.8828

#define PIN_DHT        4
#define PIN_MQ2_AO     34   // ADC1 only (ADC2 is unusable while Wi-Fi is on)
#define PIN_MQ2_HEATER 25   // MOSFET gate
#define PIN_FLAME_DO   27   // active LOW on most KY-026 modules
#define PIN_BATT       35   // 100k/100k divider

#define MQ2_WARMUP_MS  20000      // heater preheat before each sample
#define MQ2_RL_KOHM    5.0
#define MQ2_R0_KOHM    9.8        // TODO: calibrate in clean air (Rs/R0 ≈ 9.8 in clean air)

#define SLEEP_SECONDS_NORMAL 300  // 5 min
#define SLEEP_SECONDS_ALERT   60  // faster cadence while smoke/flame is detected
