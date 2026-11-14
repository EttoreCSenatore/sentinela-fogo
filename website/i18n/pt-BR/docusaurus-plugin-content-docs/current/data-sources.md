---
sidebar_position: 5
title: Fontes de dados
---

# Fontes de dados

Tudo o que usamos é gratuito e aberto.

## INPE BDQueimadas: focos de calor por satélite

- **O quê:** detecções de fogo ativo ("focos de calor") de vários satélites (GOES-19, NOAA-20/21, Suomi-NPP, Aqua, Terra, METOP...),
  publicadas pelo Programa Queimadas do INPE.
- **Feed:** `https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/10min/`, com um CSV novo a cada 10 minutos
  chamado `focos_10min_AAAAMMDD_HHMM.csv`. Colunas: `lat,lon,satelite,data` (UTC).
- **Cobertura:** América do Sul. Guardamos apenas os pontos dentro do retângulo que envolve o Brasil. Esse retângulo é
  aproximado e deixa passar alguns pontos de países vizinhos; filtrar pela fronteira real do Brasil está no [roadmap](roadmap.md).
- **Limitações:** detecções geoestacionárias (GOES) são frequentes, mas grosseiras (pixel de ~2 km). Os sensores de órbita
  polar são mais precisos, mas passam poucas vezes por dia. Nuvens e fumaça podem esconder focos, e incêndios pequenos podem não ser detectados.
- **Código:** `backend/app/ingest/inpe.py`

## Open-Meteo: clima das áreas monitoradas

- **O quê:** temperatura, umidade relativa, vento e precipitação de hora em hora para qualquer coordenada. Não exige chave de API.
- **Usado para:** estações virtuais em cada área piloto. Esses dados alimentam o índice de perigo FMA+.
- **Observações:** são **dados de modelo** (previsão e reanálise), não medições de estação meteorológica. A API gratuita
  do Open-Meteo é para **uso não comercial**, e os dados são CC BY 4.0, então dê o crédito se publicar resultados.
- **Código:** `backend/app/ingest/weather.py`

## Risco de Fogo do INPE: risco oficial de fogo (validação)

- **O quê:** o índice diário de risco de fogo do INPE (0–1, cinco classes), em uma grade de cerca de 1 km.
- **Feed:** `https://dataserver-coids.inpe.br/queimadas/queimadas/riscofogo_meteorologia/observado/risco_fogo/`
  (um arquivo NetCDF por dia, ~12,5 MB, ano corrente). Há também uma previsão de 0 a 3 dias em `.../previsto/risco_fogo/` (GeoTIFF).
- **Usado para:** conferir a nossa FMA+ ([Validação](validation.md)). Usá-lo como fonte de perigo em tempo real está no roadmap.
- **Código:** `backend/app/validation/inpe_risk.py`

## Fontes candidatas

| Fonte | Por quê |
|---|---|
| Estações automáticas do INMET | Medições reais para validar os valores do Open-Meteo |
| Limites de biomas e estados do IBGE | Filtro preciso do Brasil e estatísticas por bioma |
| Unidades de conservação do ICMBio | Monitorar áreas protegidas automaticamente |
| NASA FIRMS (VIIRS 375 m) | Focos mais precisos (exige chave de mapa gratuita) |
| MapBiomas Fogo | Área queimada histórica, para escolher áreas e validar resultados |
