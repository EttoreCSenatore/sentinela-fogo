---
sidebar_position: 2
title: Primeiros passos
---

# Primeiros passos

Você precisa de **Python 3.12+**, **Node.js 20.19+ ou 22+** e, opcionalmente, **Docker** (para o broker MQTT).

## 1. Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q          # roda offline, todo HTTP é simulado
SENTINELA_MQTT_ENABLED=false .venv/bin/python -m uvicorn app.main:app --reload --port 8100
```

Ao iniciar, o backend:

1. cria o `sentinela.db` (SQLite) e registra as áreas piloto de `config/sites.json`;
2. baixa a última hora de focos do INPE e atualiza a cada 10 minutos;
3. carrega 30 dias de clima horário para cada área e atualiza a cada hora.

A documentação da API fica em [http://localhost:8100/docs](http://localhost:8100/docs).

## 2. Painel

```bash
cd dashboard
npm install
npm run dev        # http://localhost:5174, encaminha /api para :8100
```

Clicar em um sensor mostra a leitura mais recente e o score de detecção:

![Popup do sensor com temperatura, umidade, fumaça, chama e FMA+](@site/static/img/screenshots/dashboard-node-popup.png)

O painel é responsivo e funciona no celular:

![Painel no celular](@site/static/img/screenshots/dashboard-mobile.png)

## 3. (Opcional) Sensores simulados via MQTT

```bash
docker compose -f infra/docker-compose.dev.yml up -d      # broker anônimo na porta 1883
# reinicie o backend sem SENTINELA_MQTT_ENABLED=false e então:
backend/.venv/bin/python simulator/simulate.py --nodes 5 --fire-at 3
```

Com `--fire-at 3`, o nó 0 "pega fogo" após 3 ciclos, e você vê um alerta de incêndio ser gerado.

## Configuração

Todas as configurações são variáveis de ambiente com o prefixo `SENTINELA_` (ou um arquivo `.env` em `backend/`).
Veja `backend/.env.example` e `backend/app/config.py`. As mais comuns:

| Variável | Padrão | Significado |
|---|---|---|
| `SENTINELA_DATABASE_URL` | `sqlite:///./sentinela.db` | URL SQLAlchemy (Postgres: `postgresql+psycopg://...`) |
| `SENTINELA_MQTT_ENABLED` | `true` | Assinar o broker MQTT |
| `SENTINELA_INPE_ENABLED` | `true` | Consultar os focos do INPE |
| `SENTINELA_WEATHER_ENABLED` | `true` | Consultar o Open-Meteo para as áreas piloto |
| `SENTINELA_SITES_FILE` | `config/sites.json` | Áreas monitoradas |
| `SENTINELA_RECIPIENTS_FILE` | `config/recipients.json` | Quem recebe quais alertas ([Alertas](alerts.md)) |
