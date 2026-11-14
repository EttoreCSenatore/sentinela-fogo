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

## Channels

| Channel | Cost | Setup |
|---|---|---|
| **Telegram** | Free | Create a bot with @BotFather and set `SENTINELA_TELEGRAM_BOT_TOKEN`. Each recipient sends `/start` to the bot. Their `chat_id` can be read from `https://api.telegram.org/bot<TOKEN>/getUpdates` |
| **Webhook** | Free | Any URL. Receives `{"node_id", "kind", "score", "message"}` as JSON. Use it to connect Defesa Civil systems, Discord, Slack or n8n |
| **WhatsApp** | Paid per conversation | Meta WhatsApp Cloud API: `SENTINELA_WHATSAPP_TOKEN`, `SENTINELA_WHATSAPP_PHONE_NUMBER_ID`. Messages a business sends first, outside a 24-hour customer window, require an **approved template**. Template support is on the roadmap |
| **SMS** | Paid per message | Twilio: `SENTINELA_TWILIO_ACCOUNT_SID`, `SENTINELA_TWILIO_AUTH_TOKEN`, `SENTINELA_TWILIO_FROM` |

Channels without credentials are skipped and logged, so the system works with Telegram alone.

:::tip Recommended free setup
A Telegram **group** per region (for example "Brigadas Chapada"), with the bot added. Use the group's `chat_id`
(a negative number) as the recipient, so everyone in the group gets the same alert.
:::
