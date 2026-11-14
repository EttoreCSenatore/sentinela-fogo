---
sidebar_position: 5
title: Validação (FMA+ vs INPE)
---

# Validação: FMA+ vs Risco de Fogo do INPE

_Última execução: 14/11/2026, de 15/10/2026 a 13/11/2026 (30 dias, 4 áreas piloto, 112 dias-área)._

Verificamos duas coisas: se a nossa implementação da FMA+ segue o método publicado e como ela se compara ao
produto oficial de risco de fogo do INPE.

## 1. A fórmula está implementada corretamente?

**Sim.** Conferimos a fórmula, as regras de chuva e os limites das classes com as tabelas de Nunes, Soares & Batista (2006),
reproduzidas em Eugenio et al. (2022), *FMA+ Sisclass*, Floresta 52(1):131–139, doi:10.5380/rf.v52i1.78591:

| Item | Publicado | Nosso |
|---|---|---|
| Fórmula | Σ (100/H) · e^(0,04·V), H = UR às 13h, V = vento (m/s) às 13h | igual |
| Chuva < 2,4 mm | sem alteração | igual |
| 2,5–4,9 / 5,0–9,9 / 10–12,9 mm | abater 30 % / 60 % / 80 % do valor do dia anterior e somar o termo do dia | × 0,7 / 0,4 / 0,2 e somar |
| > 12,9 mm | interromper (FMA+ = 0) e recomeçar a soma no dia seguinte | igual |
| Classes | Nula ≤ 3,0, Pequena 3,1–8,0, Média 8,1–14,0, Alta 14,1–24,0, Muito alta > 24 | igual |

**Bug encontrado e corrigido:** "13h" é a hora local do relógio. Usávamos o horário de Brasília para todas as áreas,
então em Mato Grosso (UTC−4) líamos a umidade às 12h. Agora cada área tem seu próprio `timezone` no `sites.json`.

## 2. Como ela se compara ao INPE?

O **Risco de Fogo (RF)** do INPE é um modelo diferente. Vai de 0 a 1, usa 120 dias de chuva, o tipo de vegetação,
temperatura e umidade às 18 UTC e o relevo, e é publicado como uma grade diária de cerca de 1 km. Os dois usam cinco classes:

| Nível | FMA+ | RF do INPE |
|---|---|---|
| 1 | Nula ≤ 3 | Mínimo < 0,15 |
| 2 | Pequena 3,1–8 | Baixo 0,15–0,4 |
| 3 | Média 8,1–14 | Médio 0,4–0,7 |
| 4 | Alta 14,1–24 | Alto 0,7–0,95 |
| 5 | Muito alta > 24 | Crítico > 0,95 |

Para cada área e dia, comparamos a nossa FMA+ (com dados do Open-Meteo) com a **média do RF do INPE dentro do raio da área**:

| Área | Dias | Mesma classe | Até 1 classe | Diferença média¹ | Correlação de postos² |
|---|---|---|---|---|---|
| Chapada dos Veadeiros (Cerrado) | 28 | 68 % | 100 % | +0,1 | 0,54 |
| Pantanal, Poconé | 28 | 7 % | 68 % | +0,3 | 0,31 |
| Novo Progresso (Amazônia) | 28 | 46 % | 86 % | +0,1 | 0,70 |
| Chapada Diamantina (Caatinga) | 28 | 50 % | 89 % | +0,6 | 0,93 |
| **Todas** | **112** | **43 %** | **86 %** | **+0,3** | **0,75** |

¹ Classe da FMA+ menos classe do INPE. Positivo significa que a FMA+ é mais alarmante.
² Spearman: 1 significa que os dois índices ordenam os dias da mesma forma. O valor de Veadeiros é baixo apenas porque quase todos os dias ali foram "nula"/"mínimo".

### O que aprendemos

1. **A FMA+ acompanha bem os ciclos de seca e chuva do INPE.** Na Chapada Diamantina os dois sobem e descem juntos
   (correlação 0,93): os dois atingem o pico em 15/10 e os dois zeram após as chuvas de 18/10, 27/10 e 9/11.
2. **A FMA+ fica cerca de uma classe mais alarmante nos períodos secos.** Por exemplo, em 5/11 na Diamantina: FMA+ 20,1
   é *alta*, enquanto INPE 0,59 é *médio*. Isso combina com a literatura: as classes da FMA+ foram calibradas para o Paraná,
   e calibrações por percentis para outras regiões (Eugenio et al. 2020) colocam "muito alta" bem acima de 24.
3. **O zeramento por chuva forte é brusco demais.** No Pantanal, em 28/10, 13,1 mm de chuva (apenas 0,2 mm acima do
   limite de 12,9 mm) zeraram a FMA+, de 38,9 (*muito alta*) para 0, enquanto o INPE continuou *alto* (0,70). O INPE
   considera 120 dias de chuva, então um único dia chuvoso depois de semanas de seca quase não o reduz. A FMA+ esquece tudo.
4. **O restante vem principalmente de diferenças nos dados e no horário da chuva.** O INPE caiu para *mínimo* em 7/11,
   mas o nosso ponto meteorológico mostra 0,4 mm nesse dia e 8,2 mm no seguinte. O INPE usa sua própria análise de
   chuva sobre a área toda e provavelmente começa cada dia em outro horário, enquanto nós usamos um único ponto de modelo.

### O que isso significa para os alertas

- Alertas diários de `danger` baseados só na FMA+ vão disparar **com mais frequência do que o INPE indicaria**, e
  podem ficar em silêncio logo depois de uma única chuva forte no meio de uma seca.
- Próximos passos recomendados (veja o [roadmap](roadmap.md)):
  1. ✅ **Usar o RF do INPE como segunda fonte de perigo** para cada área, incluindo a previsão de 0 a 3 dias do INPE.
     Feito: agora o INPE decide os alertas `danger` (veja [Modelo de risco](risk-model.md#alertas-de-perigo-inpe-primeiro-fma-junto)).
  2. **Calibrar as classes da FMA+ por bioma** com o método de percentis de Eugenio et al. (2020), usando o histórico
     de focos do INPE de cada área.

## Rodar a comparação de novo

```bash
cd backend
.venv/bin/python -m app.cli compare-inpe --days 30 --csv data/compare.csv
```

O comando baixa uma grade do INPE por dia (~12,5 MB cada, apagada após o uso) e guarda só as amostras por área
em `data/inpe_rf_samples.csv`, então as execuções seguintes só buscam os dias novos. O INPE mantém as grades diárias
do ano corrente. Código: `backend/app/validation/inpe_risk.py`.
