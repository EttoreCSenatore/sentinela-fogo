#!/bin/sh
# Runs Mosquitto with the TLS certificate Caddy obtained for $DOMAIN.
# Waits for the first certificate, then checks every 12 h and restarts the broker when Caddy has renewed it
# (nodes reconnect on their next wake-up).
set -eu
: "${DOMAIN:?DOMAIN must be set}"
CERTS=/mosquitto/certs
mkdir -p "$CERTS"

find_cert() { find /caddy-data/caddy/certificates -type f -name "$DOMAIN.crt" 2>/dev/null | head -n 1; }

copy_cert() {  # returns 0 when a (new) certificate was installed
  crt=$(find_cert)
  [ -n "$crt" ] || return 1
  if [ -f "$CERTS/server.crt" ] && cmp -s "$crt" "$CERTS/server.crt"; then return 1; fi
  cp "$crt" "$CERTS/server.crt"
  cp "${crt%.crt}.key" "$CERTS/server.key"
  chown mosquitto:mosquitto "$CERTS/server.crt" "$CERTS/server.key"
  chmod 600 "$CERTS/server.key"
  echo "installed certificate $crt"
}

echo "waiting for Caddy to obtain a certificate for $DOMAIN ..."
until copy_cert || [ -f "$CERTS/server.crt" ]; do sleep 5; done

pid=0
start() { mosquitto -c /mosquitto/config/mosquitto.conf & pid=$!; }
stop() { [ "$pid" -ne 0 ] && kill -TERM "$pid" 2>/dev/null && wait "$pid" 2>/dev/null || true; }
trap 'stop; exit 0' TERM INT

start
while :; do
  sleep "${CERT_CHECK_SECONDS:-43200}" & wait $! || true
  if ! kill -0 "$pid" 2>/dev/null; then echo "mosquitto exited; restarting"; start; continue; fi
  if copy_cert; then echo "certificate renewed; restarting mosquitto"; stop; start; fi
done
