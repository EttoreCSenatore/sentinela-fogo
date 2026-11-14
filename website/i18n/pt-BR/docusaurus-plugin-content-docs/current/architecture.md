---
sidebar_position: 3
title: Arquitetura
---

# Arquitetura

```text
 ┌──────────────┐ MQTT (Wi-Fi/4G)    ┌────────────┐       ┌────────────────────────────────┐
 │ Nó ESP32     │ ─────────────────▶ │ Mosquitto  │ ────▶ │ backend (FastAPI)              │
 │ chama,fumaça │ LoRaWAN AU915      │  broker    │       │  ├ ingest/mqtt.py    sensores  │
 │ temp/UR, GPS │ ─▶ gateway ─▶      └────────────┘       │  ├ ingest/inpe.py    focos     │──▶ Telegram / WhatsApp
 └──────────────┘    ChirpStack ── HTTP ──────────▶       │  ├ ingest/weather.py áreas     │    SMS / webhook
                                                          │  ├ risk/  FMA+ e detecção      │
   INPE BDQueimadas (10 min) ───────────────────────────▶ │  ├ ingest/inpe_risk.py RF+prev │
   Risco de Fogo INPE (diário) ─────────────────────────▶ │  ├ alerts/ roteamento e envio  │
   Open-Meteo (horário) ────────────────────────────────▶ │  └ REST + SSE  /api/...        │
                                                          │     SQLite → Postgres/PostGIS  │
                                                          └───────────────┬────────────────┘
                                                                          │ HTTP + Server-Sent Events
                                                                   ┌──────▼──────┐
                                                                   │ painel      │ React + Leaflet
                                                                   └─────────────┘
```

## Componentes

| Componente | Tecnologia | Papel | Equivalente AWS no projeto de referência |
|---|---|---|---|
| Broker | Mosquitto 2 | Recebe a telemetria dos sensores, com ACL por nó | IoT Core |
| Backend | Python, FastAPI, SQLAlchemy | Ingestão, motor de risco, alertas, API | Lambda + API Gateway |
| Armazenamento | SQLite (WAL) → Postgres/PostGIS | Nós, leituras, focos, alertas | DynamoDB |
| Painel | React, Vite, Leaflet, OpenStreetMap | Mapa ao vivo, áreas, alertas | Painel React |
| Docs | Docusaurus (en, pt-BR) | Este site | — |

## Estrutura do repositório

```text
backend/              Serviço FastAPI + testes
  app/ingest/         mqtt.py, inpe.py, weather.py
  app/risk/           fma.py (FMA+), detect.py (score de detecção dos sensores)
  app/alerts/         dispatch.py (destinatários x canais)
  config/             sites.json, recipients.example.json
dashboard/            Painel React
firmware/esp32-node/  Firmware do sensor (PlatformIO)
simulator/            Nós sensores simulados via MQTT
infra/                docker-compose, configuração/ACL do Mosquitto, script de provisionamento
website/              Esta documentação
```

## Contrato MQTT

Tópico: `sentinela/v1/nodes/{node_id}/telemetry` (QoS 1). **O tópico define o `node_id`**. Qualquer `node_id`
no payload é ignorado, então um nó não consegue enviar dados como se fosse outro.

```json
{
  "ts": "2026-11-14T16:00:00Z",
  "lat": -15.79, "lon": -47.88,
  "temp_c": 34.2, "humidity_pct": 18.0,
  "smoke_ppm": 120.0,
  "flame": false,
  "wind_ms": 3.1,
  "rain_mm": 0.0,
  "battery_v": 3.92
}
```

`ts`, `smoke_ppm`, `wind_ms`, `rain_mm` e `battery_v` são opcionais. `lat`/`lon` vêm do módulo GPS ou de uma
posição fixa no firmware. `sentinela/v1/nodes/{node_id}/status` leva a mensagem retida `online`/`offline`
(last will do MQTT).

O mesmo payload (com `node_id`) pode ser enviado para `POST /api/readings`. Servidores de rede LoRaWAN e gateways 4G usam esse caminho.

## API HTTP

| Método | Caminho | Descrição |
|---|---|---|
| GET | `/api/overview` | Todos os nós/áreas com a última leitura, o perigo FMA+ e o risco + previsão do INPE (uma chamada para o painel) |
| GET | `/api/stream` | Server-Sent Events: eventos `alert` e `reading` em tempo real |
| GET | `/api/nodes` | Nós e áreas |
| GET | `/api/nodes/{id}/readings` | Leituras recentes |
| GET | `/api/nodes/{id}/danger` | Valor e classe do FMA+ |
| GET | `/api/hotspots?hours=24&uf=GO` | Focos do INPE no Brasil, opcionalmente de um estado |
| GET | `/api/alerts` | Últimos alertas |
| POST | `/api/readings` | Ingestão via HTTP |

## Modelo de dados

- `nodes`: id, name, kind (`sensor` / `virtual`), lat, lon, biome, radius_km, last_seen, battery_v
- `readings`: node_id, ts, temp_c, humidity_pct, smoke_ppm, flame, wind_ms, rain_mm, score
- `hotspots`: lat, lon, satellite, ts (únicos por esses quatro campos), uf (estado, pelos limites do IBGE)
- `site_risk`: node_id, kind (`observed` / `forecast`), valid_date, issued_date, rf_mean, rf_max (Risco de Fogo do INPE por área)
- `alerts`: node_id, ts, kind (`fire` / `hotspot` / `danger`), score, message, delivered
