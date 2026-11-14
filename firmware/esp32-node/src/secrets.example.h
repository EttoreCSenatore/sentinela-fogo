#pragma once
// Copy to secrets.h (git-ignored) and fill in.
#define WIFI_SSID     "your-ssid"
#define WIFI_PASSWORD "your-password"

#define MQTT_HOST     "192.168.0.10"   // server IP or domain (e.g. mqtt.example.org)
#define MQTT_USER     NODE_ID          // must equal NODE_ID (the broker ACL depends on it)
#define MQTT_PASSWORD "printed-by-provision.sh"

// Plain MQTT on a local network:
#define MQTT_USE_TLS  0
#define MQTT_PORT     1883

// Internet-facing server (see the Deployment docs): set MQTT_USE_TLS 1, port 8883, and paste the CA
// certificate that signed the broker's certificate. For Let's Encrypt that is ISRG Root X1:
//   curl -s https://letsencrypt.org/certs/isrgrootx1.pem
// #define MQTT_USE_TLS 1
// #define MQTT_PORT    8883
// static const char MQTT_CA_CERT[] = R"PEM(
// -----BEGIN CERTIFICATE-----
// ...
// -----END CERTIFICATE-----
// )PEM";
