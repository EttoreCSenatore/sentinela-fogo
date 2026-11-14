---
title: "ADR 0001: Self-hosted stack"
sidebar_label: "ADR 0001: Self-hosted"
---

# ADR 0001: Self-hosted, open-source stack instead of AWS

- **Status:** accepted (2026-11-14)
- **Context:** The reference project uses AWS IoT Core, Lambda and DynamoDB. Sentinela targets small pilots
  (3–50 nodes) in Brazil, run by a small team on a limited budget, where we'd rather not be locked into one vendor.

## Decision

Run everything on one VPS or local server using Docker Compose:

| Concern | Choice |
|---|---|
| Broker | Mosquitto 2 with a password file + per-node ACLs (TLS on 8883 in production) |
| API / processing | FastAPI (single process: MQTT subscriber + INPE poller + REST) |
| Storage | SQLite (WAL) for pilots, Postgres + PostGIS once there are more than ~100 nodes or we need spatial queries |
| Dashboard | Static Vite build served by nginx, which also proxies `/api` |
| LoRaWAN (later) | ChirpStack (self-hosted) → HTTP integration → `POST /api/readings` |

## Consequences

- Fixed cost (a ~R$30–60/month VPS in a Brazilian region), and the whole system can run offline on a local server at a farm.
- We handle backups, TLS and updates ourselves. The roadmap tracks these as ops tasks.
- AWS stays possible later: the MQTT contract and the HTTP ingest don't change.
