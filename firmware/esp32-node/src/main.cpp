// Sentinela do Fogo: sensor node v1 (Wi-Fi + MQTT, deep sleep)
// Cycle: wake -> heat MQ-2 -> sample -> publish -> sleep.
#include <Arduino.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <PubSubClient.h>
#include <WiFi.h>

#include "config.h"

DHT dht(PIN_DHT, DHT22);
WiFiClient net;
PubSubClient mqtt(net);

static const char* TELEMETRY_TOPIC = "sentinela/v1/nodes/" NODE_ID "/telemetry";
static const char* STATUS_TOPIC    = "sentinela/v1/nodes/" NODE_ID "/status";

static float readMq2Ppm() {
  int raw = 0;
  for (int i = 0; i < 16; i++) { raw += analogRead(PIN_MQ2_AO); delay(5); }
  float v = (raw / 16.0f) / 4095.0f * 3.3f;
  if (v < 0.01f) return 0;
  float rs = MQ2_RL_KOHM * (3.3f - v) / v;
  float ratio = rs / MQ2_R0_KOHM;
  // Smoke curve from MQ-2 datasheet (log-log fit). Approximate: treat it as a relative indicator.
  return powf(10.0f, (log10f(ratio) - 0.53f) / -0.44f) * 100.0f;
}

static float readBatteryV() {
  return analogReadMilliVolts(PIN_BATT) * 2.0f / 1000.0f;
}

static bool connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(250);
  return WiFi.status() == WL_CONNECTED;
}

static bool connectMqtt() {
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setBufferSize(512);
  return mqtt.connect(NODE_ID, MQTT_USER, MQTT_PASSWORD, STATUS_TOPIC, 1, true, "offline");
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_MQ2_HEATER, OUTPUT);
  pinMode(PIN_FLAME_DO, INPUT);
  analogReadResolution(12);
  dht.begin();

  digitalWrite(PIN_MQ2_HEATER, HIGH);
  delay(MQ2_WARMUP_MS);

  float t = dht.readTemperature();
  float h = dht.readHumidity();
  float smoke = readMq2Ppm();
  bool flame = digitalRead(PIN_FLAME_DO) == LOW;
  digitalWrite(PIN_MQ2_HEATER, LOW);

  bool suspicious = flame || smoke > 300;
  uint32_t sleepS = suspicious ? SLEEP_SECONDS_ALERT : SLEEP_SECONDS_NORMAL;

  if (!isnan(t) && !isnan(h) && connectWifi() && connectMqtt()) {
    JsonDocument doc;
    doc["lat"] = NODE_LAT;
    doc["lon"] = NODE_LON;
    doc["temp_c"] = t;
    doc["humidity_pct"] = h;
    doc["smoke_ppm"] = smoke;
    doc["flame"] = flame;
    doc["battery_v"] = readBatteryV();
    char buf[384];
    size_t n = serializeJson(doc, buf);
    mqtt.publish(STATUS_TOPIC, "online", true);
    mqtt.publish(TELEMETRY_TOPIC, (const uint8_t*)buf, n, false);
    mqtt.loop();
    delay(200);
    mqtt.disconnect();
    Serial.printf("published: %s\n", buf);
  } else {
    Serial.println("sensor or network failure; sleeping");
  }

  WiFi.disconnect(true);
  esp_sleep_enable_timer_wakeup((uint64_t)sleepS * 1000000ULL);
  esp_deep_sleep_start();
}

void loop() {}
