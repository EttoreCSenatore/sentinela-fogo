---
sidebar_position: 4
title: Modelo de risco
---

# Modelo de risco

O sistema calcula duas coisas diferentes:

| | **Perigo** de incêndio | **Detecção** de incêndio |
|---|---|---|
| Pergunta | Com que facilidade um fogo começaria e se espalharia aqui? | Algo está queimando agora? |
| Frequência | Diária | A cada leitura ou foco |
| Entradas | Umidade, vento e chuva | Chama, fumaça, anomalias de temperatura/umidade, focos de satélite |
| Tipo de alerta | `danger` (Risco de Fogo do INPE + FMA+) | `fire` (sensor) e `hotspot` (satélite) |

## Perigo de incêndio: FMA+

A **FMA+** (Fórmula de Monte Alegre Alterada; Nunes, Soares & Batista, 2006) é um índice acumulativo desenvolvido
e calibrado no Brasil. Ela acrescenta o vento à Fórmula de Monte Alegre original (Soares, 1972):

```text
FMA+ = Σ (100 / Hᵢ) · e^(0.04 · vᵢ)
```

- `Hᵢ` é a umidade relativa (%) às 13h (horário local) do dia *i*.
- `vᵢ` é a velocidade do vento (m/s) às 13h.
- A chuva de cada dia reduz a soma acumulada antes de somar o termo desse dia:

| Chuva diária (mm) | Efeito na soma |
|---|---|
| ≤ 2,4 | nenhum |
| 2,5 – 4,9 | × 0,7 |
| 5,0 – 9,9 | × 0,4 |
| 10,0 – 12,9 | × 0,2 |
| > 12,9 | zera, e esse dia não soma nada |

| FMA+ | Classe |
|---|---|
| ≤ 3,0 | Nula |
| 3,1 – 8,0 | Pequena |
| 8,1 – 14,0 | Média |
| 14,1 – 24,0 | Alta |
| > 24,0 | Muito alta |

O backend calcula a FMA+ sobre os últimos 30 dias de leituras de cada nó ou área. Ele usa a leitura mais próxima
das 13h no horário local da área (`timezone` no `sites.json`) e a chuva total de cada dia. FMA+ *alta* e *muito alta* só geram alertas `danger` quando não há
dados do INPE (veja abaixo).

:::info Validado
A fórmula, as faixas de chuva e os limites das classes conferem com o método publicado. Em comparação com o *Risco de Fogo*
do INPE, a FMA+ acompanha os mesmos ciclos de seca e chuva (correlação de postos 0,75), mas fica cerca de uma classe mais
alarmante nos períodos secos e zera de forma brusca demais após uma única chuva forte. Veja [Validação](validation.md).
:::

## Alertas de perigo: INPE primeiro, FMA+ junto

Cada área monitorada também recebe o **Risco de Fogo oficial do INPE**: o valor observado e a previsão do INPE para
hoje e os próximos 3 dias. A nossa [validação](validation.md) mostrou que a FMA+ fica cerca de uma classe acima e zera de
forma brusca demais depois da chuva, então é o índice do INPE que decide os alertas `danger`:

| Situação | Alerta? |
|---|---|
| INPE hoje está **Alto** ou **Crítico** | Sim: "risco de fogo ALTO hoje em …" |
| Previsão do INPE Alto/Crítico em um dos próximos 3 dias | Sim, como aviso antecipado: "Previsão: risco de fogo CRÍTICO em … em 17/11" |
| INPE abaixo de Alto, mesmo com a FMA+ *alta* | Não |
| Sem dados do INPE para a área | Volta a usar a FMA+ *alta* / *muito alta* |

As mensagens sempre trazem a previsão do INPE para os próximos dias e o valor atual da FMA+, e há no máximo um alerta
`danger` por área por dia. O painel colore cada área pelo nível do INPE (FMA+ quando o INPE não tem dados), e o comando
`/status` do Telegram mostra os dois índices.

## Detecção de incêndio por sensores

Cada leitura de sensor recebe um score de 0 a 1. Cada sinal detectado soma ao score, que fica limitado a 1:

| Sinal | Peso |
|---|---|
| Sensor de chama infravermelho acionado | 0,6 |
| Fumaça ≥ 4× a mediana móvel do nó | 0,5 |
| Fumaça ≥ 2× a mediana móvel do nó | 0,3 |
| Temperatura +5 °C **e** umidade −10 pontos em relação à mediana móvel | 0,2 |
| Foco do INPE a até 5 km nas últimas 3 h | 0,3 |

Um score de **0,6 ou mais** gera um alerta `fire`, com intervalo mínimo de 30 minutos por nó. Comparar cada leitura
com a linha de base do próprio nó, em vez de limites fixos, ajusta automaticamente para cada sensor e seu entorno
(veja [calibração](hardware.md#calibração)). Usamos a mediana móvel (e não a leitura anterior) para que um fogo que cresce
aos poucos ainda se destaque.

## Proximidade de focos

Sempre que chegam novos focos do INPE, cada área e cada nó é verificado em busca de focos dentro do seu raio
(`radius_km` para áreas, 5 km para sensores) nas últimas 3 horas. Uma ocorrência gera um alerta `hotspot`, com intervalo
de 3 horas por área. O alerta informa o número de focos e a distância até o mais próximo.

## Ajuste fino

Os pesos e limites ficam em `backend/app/risk/detect.py` e `backend/app/config.py`. Eles são um ponto de partida.
Dados do piloto (inclusive alarmes falsos causados por poeira, escapamento de veículos e queimas controladas) devem ser usados para reajustá-los.
