---
sidebar_position: 6
title: Áreas piloto
---

# Áreas piloto

Sem hardware, cada área monitorada é uma **estação virtual**: um ponto mais um raio. O clima horário do ponto
alimenta a FMA+, e qualquer foco do INPE dentro do raio gera um alerta.

As quatro primeiras áreas ficam em regiões propensas a incêndios, em biomas diferentes:

| ID | Área | Bioma | Raio | Por quê |
|---|---|---|---|---|
| `chapada-veadeiros` | Chapada dos Veadeiros (GO) | Cerrado | 20 km | Parque nacional com grandes incêndios recorrentes (ex.: 2017) |
| `pantanal-pocone` | Transpantaneira, Poconé (MT) | Pantanal | 25 km | Muito atingida nas temporadas de fogo de 2020 e 2024 |
| `novo-progresso` | Novo Progresso (PA) | Amazônia | 25 km | Arco do desmatamento, onde o fogo é usado para abrir áreas |
| `chapada-diamantina` | Chapada Diamantina (BA) | Caatinga/Cerrado | 20 km | Incêndios frequentes no parque nacional durante a seca |

As coordenadas são centros aproximados das áreas. Ajuste-as antes de depender delas.

## Adicionando uma área

Edite `backend/config/sites.json` e reinicie o backend:

```json
{"id": "jalapao", "name": "Jalapão (TO)", "biome": "cerrado", "lat": -10.40, "lon": -46.60, "radius_km": 25, "timezone": "America/Araguaina"}
```

O `id` deve ser único e pode conter apenas letras, números, `-` e `_`. O `timezone` é o horário legal
local da área (nome IANA), usado na leitura das 13h da FMA+; o padrão é `America/Sao_Paulo`. Na próxima inicialização, o backend busca 30 dias de clima para a nova área.
