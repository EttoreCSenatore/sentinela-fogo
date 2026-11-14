---
sidebar_position: 9
title: Hardware e calibração
---

# Hardware e calibração

O hardware é **opcional**. O sistema já funciona com dados de satélite e de clima. Os nós sensores acrescentam
detecção no nível do solo em minutos. O firmware fica em `firmware/esp32-node` (PlatformIO, framework Arduino).

## Lista de materiais: nó v1 (aprox. R$ 250–400)

| Peça | Função | Observações |
|---|---|---|
| ESP32 DevKit, ou Heltec LoRa32 / LILYGO T-Beam para LoRa | Microcontrolador | O T-Beam já vem com GPS e LoRa |
| SHT31 (preferível) ou DHT22 | Temperatura / umidade | O SHT31 é mais preciso e resiste melhor ao tempo |
| MQ-2 | Fumaça / gás combustível | O aquecedor consome ~150 mA. Ligue-o via MOSFET apenas durante a amostragem |
| Sensor de chama IR (KY-026) | Chama direta | Alcance curto (~1 m). Útil apenas perto de pontos prováveis de ignição |
| GPS (NEO-6M / NEO-M8N) | Posição, horário | Opcional para nós fixos: registre a posição uma vez na instalação |
| Anemômetro, pluviômetro (opcional) | Vento/chuva para a FMA+ | Dados de clima podem ser usados no lugar |
| Painel solar 6 V 2–5 W + carregador + 2× 18650 | Energia | |
| Caixa IP65 + abrigo contra radiação | Proteção | Sol direto faz as leituras de temperatura subirem vários °C |

### Ligações (padrões em `src/config.h`)

| Sinal | Pino do ESP32 |
|---|---|
| DHT22 dados | GPIO 4 |
| MQ-2 AO | GPIO 34 (ADC1) |
| MOSFET do aquecedor do MQ-2 | GPIO 25 |
| Chama DO | GPIO 27 |
| Divisor da bateria | GPIO 35 |
| TX do GPS → RX do ESP32 | GPIO 16 (UART2) |

:::danger 5 V no ADC
A maioria das placas MQ-2 funciona em 5 V, e o pino AO pode chegar a 5 V. O ADC do ESP32 aceita no máximo 3,3 V.
Use um divisor (ex.: 10 kΩ / 20 kΩ) e compense-o em `readMq2Ppm()`.
:::

## Calibração

Sensores ao ar livre derivam e variam de uma unidade para outra, então calibre antes de confiar nas leituras.

1. **Amaciamento do MQ-2:** deixe o aquecedor ligado por 24–48 h antes da primeira calibração.
2. **R0 do MQ-2:** em ar limpo, meça Rs e defina `MQ2_R0_KOHM = Rs / 9,8` (a razão em ar limpo, segundo o datasheet).
   Repita a cada poucos meses. Umidade e temperatura deslocam a curva.
3. **Trate a fumaça como valor relativo:** sensores de gás baratos não dão valores exatos em ppm. Por isso o backend compara
   cada leitura com a **mediana móvel do próprio nó**, e não com limites fixos em ppm. Isso compensa a deriva.
4. **Temperatura/umidade:** antes da instalação, deixe todos os nós ao lado de um termo-higrômetro de referência por
   24 h e anote os desvios de cada nó. (Uma tabela de desvios por nó no backend está no roadmap.)
5. **Abrigo contra radiação:** sem ele, o sol na caixa pode somar 5–10 °C. Isso causa alertas térmicos falsos e uma FMA+ errada.
6. **Sensor de chama:** teste o alcance e o ângulo com um isqueiro na distância planejada e ajuste o
   potenciômetro para evitar disparos falsos com sol direto.

## Conectividade

| Opção | Quando usar |
|---|---|
| Wi-Fi | Perto de uma sede ou outra construção com internet |
| Modem 4G (SIM7600) | Onde houver cobertura de celular |
| **LoRaWAN AU915** | Áreas remotas: gateway com ChirpStack (servidor próprio), até ~10 km em terreno aberto |

AU915 é o plano de frequências LoRaWAN usado no Brasil (Anatel). Use a sub-banda 2 (canais 8–15), a mesma da The Things Network.
