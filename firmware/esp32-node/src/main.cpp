// Sentinela do Fogo: sensor node v1
// Each cycle: wake -> heat MQ-2 -> read sensors -> publish over MQTT -> deep sleep.
// Build guide: website/docs/hardware.md
#include <Arduino.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <Wire.h>

#include "config.h"

#if TH_SENSOR_SHT31
#include <Adafruit_SHT31.h>
Adafruit_SHT31 sht31;
#else
#include <DHT.h>
DHT dht(PIN_DHT, DHT22);
#endif

#if USE_GPS
#include <TinyGPSPlus.h>
TinyGPSPlus gps;
HardwareSerial gpsSerial(2);
#endif

#if MQTT_USE_TLS
WiFiClientSecure net;
#else
WiFiClient net;
#endif
PubSubClient mqtt(net);

static const char* TELEMETRY_TOPIC = "sentinela/v1/nodes/" NODE_ID "/telemetry";
static const char* STATUS_TOPIC = "sentinela/v1/nodes/" NODE_ID "/status";

// Survives deep sleep (lost on power loss, then the GPS fix is taken again).
RTC_DATA_ATTR double cachedLat = NODE_LAT;
RTC_DATA_ATTR double cachedLon = NODE_LON;
RTC_DATA_ATTR bool hasGpsFix = false;
RTC_DATA_ATTR uint32_t bootCount = 0;

struct Readings {
  float tempC = NAN;
  float humidity = NAN;
  float smokePpm = NAN;
  float mq2Rs = NAN;
  bool flame = false;
  float batteryV = NAN;
};

// ---------------------------------------------------------------- sensors

static void readTempHumidity(Readings& r) {
#if TH_SENSOR_SHT31
  r.tempC = sht31.readTemperature();
  r.humidity = sht31.readHumidity();
#else
  r.tempC = dht.readTemperature();
  r.humidity = dht.readHumidity();
#endif
}

// Smoke curve from the MQ-2 datasheet (log-log line through ~200 ppm @ Rs/R0 3.4 and ~10000 ppm @ 0.6).
// Cheap gas sensors are not accurate in absolute ppm; the backend compares each reading with the node's own
// rolling baseline, so what matters is that the value rises when there is smoke.
static constexpr float SMOKE_M = -0.444f;
static constexpr float SMOKE_B = 1.553f;

static void readMq2(Readings& r) {
#if USE_MQ2
  uint32_t mv = 0;
  for (int i = 0; i < 16; i++) {
    mv += analogReadMilliVolts(PIN_MQ2_AO);
    delay(5);
  }
  float vAo = (mv / 16.0f) / 1000.0f * MQ2_DIVIDER;  // voltage at the module's AO pin
  if (vAo < 0.01f) return;                           // sensor not connected / heater off
  r.mq2Rs = MQ2_RL_KOHM * (MQ2_VCC - vAo) / vAo;
  float ratio = r.mq2Rs / MQ2_R0_KOHM;
  r.smokePpm = powf(10.0f, (log10f(ratio) - SMOKE_B) / SMOKE_M);
#endif
}

static void readFlame(Readings& r) {
#if USE_FLAME
  int v = digitalRead(PIN_FLAME_DO);
  r.flame = FLAME_ACTIVE_LOW ? (v == LOW) : (v == HIGH);
#endif
}

static void readBattery(Readings& r) {
  r.batteryV = analogReadMilliVolts(PIN_BATT) * BATT_DIVIDER / 1000.0f;
}

static void updateGps() {
#if USE_GPS
  if (hasGpsFix) return;  // fixed node: one good fix per power-up is enough
  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, PIN_GPS_RX, PIN_GPS_TX);
  uint32_t until = millis() + GPS_FIX_TIMEOUT_S * 1000UL;
  while (millis() < until) {
    while (gpsSerial.available()) gps.encode(gpsSerial.read());
    if (gps.location.isValid() && gps.location.age() < 2000 && gps.hdop.isValid() && gps.hdop.hdop() < 3.0) {
      cachedLat = gps.location.lat();
      cachedLon = gps.location.lng();
      hasGpsFix = true;
      Serial.printf("GPS fix: %.6f, %.6f (hdop %.1f)\n", cachedLat, cachedLon, gps.hdop.hdop());
      break;
    }
    delay(10);
  }
  if (!hasGpsFix) Serial.println("GPS: no fix yet, using NODE_LAT/NODE_LON");
  gpsSerial.end();
#endif
}

// ---------------------------------------------------------------- network

static bool connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  uint32_t until = millis() + WIFI_TIMEOUT_MS;
  while (WiFi.status() != WL_CONNECTED && millis() < until) delay(250);
  return WiFi.status() == WL_CONNECTED;
}

// Real time is needed to validate TLS certificates, and lets us timestamp readings.
static bool syncClock() {
  configTime(0, 0, "a.st1.ntp.br", "pool.ntp.org");
  uint32_t until = millis() + 10000;
  while (time(nullptr) < 1700000000 && millis() < until) delay(100);
  return time(nullptr) >= 1700000000;
}

