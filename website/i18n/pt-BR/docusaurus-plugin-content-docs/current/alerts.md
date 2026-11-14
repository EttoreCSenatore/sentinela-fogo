---
sidebar_position: 7
title: Alertas
---

# Alertas

## Tipos de alerta

| Tipo | Gatilho | Intervalo mínimo |
|---|---|---|
| `fire` | Score de detecção do sensor ≥ 0,6 | 30 min por nó |
| `hotspot` | Foco do INPE dentro do raio de uma área ou nó | 3 h por área |
| `danger` | FMA+ *alta* ou *muito alta* | 1 por dia por área |

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

## Canais

| Canal | Custo | Configuração |
|---|---|---|
| **Telegram** | Gratuito | Crie um bot com o @BotFather e defina `SENTINELA_TELEGRAM_BOT_TOKEN`. Cada destinatário envia `/start` ao bot. O `chat_id` aparece em `https://api.telegram.org/bot<TOKEN>/getUpdates` |
| **Webhook** | Gratuito | Qualquer URL. Recebe `{"node_id", "kind", "score", "message"}` em JSON. Use para integrar sistemas da Defesa Civil, Discord, Slack ou n8n |
| **WhatsApp** | Pago por conversa | Meta WhatsApp Cloud API: `SENTINELA_WHATSAPP_TOKEN`, `SENTINELA_WHATSAPP_PHONE_NUMBER_ID`. Mensagens que a empresa envia primeiro, fora de uma janela de 24 horas do cliente, exigem um **template aprovado**. O suporte a templates está no roadmap |
| **SMS** | Pago por mensagem | Twilio: `SENTINELA_TWILIO_ACCOUNT_SID`, `SENTINELA_TWILIO_AUTH_TOKEN`, `SENTINELA_TWILIO_FROM` |

Canais sem credenciais são ignorados e registrados no log, então o sistema funciona só com o Telegram.

:::tip Configuração gratuita recomendada
Um **grupo** de Telegram por região (por exemplo, "Brigadas Chapada"), com o bot adicionado. Use o `chat_id` do grupo
(um número negativo) como destinatário, para que todos no grupo recebam o mesmo alerta.
:::
