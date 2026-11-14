---
sidebar_position: 8
title: Deployment
---

# Deployment (self-hosted)

For alerts to be useful, the system has to run **24/7** on a machine that is always on and reachable from the
internet. This page takes you from an empty server to a running system with HTTPS, encrypted MQTT for sensor nodes, and
daily backups.

```text
infra/docker-compose.prod.yml
  caddy       :80 :443   HTTPS for the dashboard (automatic Let's Encrypt certificate)
  mosquitto   :8883      MQTT over TLS for sensor nodes (reuses Caddy's certificate)
  backend     internal   FastAPI, SQLite in a volume, backend/config mounted read-only
  dashboard   internal   nginx serving the React build, proxying /api to the backend
```

Plain MQTT (1883) and the backend are only reachable inside the Docker network.

## 1. Get a server

Any Linux machine with **1 vCPU, 1–2 GB RAM, 10 GB disk** and a public IP is enough for a pilot. A server in a
Brazilian region keeps latency low.

| Option | Cost | Notes |
|---|---|---|
| **Oracle Cloud "Always Free"** (São Paulo or Vinhedo region) | Free | Ampere (ARM) VM. Sign-up needs a card, and free capacity is sometimes unavailable, so retry or choose another availability domain. Check the current free-tier terms |
| Small VPS from a Brazilian or international provider | ~R$ 30–60/month | Simplest. Pick Ubuntu 24.04 LTS |
| Mini-PC / Raspberry Pi 4/5 at home or on a farm | Hardware only | Needs a fixed public IP or port forwarding for 80, 443 and 8883, and a stable connection |

## 2. Get a domain name

HTTPS certificates need a name, not just an IP.

