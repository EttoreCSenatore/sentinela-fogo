---
title: "ADR 0001: Stack própria"
sidebar_label: "ADR 0001: Stack própria"
---

# ADR 0001: Stack própria e de código aberto em vez da AWS

- **Status:** aceito (14/11/2026)
- **Contexto:** o projeto de referência usa AWS IoT Core, Lambda e DynamoDB. O Sentinela é voltado a pilotos pequenos
  (3–50 nós) no Brasil, tocados por uma equipe pequena com orçamento limitado, e preferimos não ficar presos a um único fornecedor.

## Decisão

Rodar tudo em uma VPS ou servidor local com Docker Compose:

| Aspecto | Escolha |
|---|---|
| Broker | Mosquitto 2 com arquivo de senhas + ACL por nó (TLS na porta 8883 em produção) |
| API / processamento | FastAPI (um único processo: assinante MQTT + coletor do INPE + REST) |
| Armazenamento | SQLite (WAL) nos pilotos; Postgres + PostGIS acima de ~100 nós ou quando precisarmos de consultas espaciais |
| Painel | Build estático do Vite servido pelo nginx, que também encaminha `/api` |
| LoRaWAN (depois) | ChirpStack (servidor próprio) → integração HTTP → `POST /api/readings` |

## Consequências

- Custo fixo (uma VPS de ~R$ 30–60/mês em região brasileira), e o sistema inteiro pode rodar offline em um servidor local na fazenda.
- Backups, TLS e atualizações ficam por nossa conta. O roadmap acompanha essas tarefas de operação.
- A AWS continua possível no futuro: o contrato MQTT e a ingestão HTTP não mudam.
