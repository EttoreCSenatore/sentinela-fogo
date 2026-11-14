---
sidebar_position: 8
title: Deployment
---

# Deployment (self-hosted)

The whole stack runs with Docker Compose on one machine: a small VPS in a Brazilian region, a home server, or a
mini-PC on a farm.

```text
infra/docker-compose.yml
  mosquitto   :1883   authenticated broker with per-node ACLs
  backend     (internal) FastAPI, SQLite in a named volume, backend/config mounted read-only
  dashboard   :8080   nginx, serving the React build and proxying /api to the backend
```

## First run

```bash
cp infra/.env.example infra/.env                 # then edit: Telegram token, etc.
infra/provision.sh backend                       # creates the backend's MQTT user, writes its password to infra/.env
infra/provision.sh node cerrado-001 cerrado-002  # one MQTT user per physical node, prints each password once
cp backend/config/recipients.example.json backend/config/recipients.json   # edit recipients
docker compose -f infra/docker-compose.yml up -d --build
```

Open `http://<server>:8080`.

## Test with simulated nodes

```bash
PASSWORD=devpass infra/provision.sh node cerrado-000 pantanal-001 amazonia-002
backend/.venv/bin/python simulator/simulate.py --nodes 3 --password devpass --fire-at 4
```

Each simulated node logs in as itself, exactly like real hardware would. Node 0 "catches fire" after 4 cycles, and a
`fire` alert appears on the dashboard. Use `--cycles N` to stop after N rounds.

## MQTT security

- `allow_anonymous false`. Every node logs in with **username = node_id**.
- The ACL (`infra/mosquitto/acl`) only lets a node publish to `sentinela/v1/nodes/<its own id>/...`, and only
  the `sentinela-backend` user can read.
- Before exposing the broker to the internet, add a TLS listener on 8883 (Let's Encrypt certificate) and close 1883.
- `infra/mosquitto/passwd` holds only salted hashes and is world-readable so the broker (uid 1883 in the container)
  can read it. On a server, restrict it: `sudo chown 1883:1883 infra/mosquitto/passwd && sudo chmod 600 infra/mosquitto/passwd`
  (after that, `provision.sh` needs `sudo`).

## Production checklist

- [ ] TLS for the dashboard (Caddy or nginx + Let's Encrypt) and for MQTT (8883)
- [ ] Back up the `backend-data` volume (SQLite file) every day
- [ ] Firewall: open only 443 and 8883
- [ ] Set `SENTINELA_TELEGRAM_*` and test with a real alert
- [ ] Watch the backend logs for `INPE poll failed` / `weather fetch failed`

## Postgres

For more than ~100 nodes, or when you need spatial queries, install the Postgres extra (`pip install '.[postgres]'`)
and set `SENTINELA_DATABASE_URL=postgresql+psycopg://user:pass@host/sentinela`. The code supports both databases.
:::note
There are no database migrations yet. Schema changes during development mean recreating the database. Alembic is on
the roadmap.
:::
