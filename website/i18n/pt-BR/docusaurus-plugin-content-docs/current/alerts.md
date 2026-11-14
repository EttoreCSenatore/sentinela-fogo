---
sidebar_position: 7
title: Alertas
---

# Alertas

Um incêndio detectado aparece no mapa do painel e na lista de alertas ao mesmo tempo em que é enviado aos destinatários:

![Um alerta de incêndio no painel lateral](@site/static/img/screenshots/dashboard-node-popup.png)

## Tipos de alerta

| Tipo | Gatilho | Intervalo mínimo |
|---|---|---|
| `fire` | Score de detecção do sensor ≥ 0,6 | 30 min por nó |
| `hotspot` | Foco do INPE dentro do raio de uma área ou nó | 3 h por área |
| `danger` | Risco de Fogo do INPE *Alto*/*Crítico* hoje ou previsto para os próximos 3 dias (FMA+ se o INPE não tiver dados). Veja [Modelo de risco](risk-model.md#alertas-de-perigo-inpe-primeiro-fma-junto) | 1 por dia por área |

## Destinatários

Os destinatários ficam em `backend/config/recipients.json`. Esse arquivo contém números de telefone e chat IDs,
por isso é **ignorado pelo git**. Comece a partir de `config/recipients.example.json`:

```json
{
  "recipients": [
    {"name": "Coordenação", "channels": {"telegram": "123456789"}, "sites": ["*"], "kinds": ["fire", "hotspot", "danger"]},
    {"name": "Brigada Chapada", "channels": {"whatsapp": "+5562999990000", "sms": "+5562999990000"},
     "sites": ["chapada-veadeiros"], "kinds": ["fire", "hotspot"]},
    {"name": "Defesa Civil GO", "channels": {"webhook": "https://example.org/hooks/sentinela"},
     "sites": ["chapada-veadeiros"], "kinds": ["fire"]}
  ]
}
```

- `sites`: IDs de áreas ou nós, ou `"*"` para todos.
- `kinds`: quais tipos de alerta esse destinatário quer receber.
- Cada canal listado recebe o alerta. Uma falha em um canal não impede os outros.

Se não houver arquivo de destinatários, `SENTINELA_TELEGRAM_CHAT_ID` (quando definido) recebe tudo. Caso contrário, os alertas apenas vão para o log.

## Configurar o Telegram (passo a passo)

O Telegram é gratuito e é o canal recomendado para começar. Leva uns 5 minutos.

**1. Crie o bot (no seu app do Telegram)**

1. Abra uma conversa com o [@BotFather](https://t.me/BotFather) e envie `/newbot`.
2. Escolha um nome de exibição (ex.: `Sentinela do Fogo`) e um nome de usuário terminado em `bot` (ex.: `sentinela_fogo_alertas_bot`).
3. O BotFather responde com um **token** como `1234567890:AAH...`. Trate-o como uma senha: quem tiver o token controla o bot.

**2. Guarde o token**

Adicione-o ao `infra/.env` (ignorado pelo git), que é lido tanto pela stack Docker quanto pela CLI:

```bash
SENTINELA_TELEGRAM_BOT_TOKEN=1234567890:AAH...
```

**3. Converse com o bot**

- Alertas pessoais: abra `https://t.me/<usuario_do_seu_bot>` e toque em **Começar** (Start).
- Alertas em grupo (recomendado para brigadas): adicione o bot ao grupo e envie qualquer mensagem lá.

**4. Descubra o chat ID e cadastre o destinatário** (a partir de `backend/`)

Se o backend já estiver rodando com o token, o bot responde ao `/start` com o chat ID. Caso contrário, use a CLI:

```bash
.venv/bin/python -m app.cli telegram-check
#   Bot OK: @sentinela_fogo_alertas_bot
#   Chats that talked to the bot:
#          123456789  private     Ana (@ana)
#     -1001234567890  supergroup  Brigada Chapada

.venv/bin/python -m app.cli add-telegram "Ana" 123456789
.venv/bin/python -m app.cli add-telegram "Brigada Chapada" -1001234567890 --sites chapada-veadeiros --kinds fire hotspot
```

Isso grava o `backend/config/recipients.json`. Rode o `add-telegram` de novo com o mesmo chat ID para mudar o nome, as áreas ou os tipos.

**5. Envie um alerta de teste**

```bash
.venv/bin/python -m app.cli test-alert
#   OK    Ana                      telegram
```

Uma linha `FAIL` mostra o motivo informado pelo Telegram (por exemplo, `chat not found` se o chat nunca tocou em Começar).

**6. Reinicie o backend** para ele carregar o token:

```bash
docker compose -f infra/docker-compose.yml up -d backend    # stack Docker
```

(ou reinicie o `uvicorn`, se estiver rodando a partir do código).

### Comandos do bot

Enquanto o backend estiver rodando, o bot responde em qualquer chat:

| Comando | Resposta |
|---|---|
| `/start` | O chat ID e se este chat já recebe alertas |
| `/status` | Risco do INPE hoje, previsão do INPE para os próximos dias e FMA+ de cada área monitorada |
| `/ajuda` | Lista de comandos |

O bot nunca cadastra ninguém sozinho: um administrador adiciona os destinatários com `add-telegram`. O Telegram
permite que apenas um programa leia as mensagens de um bot por vez, então, com o backend rodando, o `telegram-check`
não lista chats novos.

## Canais

| Canal | Custo | Configuração |
|---|---|---|
| **Telegram** | Gratuito | Veja [Configurar o Telegram](#configurar-o-telegram-passo-a-passo) acima |
| **Webhook** | Gratuito | Qualquer URL. Recebe `{"node_id", "kind", "score", "message"}` em JSON. Use para integrar sistemas da Defesa Civil, Discord, Slack ou n8n |
| **WhatsApp** | Pago por conversa | Meta WhatsApp Cloud API: `SENTINELA_WHATSAPP_TOKEN`, `SENTINELA_WHATSAPP_PHONE_NUMBER_ID`. Mensagens que a empresa envia primeiro, fora de uma janela de 24 horas do cliente, exigem um **template aprovado**. O suporte a templates está no roadmap |
| **SMS** | Pago por mensagem | Twilio: `SENTINELA_TWILIO_ACCOUNT_SID`, `SENTINELA_TWILIO_AUTH_TOKEN`, `SENTINELA_TWILIO_FROM` |

Canais sem credenciais são ignorados e registrados no log, então o sistema funciona só com o Telegram.

:::tip Configuração gratuita recomendada
Um **grupo** de Telegram por região (por exemplo, "Brigadas Chapada"), com o bot adicionado. Use o `chat_id` do grupo
(um número negativo) como destinatário, para que todos no grupo recebam o mesmo alerta.
:::