static bool connectMqtt() {
#if MQTT_USE_TLS
  net.setCACert(MQTT_CA_CERT);
#endif
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setBufferSize(512);
  return mqtt.connect(NODE_ID, MQTT_USER, MQTT_PASSWORD, STATUS_TOPIC, 1, true, "offline");
}

static bool publish(const Readings& r) {
  JsonDocument doc;
  time_t now = time(nullptr);
  if (now >= 1700000000) {
    char ts[25];
    strftime(ts, sizeof ts, "%Y-%m-%dT%H:%M:%SZ", gmtime(&now));
    doc["ts"] = ts;
  }
  doc["lat"] = cachedLat;
  doc["lon"] = cachedLon;
  doc["temp_c"] = r.tempC;
  doc["humidity_pct"] = r.humidity;
  if (!isnan(r.smokePpm)) doc["smoke_ppm"] = r.smokePpm;
  doc["flame"] = r.flame;
  doc["battery_v"] = r.batteryV;
  char buf[384];
  size_t n = serializeJson(doc, buf);
  bool ok = mqtt.publish(STATUS_TOPIC, "online", true) &&
            mqtt.publish(TELEMETRY_TOPIC, reinterpret_cast<const uint8_t*>(buf), n, false);
  mqtt.loop();
  delay(200);
  Serial.printf("%s: %s\n", ok ? "published" : "publish FAILED", buf);
  return ok;
}

// ---------------------------------------------------------------- lifecycle

static void initSensors() {
  pinMode(PIN_MQ2_HEATER, OUTPUT);
  digitalWrite(PIN_MQ2_HEATER, LOW);
#if USE_FLAME
  pinMode(PIN_FLAME_DO, INPUT);
#endif
  analogReadResolution(12);
  analogSetPinAttenuation(PIN_MQ2_AO, ADC_11db);  // full 0-3.3 V range
  analogSetPinAttenuation(PIN_BATT, ADC_11db);
#if TH_SENSOR_SHT31
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  if (!sht31.begin(SHT31_ADDR)) Serial.println("SHT31 not found: check wiring and address");
#else
  dht.begin();
#endif
}

static void sleepFor(uint32_t seconds) {
  Serial.printf("sleeping %u s\n", seconds);
  Serial.flush();
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  esp_sleep_enable_timer_wakeup(static_cast<uint64_t>(seconds) * 1000000ULL);
  esp_deep_sleep_start();
}

#if CALIBRATION_MODE
void setup() {
  Serial.begin(115200);
  delay(500);
  initSensors();
  digitalWrite(PIN_MQ2_HEATER, HIGH);
  Serial.println("CALIBRATION MODE: heater on. Leave in clean air for 24-48 h on first use, then let readings settle.");
}

void loop() {
  Readings r;
  readTempHumidity(r);
  readMq2(r);
  readFlame(r);
  readBattery(r);
  Serial.printf("T %.1f C  RH %.0f %%  MQ2 Rs %.2f kOhm -> R0 (clean air) = %.2f  smoke %.0f ppm  flame %d  batt %.2f V\n",
                r.tempC, r.humidity, r.mq2Rs, r.mq2Rs / 9.8f, r.smokePpm, r.flame, r.batteryV);
  delay(2000);
}
#else
void setup() {
  Serial.begin(115200);
  bootCount++;
  Serial.printf("\nSentinela node %s, boot %u\n", NODE_ID, bootCount);
  initSensors();

  // Heat the MQ-2 while the other slow things (GPS) happen.
  digitalWrite(PIN_MQ2_HEATER, HIGH);
  uint32_t heaterOn = millis();
  updateGps();
  while (millis() - heaterOn < MQ2_WARMUP_MS) delay(100);

  Readings r;
  readTempHumidity(r);
  readMq2(r);
  readFlame(r);
  readBattery(r);
  digitalWrite(PIN_MQ2_HEATER, LOW);

  bool suspicious = r.flame || (!isnan(r.smokePpm) && r.smokePpm > SMOKE_FAST_PPM);
  uint32_t sleepS = suspicious ? SLEEP_SECONDS_ALERT : SLEEP_SECONDS_NORMAL;

  if (isnan(r.tempC) || isnan(r.humidity)) {
    Serial.println("temperature/humidity read failed: skipping this cycle");
  } else if (!connectWifi()) {
    Serial.println("Wi-Fi connection failed");
  } else if (!syncClock() && MQTT_USE_TLS) {
    Serial.println("NTP time sync failed: needed to validate the TLS certificate");
  } else if (!connectMqtt()) {
    Serial.printf("MQTT connection failed (state %d): check host, port, user = NODE_ID and password\n", mqtt.state());
  } else {
    publish(r);
    mqtt.disconnect();
  }
  sleepFor(sleepS);
}

void loop() {}
#endif
