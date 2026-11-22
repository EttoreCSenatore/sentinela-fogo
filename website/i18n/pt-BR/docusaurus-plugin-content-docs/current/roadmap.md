---
sidebar_position: 10
title: Roadmap
---

# Roadmap

Este é o plano que seguimos. Os itens marcados com **(K)** foram adaptados do [Kaladrius](https://github.com/facchini-miguel/kaladrius),
um sistema open source maduro de gestão de clínicas, mantido por uma pessoa só. Ele resolve outro problema, mas já
respondeu muitas perguntas sobre como manter um projeto open source pequeno de forma responsável. Veja
[O que aprendemos com o Kaladrius](#o-que-aprendemos-com-o-kaladrius) abaixo.

Regra para a ordem: **operar o que já existe antes de acrescentar funções**, e **nenhum gasto com hardware** até o
software merecer confiança.

## Pronto ✅

- Backend: ingestão MQTT + HTTP, focos do INPE (filtro por estados do IBGE), clima Open-Meteo, FMA+ e *Risco de Fogo* do INPE (observado + previsão de 3 dias), detecção por sensor, API REST + SSE
- Alertas: Telegram no ar; WhatsApp, SMS e webhook prontos
- Painel (React + Leaflet), estações virtuais em 4 áreas piloto, simulador de sensores
- Firmware ESP32 (compila, nunca rodou numa placa) e guia de montagem passo a passo
- Stack Docker de desenvolvimento e de produção (Caddy HTTPS, MQTT com TLS, backups), guia de implantação
- Reforço de segurança, proteções no GitHub (relato privado, Dependabot, proteção da branch)
- Documentação bilíngue (en / pt-BR) com capturas de tela; FMA+ validado com a literatura e com o INPE

## Marco 1: Entrar no ar e poder confiar (próximo)

Objetivo: o sistema roda 24/7 num servidor real e avisa quando quebra, antes dos usuários.

- [ ] Implantar no plano gratuito da Oracle Cloud (São Paulo) + DuckDNS; enviar um alerta real do Telegram para um grupo real *(precisa da VM e do domínio do usuário)*
- [ ] Trocar o token do bot do Telegram e remover os logins de teste `devpass` antes de expor qualquer coisa
- [ ] **(K) Endpoints de saúde e versão:** `/api/health` verifica o banco e a atualidade dos dados; `/api/version` para monitores e para o rodapé do painel
- [ ] **(K) Sinais externos** (Healthchecks.io, grátis): uma verificação para sistema no ar, backup diário, teste de restauração e validade do certificado. Um sinal que *deixa de chegar* também avisa, o que cobre o servidor inteiro fora do ar. Documentado numa página *Operação → Monitoramento*
- [ ] **Avisos de atualidade dos dados** (específico nosso): avisar os mantenedores quando focos do INPE, risco do INPE ou clima ficarem N horas sem atualizar, e quando um nó sensor ficar em silêncio
- [ ] **(K) Teste semanal automático de restauração:** restaurar o backup mais novo num banco descartável e conferir. Backup só vale se restaura
- [ ] **(K) Cópia do backup fora do servidor** (rclone para armazenamento de objetos gratuito) em vez de só uma pasta local
- [ ] **(K) Timers do systemd** (backup, teste de restauração, atualização) instalados pelo `infra/provision.sh`, com trava para que execuções nunca se sobreponham
- [ ] **(K) Documentação de operação:** páginas separadas *Atualizar*, *Backup e restauração*, *Monitoramento*, *Voltar versão* (hoje são seções da Implantação)

## Marco 2: Disciplina de engenharia

Objetivo: com duas pessoas, nada importante vive só na cabeça de alguém, e uma mudança ruim não chega à produção em silêncio.

- [ ] **(K) Registro de decisões:** uma tabela numerada (`#`, data, decisão, motivo, status), com linhas substituídas mantidas, nunca apagadas. Mover a página de ADR atual para ele e registrar as escolhas passadas (servidor próprio, FMA+ + INPE, SQLite primeiro, sem hardware por ora, Oracle)
- [ ] **(K) Migrações com Alembic** + um job de CI que roda cada migração para cima e para baixo num banco descartável e falha quando uma mudança de modelo não tem migração (`alembic check`)
- [ ] **(K) Reforço do CI:** fixar Actions de terceiros por hash de commit (tag em comentário), `persist-credentials: false`, piso de cobertura (começar no nível atual e subir), lint (`ruff`) como verificação obrigatória
- [ ] **(K) Dependabot:** carência de 7 dias para atualizações de versão (as de segurança continuam imediatas), incluir dependências indiretas, um grupo por ecossistema
- [ ] **(K) Dependências reproduzíveis:** arquivo de lock compilado para o backend (`pip-tools` ou `uv`), com o CI falhando se estiver desatualizado
- [ ] **(K) Verificações da documentação no CI:** link quebrado derruba o build; uma checagem de que toda página em inglês tem a sua gêmea em pt-BR
- [ ] **(K) Higiene do repositório:** `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CODEOWNERS`, `NOTICE` (nome/logo fora da MIT), modelos de issue e de PR
- [ ] **(K) Versionamento semântico e releases:** tags `0.x`, um `releases.yaml` (ou `CHANGELOG.md`) como fonte única, GitHub Releases geradas dele, versão no rodapé do painel
- [ ] Publicar as imagens do backend e do painel no GHCR pelo CI, para os servidores baixarem em vez de compilar (importante na VM ARM da Oracle)

## Marco 3: Ciência do risco melhor (sem hardware)

Objetivo: deixar os alertas tão precisos quanto os dados abertos permitem.

- [ ] Calibrar as classes do FMA+ por bioma (percentis do FMA+ em dias com focos do INPE por perto)
- [ ] Limites de biomas (IBGE) para estatísticas e limiares por bioma
- [ ] **Replay histórico:** passar um episódio real de fogo do passado (focos do INPE + clima do dia) pelo pipeline e conferir se o alerta teria disparado. Isso substitui o teste com hardware por enquanto. **(K)** Os comandos de dados falsos `simulate_activity` e `advance_dates` do Kaladrius são o modelo
- [ ] Métricas de qualidade dos alertas: falsos alarmes x eventos perdidos por área, publicadas na documentação
- [ ] Áreas automáticas a partir das unidades de conservação do ICMBio
- [ ] Gráficos de histórico por área (FMA+ e clima ao longo do tempo)

## Marco 4: Quem responde

Objetivo: o alerta leva a uma ação, com responsabilização e privacidade.

- [ ] Visão do socorrista: confirmação de alerta, notas e status (novo → confirmado → resolvido) para brigadas e Defesa Civil
- [ ] **(K) Trilha de auditoria:** quem confirmou ou mudou o quê, e quando; registro de entrega por destinatário e canal
- [ ] **LGPD para destinatários:** telefones e IDs de chat são dados pessoais. Documentar o que é guardado, por quê e por quanto tempo, com um comando de retenção que apaga leituras e registros de entrega antigos **(K)** `apply_retention`
- [ ] **(K) Reforço do login** da visão do socorrista: limite de tentativas e bloqueio, autenticação em dois fatores opcional
- [ ] Preferências por destinatário: canais, limiar de severidade, horário de silêncio para avisos não críticos
- [ ] Mensagens modelo (templates) do WhatsApp
- [ ] **(K) Modo demonstração:** demo pública com dados de exemplo que reinicia toda noite, com os logins na página inicial
- [ ] **(K) Documentação: página de Segurança e privacidade, FAQ, glossário** (termos de perigo de fogo em pt/en)
- [ ] Documentação em espanhol (opcional) para vizinhos latino-americanos com as mesmas temporadas de fogo

## Marco 5: Nós físicos

- [ ] Montar a lista de materiais, calibrar o MQ-2, testar bateria e solar em campo
- [ ] Ajustes de calibração por nó no backend
- [ ] Atualização de firmware pelo ar (assinada)
- [ ] Postgres + PostGIS quando passarmos de ~100 nós
- [ ] Gateway LoRaWAN AU915 + ChirpStack → ingestão HTTP
- [ ] Nós com câmera + modelo aberto de detecção de fumaça
- [ ] **(K) Pacote:** um instalador de um comando ou um `.deb` com repositório apt para quem hospeda, com reversão automática se a nova versão não responder à página de saúde em 5 minutos

## O que aprendemos com o Kaladrius

| Área | Kaladrius | Sentinela hoje | O que fazemos |
|---|---|---|---|
| **Domínio** | Gestão de clínicas (agenda, pacientes, financeiro) | Alerta antecipado de incêndios | Problema diferente; só tomamos emprestadas as práticas de projeto |
| **Stack** | Django, PostgreSQL, HTMX; app móvel à parte | FastAPI, SQLite, React, MQTT | Mantemos a nossa; Postgres depois, para consultas espaciais |
| **Decisões** | 200+ numeradas, datadas, substituídas e não apagadas | Uma ADR | Adotar o registro (M2) |
| **Migrações** | CI mostra o SQL, testa ida e volta, sinaliza as que apagam dados | Colunas adicionadas na inicialização | Alembic + teste no CI (M2) |
| **CI** | Actions fixadas por hash, piso de cobertura de 90%, checagem do lock e das traduções, build da documentação | Testes + builds; Actions por tag | Fixar, pisos, checagem do lock (M2) |
| **Dependências** | Dependabot com carência de 7 dias, lock, agrupado | Dependabot agrupado | Acrescentar carência e locks (M2) |
| **Atualizações** | A VM baixa a imagem nova a cada 5 min, **reversão automática** se a saúde falhar, versões recusadas lembradas | `git pull` + compose à mão | Publicação de imagem no M2, atualização automática com reversão no M5 |
| **Backups** | Diário, **teste de restauração** semanal, aviso no sistema se atrasar | Backup diário, sem teste de restauração | Teste de restauração + aviso de backup velho (M1) |
| **Monitoramento** | Healthchecks.io com 8 sinais, amostras de recursos, arquivos Prometheus, paradas planejadas não alertam | Só endpoint de saúde | Sinais externos + avisos de atualidade (M1) |
| **Privacidade** | Isolamento por clínica, auditoria, comando de retenção, decisões guiadas pela LGPD | Dados de destinatários num arquivo JSON | Auditoria + retenção (M4) |
| **Documentação** | 3 idiomas, manual por papel, operação, decisões, FAQ, marca | 2 idiomas, guias técnicos e de montagem | Separar operação, FAQ, glossário, página de segurança |
| **Releases** | Semver, `releases.yaml`, versão na interface, GitHub Releases | Sem versões ainda | Começar em 0.1.0 (M2) |
| **Distribuição** | `.deb`, `.rpm`, Arch, Docker Compose, Google Cloud | Docker Compose, script de provisionamento | Imagem no GHCR primeiro, pacotes depois |
| **Demo** | Demo pública, reinício noturno, logins de demonstração | Só painel local | Demo pública (M4) |

### O que deliberadamente não copiamos

- **Multi-inquilino e o caminho de proprietário para aberto.** O Sentinela é uma instalação única e MIT desde o primeiro dia.
- **Um registro de decisões enorme desde o início.** Começamos com a tabela e acrescentamos linhas conforme decidimos, sem reconstruir 200 linhas de histórico.
- **A pilha própria de monitoramento deles.** Usamos o Healthchecks.io gratuito mais o painel, e só acrescentamos Prometheus se precisarmos de gráficos.
- **Um app móvel nativo.** O painel instalável como PWA mais o Telegram atendem os primeiros usuários.

### Onde já estamos à frente

- Dados abertos ao vivo (INPE, IBGE, Open-Meteo) e um modelo de risco validado e publicado
- Envio em tempo real ao navegador (SSE) e um broker MQTT autenticado com ACL por nó
- Firmware, guia de hardware e simulador, então o sistema já é utilizável antes de existir qualquer hardware
