---
sidebar_position: 7
title: Alerts
---

# Alerts

## Alert kinds

| Kind | Trigger | Cooldown |
|---|---|---|
| `fire` | Sensor detection score ≥ 0.6 | 30 min per node |
| `hotspot` | INPE hotspot inside a site's or node's radius | 3 h per area |
| `danger` | FMA+ *alta* or *muito alta* | 1 per day per area |

## Recipients

Recipients are listed in `backend/config/recipients.json`. That file holds phone numbers and chat IDs, so it is
**git-ignored**. Start from `config/recipients.example.json`:

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

- `sites`: site or node IDs, or `"*"` for all of them.
- `kinds`: which alert kinds this recipient wants.
- Every listed channel gets the alert. A failure on one channel doesn't stop the others.

If there is no recipients file, `SENTINELA_TELEGRAM_CHAT_ID` (when set) receives everything. Otherwise alerts are only logged.

## Set up Telegram (step by step)

Telegram is free and is the recommended first channel. It takes about 5 minutes.

**1. Create the bot (in your Telegram app)**

1. Open a chat with [@BotFather](https://t.me/BotFather) and send `/newbot`.
2. Choose a display name (e.g. `Sentinela do Fogo`) and a username ending in `bot` (e.g. `sentinela_fogo_alertas_bot`).
3. BotFather replies with a **token** like `1234567890:AAH...`. Treat it like a password: anyone with it controls the bot.

**2. Save the token**

Add it to `infra/.env` (git-ignored), which both the Docker stack and the CLI read:

```bash
SENTINELA_TELEGRAM_BOT_TOKEN=1234567890:AAH...
```

**3. Talk to the bot**

- Personal alerts: open `https://t.me/<your_bot_username>` and press **Start**.
- Group alerts (recommended for brigades): add the bot to the group and send any message there.

**4. Find the chat ID and register the recipient** (from `backend/`)

```bash
.venv/bin/python -m app.cli telegram-check
#   Bot OK: @sentinela_fogo_alertas_bot
#   Chats that talked to the bot:
#          123456789  private     Ana (@ana)
#     -1001234567890  supergroup  Brigada Chapada

.venv/bin/python -m app.cli add-telegram "Ana" 123456789
.venv/bin/python -m app.cli add-telegram "Brigada Chapada" -1001234567890 --sites chapada-veadeiros --kinds fire hotspot
```

This writes `backend/config/recipients.json`. Run `add-telegram` again with the same chat ID to change its name, sites or kinds.

**5. Send a test alert**

```bash
.venv/bin/python -m app.cli test-alert
#   OK    Ana                      telegram
```

A `FAIL` line shows Telegram's reason (for example `chat not found` if the chat never pressed Start).

**6. Restart the backend** so it picks up the token:

```bash
docker compose -f infra/docker-compose.yml up -d backend    # Docker stack
```

(or restart `uvicorn` if you run it from source).

## Channels

| Channel | Cost | Setup |
|---|---|---|
| **Telegram** | Free | See [Set up Telegram](#set-up-telegram-step-by-step) above |
| **Webhook** | Free | Any URL. Receives `{"node_id", "kind", "score", "message"}` as JSON. Use it to connect Defesa Civil systems, Discord, Slack or n8n |
| **WhatsApp** | Paid per conversation | Meta WhatsApp Cloud API: `SENTINELA_WHATSAPP_TOKEN`, `SENTINELA_WHATSAPP_PHONE_NUMBER_ID`. Messages a business sends first, outside a 24-hour customer window, require an **approved template**. Template support is on the roadmap |
| **SMS** | Paid per message | Twilio: `SENTINELA_TWILIO_ACCOUNT_SID`, `SENTINELA_TWILIO_AUTH_TOKEN`, `SENTINELA_TWILIO_FROM` |

Channels without credentials are skipped and logged, so the system works with Telegram alone.

:::tip Recommended free setup
A Telegram **group** per region (for example "Brigadas Chapada"), with the bot added. Use the group's `chat_id`
(a negative number) as the recipient, so everyone in the group gets the same alert.
:::
