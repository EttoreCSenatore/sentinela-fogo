---
sidebar_position: 9
title: Monte um nó sensor
---

# Monte um nó sensor

O sistema já funciona sem hardware (focos de satélite, clima e risco do INPE). Um **nó sensor** acrescenta o que os
satélites não conseguem: **detecção no nível do solo em minutos**, exatamente onde o fogo costuma começar. Este guia vai
das peças até um nó enviando dados ao painel e disparando alertas no Telegram.

**Tempo:** uma tarde para montar e gravar, mais 1–2 dias de amaciamento do sensor. **Custo:** cerca de R$ 300–500 por nó.
**Habilidades:** solda básica, ou protoboard/jumpers para a versão de bancada, e copiar comandos no terminal.

:::danger Segurança em primeiro lugar
- Nunca teste com fogo de verdade perto de vegetação. Use um incenso (fumaça) e um isqueiro por poucos segundos (chama), sobre uma superfície que não pegue fogo.
- O aquecedor do MQ-2 esquenta (~50 °C na carcaça). Não toque nele enquanto estiver ligado.
- Use baterias 18650 **protegidas** (com placa de proteção BMS/DW01) e um carregador próprio para lítio. Baterias numa caixa fechada ao sol esquentam muito: faça sombra na caixa.
:::

## 1. Peças

Preços são estimativas aproximadas de 2026, em reais, de vendedores comuns (Mercado Livre, lojas de eletrônica, AliExpress).

| # | Peça | Qtd | ~R$ | Observações |
|---|---|---|---|---|
| 1 | **ESP32 DevKit v1** (ESP-WROOM-32, 30 ou 38 pinos) | 1 | 40–60 | O microcontrolador. Qualquer ESP32 com Wi-Fi serve; os pinos abaixo são do DevKit v1 |
| 2 | Módulo de temperatura/umidade **SHT31** (I2C) | 1 | 30–50 | Recomendado. *Alternativa:* DHT22 (R$ 25–40), mais barato mas menos confiável ao ar livre |
| 3 | Módulo de gás/fumaça **MQ-2** | 1 | 10–20 | Placa com saída AO (analógica) |
| 4 | Módulo sensor de chama IR **KY-026** | 1 | 8–15 | Opcional. Só é útil a ~1 m de onde o fogo pode começar |
| 5 | Módulo **GPS NEO-6M** (ou NEO-M8N) com antena | 1 | 40–70 | Opcional. Você pode digitar a posição na configuração |
| 6 | MOSFET N de nível lógico **AO3400** ou **IRLZ44N** | 1 | 2–5 | Liga o aquecedor do MQ-2 só durante a medição |
| 7 | Resistores: 2× 100 kΩ, 1× 100 kΩ, 1× 10 kΩ, 1× 20 kΩ, 1× 100 Ω | 1 kit | 5–10 | Divisores, gate do MOSFET, medição da bateria |
| 8 | Painel solar **6 V, 3–5 W** | 1 | 40–70 | Virado para o norte (estamos no hemisfério sul) |
| 9 | Módulo carregador **TP4056** *com proteção* (versão USB-C com chip DW01) | 1 | 5–10 | Carrega as baterias a partir do painel |
| 10 | Baterias **18650** Li-ion protegidas + suporte para 2 em **paralelo** | 2 | 40–80 | ~6000 mAh no total, em 3,7 V |
| 11 | Conversor elevador **MT3608** (ajustado para 5,0 V) | 1 | 5–10 | Bateria → 5 V para o ESP32 (VIN) e o MQ-2 |
| 12 | Caixa IP65 ~15×10×7 cm + prensa-cabos | 1 | 30–60 | |
| 13 | Abrigo contra radiação para o SHT31 | 1 | 0–40 | Faça você mesmo: 5–6 pratos plásticos brancos empilhados com espaçadores, ou compre um |
| 14 | Tela inox (mosquiteiro), silicone, abraçadeiras, poste/suporte | — | 20–40 | |

**Ferramentas:** ferro de solda, multímetro (essencial: você vai ajustar o elevador para 5 V e conferir tensões),
alicate desencapador, cabo USB e um computador com porta USB.