- **Free:** create a subdomain at [DuckDNS](https://www.duckdns.org) (e.g. `sentinela-chapada.duckdns.org`) and point it at your server's IP.
- **Own domain:** add an `A` record (e.g. `sentinela.example.org`) pointing to the server's IP.

Check it from your computer: `ping sentinela.example.org` should show the server's IP.

## 3. Install

On the server (Ubuntu), as a user with `sudo`:

```bash
# Docker + Compose plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker

# Code
sudo mkdir -p /opt/sentinela && sudo chown $USER /opt/sentinela
git clone https://github.com/EttoreCSenatore/sentinela-fogo.git /opt/sentinela
cd /opt/sentinela

# Configuration
cp infra/.env.example infra/.env
nano infra/.env                       # set DOMAIN=sentinela.example.org (and the Telegram token, see Alerts)
infra/provision.sh backend            # MQTT user for the backend; password goes into infra/.env
cp backend/config/recipients.example.json backend/config/recipients.json   # or use app.cli add-telegram later
```

### Firewall

Open only SSH, HTTP/HTTPS and MQTT-TLS:

```bash
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw allow 8883/tcp
sudo ufw enable
```

:::note Oracle Cloud
On Oracle you must **also** add ingress rules for TCP 80, 443 and 8883 in the VCN's *Security List*. Oracle's Ubuntu
images also ship with `iptables` rules that block everything except SSH. Allow the ports there too, or the site stays unreachable.
:::

### Start

```bash
docker compose -f infra/docker-compose.prod.yml up -d --build
docker compose -f infra/docker-compose.prod.yml logs -f caddy mosquitto     # Ctrl+C to stop following
```

Within a minute Caddy logs `certificate obtained successfully`, and Mosquitto logs `installed certificate …`. Open
`https://<your domain>`: the dashboard loads, and after a few minutes it shows the monitored areas and INPE data.

## 4. Connect sensor nodes

For each node:

```bash
infra/provision.sh node cerrado-001          # prints the node's password once
```

In the node's `secrets.h` (see [Build a sensor node](hardware.md)): `MQTT_HOST` = your domain, `MQTT_USE_TLS 1`,
`MQTT_PORT 8883`, and the Let's Encrypt root certificates as described in the file's comments. The node syncs its clock
over NTP before connecting, which certificate checks require.

To test without hardware, from any computer with the repository:

```bash
backend/.venv/bin/python simulator/simulate.py --host sentinela.example.org --port 8883 --tls \
    --nodes 1 --password <node password> --cycles 3
```

### HTTP ingest (optional: LoRaWAN webhooks, 4G gateways)

`POST /api/readings` is the only public endpoint that writes data, so it is **off by default**. To enable it, create a
secret, put it in `infra/.env`, and restart the backend:

```bash
echo "SENTINELA_INGEST_TOKEN=$(openssl rand -hex 24)" >> infra/.env
docker compose -f infra/docker-compose.prod.yml up -d backend
```

The sender must include it as a header: `X-Ingest-Token: <the token>`. Requests without it get `401`. Without any token
configured the endpoint returns `503`. Sensors using MQTT don't need this.

## 5. Backups

The database (alerts, readings, INPE data) lives in a Docker volume. Back it up every day with cron on the server:

```bash
crontab -e
# add:
0 3 * * * cd /opt/sentinela && docker compose -f infra/docker-compose.prod.yml exec -T backend python -m app.cli backup /data/backups --keep 14
```

The `backup` command makes a consistent copy while the system is running and keeps the newest 14. To keep a copy
**off the server** (recommended), copy the folder out regularly:

```bash
docker compose -f infra/docker-compose.prod.yml cp backend:/data/backups ./backups
# then send ./backups to another machine or storage, e.g. with rsync or rclone
```

Also keep a safe copy of `infra/.env`, `infra/mosquitto/passwd` and `backend/config/recipients.json`. They aren't in git.

**Restore:** stop the backend, copy a backup over `/data/sentinela.db` in the `backend-data` volume, start again.

## 6. Updating

```bash
cd /opt/sentinela
git pull
docker compose -f infra/docker-compose.prod.yml up -d --build
```

:::note
New optional columns are added to an existing database automatically at startup. Other schema changes would need a
migration tool (Alembic is on the roadmap), so take a backup before updating.
:::

## 7. Keeping an eye on it

| Check | How |
|---|---|
| All services up | `docker compose -f infra/docker-compose.prod.yml ps`: the backend shows `(healthy)` |
| Data still flowing | Dashboard header shows `● ao vivo`, and INPE hotspots keep updating |
| Problems | `… logs backend \| grep -E "WARNING\|ERROR"`. Look for `INPE poll failed`, `weather fetch failed`, `Telegram` |
| Alerts reach people | `docker compose … exec backend python -m app.cli test-alert` |

For an outside check, a free uptime monitor (e.g. UptimeRobot) can watch `https://<domain>/api/health` and email
you if it goes down.

## Security notes

- Each node logs in as itself, and the ACL only lets it publish its own data (`infra/mosquitto/acl`).
- `infra/mosquitto/passwd` only contains salted hashes and must be readable by the broker container. On a shared
  server, restrict it: `sudo chown 1883:1883 infra/mosquitto/passwd && sudo chmod 600 infra/mosquitto/passwd` (then
  run `provision.sh` with `sudo`).
- Keep the server updated (`sudo apt upgrade`, or enable unattended upgrades).
- The Telegram bot token, the MQTT passwords, the ingest token and `recipients.json` are secrets: never commit them.
- The dashboard and every `GET` under `/api` are public by design (public awareness). They show sensor locations and alert texts.
- The broker drops MQTT messages larger than 8 KB (`message_size_limit`); real telemetry is about 300 bytes.

## Local / development stack

For development, or a test on your own computer, use the simpler stack (dashboard on port 8080, plain MQTT on 1883):

```bash
cp infra/.env.example infra/.env && infra/provision.sh backend
docker compose -f infra/docker-compose.yml up -d --build
```

## Postgres

For more than ~100 nodes, or when you need spatial queries, use Postgres: set
`SENTINELA_DATABASE_URL=postgresql+psycopg://user:pass@host/sentinela` and install the `postgres` extra
(`pip install '.[postgres]'`, also needed in the backend image). The `backup` command only handles SQLite; use `pg_dump` for Postgres.
