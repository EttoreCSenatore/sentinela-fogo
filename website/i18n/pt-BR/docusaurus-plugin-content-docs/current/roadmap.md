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
- [x] Validar as constantes da FMA+ com Nunes et al. (2006); comparar com o *Risco de Fogo* do INPE ([resultados](validation.md))
- [x] Usar o *Risco de Fogo* do INPE (observado + previsão de 0 a 3 dias) como segunda fonte de perigo por área
- [ ] Calibrar as classes da FMA+ por bioma (percentis da FMA+ nos dias com focos do INPE por perto)
- [x] Filtro preciso pela fronteira do Brasil (estados do IBGE): focos fora do país são descartados e marcados com a UF
- [ ] Limites dos biomas (IBGE) para estatísticas por bioma
- [ ] Áreas automáticas a partir das unidades de conservação do ICMBio
- [ ] Migrações de banco (Alembic)
- [ ] Visão pública vs. visão de resposta: confirmação de alertas e anotações para as brigadas
- [ ] Gráficos de histórico por área (FMA+ e clima ao longo do tempo)
- [ ] Mensagens de WhatsApp com template
- [x] Stack de produção: HTTPS (Caddy), MQTT com TLS, backups, guia de implantação
- [ ] Implantar num servidor de verdade; enviar um alerta de Telegram para um grupo real

## Fase 2: Primeiro nó físico
- [ ] Montar a lista de materiais, calibrar o MQ-2, testar bateria e solar em campo
- [ ] Desvios de calibração por nó no backend
- [x] Suporte a GPS no firmware (mais escolha SHT31/DHT22, modo de calibração, MQTT com TLS)
- [x] Guia de montagem passo a passo ([Monte um nó sensor](hardware.md))

## Fase 3: Rede piloto
- [ ] Gateway LoRaWAN AU915 + ChirpStack → ingestão HTTP
- [ ] Postgres + PostGIS
- [ ] Atualização de firmware OTA
- [ ] Nós com câmera + modelo aberto de detecção de fumaça