## 2. Como as partes se ligam

```text
 Solar 6V ──▶ TP4056 (carregador+proteção) ──▶ 2× 18650 em paralelo (3,0–4,2 V)
                                   │ OUT+/OUT-
                                   ├──────────────▶ divisor de medição da bateria ──▶ GPIO35
                                   ▼
                          Elevador MT3608 → 5,0 V
                                   │
               ┌───────────────────┼────────────────────────┐
               ▼                   ▼                        ▼
         ESP32 VIN (5V)     MQ-2 VCC (5V)            GPS VCC (5V ou 3,3V*)
         ESP32 3V3 ──▶ SHT31 VCC, KY-026 VCC
         MQ-2 GND ──▶ dreno do MOSFET │ fonte ──▶ GND │ gate ◀── 100Ω ◀── GPIO25
```

\* Confira na placa do seu GPS: a maioria das placas NEO-6M aceita 3,3–5 V.

## 3. Ligações

Ligue todos os terras (GND) juntos: negativo da bateria, GND do elevador, GND do ESP32, GND dos sensores e fonte (source) do MOSFET.

### Alimentação

| De | Para |
|---|---|
| Painel solar + / − | TP4056 **IN+ / IN−** |
| Suporte das 18650 + / − (baterias em **paralelo**) | TP4056 **B+ / B−** |
| TP4056 **OUT+ / OUT−** | MT3608 **VIN+ / VIN−** |
| MT3608 **VOUT+** (ajuste para **5,0 V** com o multímetro *antes* de ligar o ESP32) | ESP32 **VIN**, MQ-2 **VCC** |
| TP4056 OUT+ → **100 kΩ** → **GPIO35** → **100 kΩ** → GND | medição da tensão da bateria |

### Temperatura e umidade

**SHT31 (recomendado):**

| SHT31 | ESP32 |
|---|---|
| VIN / VCC | 3V3 |
| GND | GND |
| SDA | GPIO21 |
| SCL | GPIO22 |

**ou DHT22:** VCC → 3V3, GND → GND, DATA → **GPIO4**, mais um resistor de **10 kΩ** entre DATA e 3V3 (muitos módulos já têm).
Defina `TH_SENSOR_SHT31 0` no `config.h`.

### Sensor de fumaça MQ-2 (aquecedor ligado pelo MOSFET)

O MQ-2 funciona em 5 V e a saída AO pode chegar a 5 V, mas a entrada do ESP32 só aguenta 3,3 V: **use sempre o divisor**.

| MQ-2 | Vai para |
|---|---|
| VCC | 5 V (saída do MT3608) |
| GND | **dreno** do MOSFET |
| AO | **10 kΩ** → **GPIO34**, e GPIO34 → **20 kΩ** → GND |
| DO | não usado |

| MOSFET (AO3400 / IRLZ44N) | Vai para |
|---|---|
| Gate | **100 Ω** → **GPIO25** (coloque 100 kΩ entre gate e GND para ele ficar desligado durante a inicialização) |
| Fonte (source) | GND |
| Dreno (drain) | GND do MQ-2 |

Com o divisor de 10 k/20 k, mantenha `MQ2_DIVIDER 1.5` no `config.h`. Sem divisor (não recomendado), use `1.0`.
Confira o resistor de carga impresso na placa do MQ-2 (geralmente "502" = 5 kΩ ou "103" = 10 kΩ) e ajuste `MQ2_RL_KOHM`.

### Sensor de chama (opcional)

| KY-026 | ESP32 |
|---|---|
| VCC (+) | 3V3 |
| GND (G) | GND |
| DO | **GPIO27** |

A maioria dos módulos leva o DO para **LOW** quando vê chama (`FLAME_ACTIVE_LOW 1`). Se o seu fizer o contrário, use 0.

### GPS (opcional)

| GPS | ESP32 |
|---|---|
| VCC | 5 V ou 3V3 (veja o módulo) |
| GND | GND |
| TX | **GPIO16** (RX do ESP32) |
| RX | **GPIO17** (TX do ESP32) |

