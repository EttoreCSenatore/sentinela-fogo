---
sidebar_position: 8
title: Implantação
---

# Implantação (servidor próprio)

A stack inteira roda com Docker Compose em uma única máquina: uma VPS pequena em região brasileira, um servidor em
casa ou um mini-PC na fazenda.

```text
infra/docker-compose.yml
  mosquitto   :1883   broker autenticado, com ACL por nó
  backend     (interno) FastAPI, SQLite em volume nomeado
  dashboard   :8080   nginx, servindo o build do React e encaminhando /api para o backend
```

## Primeira execução

```bash
cp infra/.env.example infra/.env                 # depois edite: token do Telegram etc.
infra/provision.sh backend                       # cria o usuário MQTT do backend e grava a senha em infra/.env
infra/provision.sh node cerrado-001 cerrado-002  # um usuário MQTT por nó físico; mostra cada senha uma única vez
cp backend/config/recipients.example.json backend/config/recipients.json   # edite os destinatários
docker compose -f infra/docker-compose.yml up -d --build
```

Acesse `http://<servidor>:8080`.

## Segurança do MQTT

- `allow_anonymous false`. Cada nó se autentica com **usuário = node_id**.
- A ACL (`infra/mosquitto/acl`) só permite que um nó publique em `sentinela/v1/nodes/<seu próprio id>/...`, e
  apenas o usuário `sentinela-backend` pode ler.
- Antes de expor o broker à internet, adicione um listener TLS na porta 8883 (certificado Let's Encrypt) e feche a 1883.

## Checklist de produção

- [ ] TLS no painel (Caddy ou nginx + Let's Encrypt) e no MQTT (8883)
- [ ] Backup diário do volume `backend-data` (arquivo SQLite)
- [ ] Firewall: abrir apenas 443 e 8883
- [ ] Definir `SENTINELA_TELEGRAM_*` e testar com um alerta real
- [ ] Acompanhar os logs do backend por `INPE poll failed` / `weather fetch failed`

## Postgres

Para mais de ~100 nós, ou quando precisar de consultas espaciais, instale o extra de Postgres (`pip install '.[postgres]'`)
e defina `SENTINELA_DATABASE_URL=postgresql+psycopg://usuario:senha@host/sentinela`. O código funciona com os dois bancos.
:::note
Ainda não há migrações de banco. Mudanças de esquema durante o desenvolvimento exigem recriar o banco. O Alembic está
no roadmap.
:::
