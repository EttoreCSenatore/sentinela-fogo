---
sidebar_position: 10
title: Roadmap
---

# Roadmap

## Fase 0: Fundação ✅
- [x] Backend: ingestão MQTT, INPE e clima, FMA+ e motor de detecção, API REST + SSE, testes
- [x] Estações virtuais para as áreas piloto (sem hardware)
- [x] Alertas para vários destinatários: Telegram, webhook, WhatsApp, SMS
- [x] Painel: mapa, áreas por nível de perigo, alertas, atualização ao vivo
- [x] Stack Docker própria com broker MQTT autenticado
- [x] Simulador de sensores, esqueleto do firmware ESP32
- [x] Documentação bilíngue (en / pt-BR)

## Fase 1: Sem hardware (agora)
- [ ] Validar as constantes da FMA+ com Nunes et al. (2006); comparar com o *Risco de Fogo* do INPE
- [ ] Filtro preciso pela fronteira do Brasil e por bioma (IBGE), descartando focos fora do país
- [ ] Áreas automáticas a partir das unidades de conservação do ICMBio
- [ ] Migrações de banco (Alembic)
- [ ] Visão pública vs. visão de resposta: confirmação de alertas e anotações para as brigadas
- [ ] Gráficos de histórico por área (FMA+ e clima ao longo do tempo)
- [ ] Mensagens de WhatsApp com template
- [ ] Implantar em uma VPS com TLS; enviar um alerta de Telegram para um grupo real

## Fase 2: Primeiro nó físico
- [ ] Montar a lista de materiais, calibrar o MQ-2, testar bateria e solar em campo
- [ ] Desvios de calibração por nó no backend
- [ ] Suporte a GPS no firmware

## Fase 3: Rede piloto
- [ ] Gateway LoRaWAN AU915 + ChirpStack → ingestão HTTP
- [ ] Postgres + PostGIS
- [ ] Atualização de firmware OTA
- [ ] Nós com câmera + modelo aberto de detecção de fumaça
