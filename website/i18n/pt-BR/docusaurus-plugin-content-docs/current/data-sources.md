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
- **Cobertura:** América do Sul. Guardamos apenas os pontos dentro do Brasil, usando os limites oficiais dos estados do
  IBGE (abaixo), e marcamos cada foco com seu estado (UF). Pontos até 2 km fora do contorno ainda contam, para que focos
  no litoral, em ilhas pequenas e em rios de fronteira não se percam no contorno simplificado.
- **Limitações:** detecções geoestacionárias (GOES) são frequentes, mas grosseiras (pixel de ~2 km). Os sensores de órbita
  polar são mais precisos, mas passam poucas vezes por dia. Nuvens e fumaça podem esconder focos, e incêndios pequenos podem não ser detectados.
- **Código:** `backend/app/ingest/inpe.py`

## Open-Meteo: clima das áreas monitoradas

- **O quê:** temperatura, umidade relativa, vento e precipitação de hora em hora para qualquer coordenada. Não exige chave de API.
- **Usado para:** estações virtuais em cada área piloto. Esses dados alimentam o índice de perigo FMA+.
- **Observações:** são **dados de modelo** (previsão e reanálise), não medições de estação meteorológica. A API gratuita
  do Open-Meteo é para **uso não comercial**, e os dados são CC BY 4.0, então dê o crédito se publicar resultados.
- **Código:** `backend/app/ingest/weather.py`

## Risco de Fogo do INPE: risco oficial de fogo

- **O quê:** o índice diário de risco de fogo do INPE (0–1, cinco classes), em uma grade de cerca de 1 km.
- **Feed:** `https://dataserver-coids.inpe.br/queimadas/queimadas/riscofogo_meteorologia/observado/risco_fogo/`
  (um arquivo NetCDF por dia, ~12,5 MB, ano corrente). Há também uma previsão de 0 a 3 dias em `.../previsto/risco_fogo/` (GeoTIFF).
- **Usado para:** a fonte principal dos alertas `danger`, das cores do painel e do `/status`, além de conferir a
  nossa FMA+ ([Validação](validation.md)). O backend procura arquivos novos a cada 3 horas e amostra o raio de cada área.
- **Tráfego:** cerca de 90 MB por dia (quatro arquivos de previsão de ~20 MB e um observado de ~12,5 MB). Os arquivos
  são apagados após a amostragem. Defina `SENTINELA_INPE_RISK_ENABLED=false` para desligar.
- **Código:** `backend/app/ingest/inpe_risk.py`

## IBGE: limites dos estados

- **O quê:** limites oficiais dos 27 estados (UFs), da API de *Malhas territoriais* do IBGE (v3, detalhe intermediário).
- **Arquivo:** `backend/config/br_uf.geojson` (250 KB, incluído no repositório, então não há download durante a execução).
- **Usado para:** descartar focos fora do Brasil e marcar cada um com seu estado (`/api/hotspots?uf=GO`).
- **Código:** `backend/app/geo.py`. Configurações: `SENTINELA_BOUNDARIES_FILE`, `SENTINELA_BORDER_TOLERANCE_KM` (padrão 2).

## Fontes candidatas

| Fonte | Por quê |
|---|---|
| Estações automáticas do INMET | Medições reais para validar os valores do Open-Meteo |
| Limites dos biomas do IBGE | Estatísticas e alertas por bioma |
| Unidades de conservação do ICMBio | Monitorar áreas protegidas automaticamente |
| NASA FIRMS (VIIRS 375 m) | Focos mais precisos (exige chave de mapa gratuita) |
| MapBiomas Fogo | Área queimada histórica, para escolher áreas e validar resultados |