Defina `USE_GPS 1`. Ao ligar, o nó espera até 2 minutos por uma boa posição (ao ar livre, céu aberto) e guarda essa
posição na memória entre os ciclos de sono. Sem GPS, preencha `NODE_LAT`/`NODE_LON` usando o mapa do celular.

## 4. Software: configurar, cadastrar, gravar

**4.1 Instale o PlatformIO** (uma vez): a extensão *PlatformIO IDE* do VS Code, ou pela linha de comando:

```bash
python3 -m pip install --user platformio
```

**4.2 Baixe o código e crie o arquivo de segredos:**

```bash
git clone https://github.com/EttoreCSenatore/sentinela-fogo.git
cd sentinela-fogo/firmware/esp32-node
cp src/secrets.example.h src/secrets.h
```

**4.3 Crie o login do nó no servidor** (cada nó tem seu próprio usuário MQTT, que deve ser igual ao seu ID):

```bash
infra/provision.sh node cerrado-001        # rode no servidor, a partir da raiz do repositório
# cerrado-001  Xk3...   <- a senha, mostrada uma única vez
```

**4.4 Edite a configuração:**

- `src/config.h`: `NODE_ID` (o mesmo de cima), `NODE_LAT`/`NODE_LON` e quais sensores você instalou (`TH_SENSOR_SHT31`,
  `USE_MQ2`, `USE_FLAME`, `USE_GPS`).
