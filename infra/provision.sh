#!/usr/bin/env bash
# Create or update MQTT credentials. Usage:
#   infra/provision.sh backend              -> sentinela-backend user, writes MQTT password into infra/.env
#   infra/provision.sh node cerrado-001 ... -> node users, prints each password once (put it in the node's secrets.h)
# Set PASSWORD=... to use a fixed password instead of a random one (dev/simulator only).
set -euo pipefail
cd "$(dirname "$0")"
PASSWD=mosquitto/passwd
touch "$PASSWD"

set_user() {  # user password
  docker run --rm -v "$PWD/mosquitto:/m" eclipse-mosquitto:2 mosquitto_passwd -b /m/passwd "$1" "$2"
}
gen() { echo "${PASSWORD:-$(head -c 18 /dev/urandom | base64 | tr -d '/+=')}"; }

case "${1:-}" in
  backend)
    pw=$(gen); set_user sentinela-backend "$pw"
    touch .env; grep -v '^SENTINELA_MQTT_PASSWORD=' .env > .env.tmp || true; mv .env.tmp .env
    echo "SENTINELA_MQTT_PASSWORD=$pw" >> .env
    echo "backend user written; password stored in infra/.env" ;;
  node)
    shift; [ $# -gt 0 ] || { echo "node ids required" >&2; exit 1; }
    for id in "$@"; do
      [[ "$id" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "bad node id: $id" >&2; exit 1; }
      pw=$(gen); set_user "$id" "$pw"; echo "$id  $pw"
    done ;;
  *) sed -n '2,6p' "$0"; exit 1 ;;
esac
