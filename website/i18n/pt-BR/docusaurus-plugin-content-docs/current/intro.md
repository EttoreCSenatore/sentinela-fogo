---
slug: /
sidebar_position: 1
title: Introdução
---

# Sentinela do Fogo

O **Sentinela do Fogo** é um sistema aberto de IoT e nuvem para **detectar incêndios florestais cedo no Brasil
e alertar quem pode responder**: proprietários, brigadas e Defesa Civil.

Ele combina três fontes de informação:

| Fonte | O que oferece | Precisa de hardware? |
|---|---|---|
| **Focos de calor do INPE** (BDQueimadas, a cada 10 min) | Incêndios ativos detectados por satélite | Não |
| **Clima das áreas monitoradas** (Open-Meteo, de hora em hora) | Temperatura, umidade, vento e chuva, que alimentam o índice de perigo de incêndio **FMA+** | Não |
| **Nós sensores ESP32** | Leituras de chama, fumaça/gás, temperatura, umidade e GPS no local, a cada poucos minutos | Sim (opcional) |

O sistema funciona sem nenhum hardware. Cada área monitorada é uma **estação virtual**: calculamos um nível diário de
perigo de incêndio a partir de dados meteorológicos reais, e o sistema emite um alerta assim que um satélite detecta um foco dentro da área.
Sensores físicos, quando instalados, acrescentam uma detecção mais rápida no nível do solo.

## Objetivos

- **Detecção precoce:** perceber o fogo em minutos, não em horas.
- **Alertas imediatos e direcionados:** cada destinatário escolhe as áreas, os tipos de alerta e os canais (Telegram, WhatsApp, SMS, webhook) que quer receber.
- **Baixo custo e aberto:** apenas software livre e dados abertos e gratuitos, rodando em um único servidor barato.
- **Feito para o Brasil:** biomas brasileiros, um índice de perigo desenvolvido no Brasil, fontes de dados brasileiras e LoRaWAN na faixa AU915 da Anatel.

## Próximos passos

- [Primeiros passos](getting-started.md): rode tudo localmente em poucos minutos.
- [Arquitetura](architecture.md): como as peças se encaixam.
- [Modelo de risco](risk-model.md): como o perigo e a detecção são calculados.
- [Roadmap](roadmap.md): o que vem a seguir.

:::info Origem
Inspirado em [AK4007/wildfire-iot-monitoring](https://github.com/AK4007/wildfire-iot-monitoring), um projeto canadense
com ESP32 e AWS. Veja o [ADR 0001](decisions/self-hosted-stack.md) para entender por que escolhemos uma stack própria e de código aberto.
:::