- `src/secrets.h`: nome e senha do Wi-Fi, `MQTT_HOST` (seu servidor) e `MQTT_PASSWORD` (do passo 4.3).
  Para um servidor na internet com TLS, siga os comentários do arquivo (porta 8883 e o certificado da CA Let's Encrypt).

**4.5 Grave** com o ESP32 ligado na USB:

```bash
pio run -t upload
pio device monitor        # Ctrl+C para sair
```

Você deve ver `published: {...}` seguido de `sleeping 300 s`. O nó passa a aparecer no painel como sensor.
Se o computador não reconhecer a placa, instale o driver USB do chip dela (CP2102 ou CH340).

## 5. Calibre (na bancada, antes de instalar)

Sensores baratos variam de uma unidade para outra. O backend compara cada nó com as suas **próprias** leituras recentes,
então pequenas diferenças não causam alarmes falsos, mas calibrar dá sentido aos números.

1. **Amaciamento e R0 do MQ-2.** Defina `CALIBRATION_MODE 1` no `config.h`, grave e deixe o nó ligado **em ar limpo**
   (ao ar livre ou num cômodo ventilado, sem cozinha ou carros por perto) por **24–48 h** na primeira vez. O monitor serial
   mostra `R0 (clean air) = X` a cada 2 s. Quando o valor estabilizar, copie-o para `MQ2_R0_KOHM`, volte `CALIBRATION_MODE 0` e grave de novo.
2. **Temperatura/umidade.** Deixe o nó ao lado de um termo-higrômetro confiável por algumas horas. Diferença de
   1 °C / 5 % UR é normal nesses sensores. Anote-a, pois um ajuste de desvio por nó está no roadmap.
3. **Sensor de chama.** No modo de calibração, segure um isqueiro na distância que quer proteger e gire o potenciômetro
   do módulo até `flame 1` aparecer só com a chama, e não com sol direto no sensor.
4. **Bateria.** Compare `batt` com o multímetro nas baterias. Se a diferença passar de 0,1 V, ajuste `BATT_DIVIDER`.

## 6. Teste de ponta a ponta

Com o nó no modo normal e o backend rodando:

1. Espere 4–5 leituras (cerca de 20 min) para o nó formar sua linha de base.
2. Segure um **incenso** aceso a poucos centímetros do MQ-2 durante uma leitura. O valor de fumaça deve subir várias vezes acima do normal.
3. Se quiser, segure um isqueiro na frente do sensor de chama ao mesmo tempo.
4. Um alerta `fire` deve aparecer no painel e chegar no Telegram:
   *"🔥 Possível incêndio no nó cerrado-001 … fumaça 6.9x acima da linha de base"*.

Enquanto houver fumaça ou chama, o nó acorda a cada minuto em vez de a cada 5 minutos.

## 7. Caixa e instalação

- **Caixa:** ESP32, baterias e eletrônica ficam dentro da caixa IP65. Passe os cabos por prensa-cabos e vede.
- **SHT31 do lado de fora, no abrigo contra radiação.** Dentro de uma caixa ao sol ele leria 5–10 °C a mais, o que
  estraga a FMA+ e gera alarmes térmicos falsos.
- **O MQ-2 precisa de ar:** monte-o numa abertura ventilada coberta com tela inox (insetos adoram essas caixas), virada para baixo para a chuva não entrar.
- **Sensor de chama:** atrás de uma pequena abertura com tela, apontado para a área a vigiar. Ele não enxerga através da parede da caixa.
- **Painel solar:** virado para o **norte**, inclinado mais ou menos na sua latitude (ex.: ~15° em Brasília), sem sombra entre 9 h e 15 h.
- **Altura:** 1,5–2 m num poste, acima do capim mas abaixo da copa das árvores.
- **Onde:** onde o fogo costuma *começar*, como beiras de estrada, aceiros, divisas de propriedade e áreas de capim seco, e
  onde o Wi-Fi chega. Vários nós baratos ao longo de uma divisa valem mais que um nó perfeito no meio.
- **Raios:** em campo aberto, aterre o poste e mantenha os cabos curtos.

### Consumo de energia

| Consumidor | Média |
|---|---|
| Aquecedor do MQ-2 (~150 mA por 20 s a cada 5 min) | ~10 mA |
| ESP32 acordado + Wi-Fi (~100 mA por ~25 s a cada 5 min) | ~8 mA |
| ESP32 DevKit em sono profundo (chip USB e regulador continuam ligados) | ~10 mA |
| **Total** | **~28 mA ≈ 0,7 Ah/dia** |

Duas baterias de 3000 mAh dão **~8 dias sem sol**. Um painel de 3 W repõe o consumo de um dia em poucas horas de sol. Para
ir além, use uma placa com baixo consumo em sono (FireBeetle ESP32, LOLIN D32) ou aumente `SLEEP_SECONDS_NORMAL`.

## 8. Conectividade

| Opção | Situação |
|---|---|
| **Wi-Fi** | Suportado. Perto de uma sede, de um posto de brigada ou de um roteador 4G com Wi-Fi |
| Modem 4G (SIM7600) | Roadmap |
| LoRaWAN AU915 (longo alcance, sem internet no nó) | Roadmap: gateway + ChirpStack → `POST /api/readings` |

Uma solução prática hoje: um **roteador 4G com Wi-Fi**, com seu próprio kit solar num ponto alto, cobrindo vários nós por perto.

## 9. Solução de problemas

| O monitor serial mostra | Causa provável |
|---|---|
| `SHT31 not found` | SDA/SCL trocados, sem 3V3, ou a placa usa o endereço 0x45 (ajuste `SHT31_ADDR`) |
| `temperature/humidity read failed` | O mesmo de cima, ou no DHT22: falta o pull-up ou pino errado |
| `Wi-Fi connection failed` | Nome/senha errados, sinal fraco ou rede só de 5 GHz (o ESP32 precisa de 2,4 GHz) |
| `MQTT connection failed (state -2)` | Servidor inacessível: `MQTT_HOST`/porta errados, firewall ou configuração de TLS |
| `MQTT connection failed (state 4 ou 5)` | Senha errada, ou `MQTT_USER` ≠ `NODE_ID`; rode `provision.sh node <id>` de novo |
| Publicou, mas nada aparece no painel | `NODE_ID` diferente do usuário cadastrado (o broker descarta a mensagem sem avisar) |
| `smoke` ausente ou `nan` | MQ-2 sem alimentação (confira o MOSFET e os 5 V) ou AO desconectado |
| `flame 1` o tempo todo | Sensibilidade alta demais ou sol no sensor: ajuste o potenciômetro, confira `FLAME_ACTIVE_LOW` |
| `batt 0.00 V` | Divisor de medição da bateria não ligado ao GPIO35 |
| O nó reinicia durante o Wi-Fi | Fonte de 5 V fraca: confira a saída do MT3608 com carga, coloque um capacitor de 470 µF no VIN |
