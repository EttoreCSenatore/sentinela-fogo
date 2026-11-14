---
sidebar_position: 8
title: Implantação
---

# Implantação (servidor próprio)

Para os alertas serem úteis, o sistema precisa rodar **24 horas por dia** numa máquina sempre ligada e acessível pela
internet. Esta página leva você de um servidor vazio até o sistema funcionando, com HTTPS, MQTT criptografado para os
nós sensores e backups diários.

```text
infra/docker-compose.prod.yml
  caddy       :80 :443   HTTPS para o painel (certificado Let's Encrypt automático)
  mosquitto   :8883      MQTT com TLS para os nós sensores (reaproveita o certificado do Caddy)
  backend     interno    FastAPI, SQLite em volume, backend/config montado só para leitura
  dashboard   interno    nginx servindo o build do React e encaminhando /api para o backend
```

O MQTT sem criptografia (1883) e o backend só são acessíveis dentro da rede do Docker.

## 1. Arrume um servidor

Qualquer máquina Linux com **1 vCPU, 1–2 GB de RAM, 10 GB de disco** e IP público basta para um piloto. Um servidor em
região brasileira mantém a latência baixa.

| Opção | Custo | Observações |
|---|---|---|
| **Oracle Cloud "Always Free"** (região São Paulo ou Vinhedo) | Grátis | VM Ampere (ARM). O cadastro pede cartão, e às vezes não há capacidade gratuita disponível: tente de novo ou escolha outro domínio de disponibilidade. Confira as regras atuais do plano gratuito |
| VPS pequena de um provedor brasileiro ou internacional | ~R$ 30–60/mês | O mais simples. Escolha Ubuntu 24.04 LTS |
| Mini-PC / Raspberry Pi 4/5 em casa ou na fazenda | Só o hardware | Precisa de IP público fixo ou redirecionamento das portas 80, 443 e 8883, e conexão estável |

## 2. Arrume um nome de domínio

Certificados HTTPS precisam de um nome, não só de um IP.

- **Grátis:** crie um subdomínio no [DuckDNS](https://www.duckdns.org) (ex.: `sentinela-chapada.duckdns.org`) apontando para o IP do servidor.
- **Domínio próprio:** crie um registro `A` (ex.: `sentinela.exemplo.org.br`) apontando para o IP do servidor.

Confira no seu computador: `ping sentinela.exemplo.org.br` deve mostrar o IP do servidor.

## 3. Instale

No servidor (Ubuntu), com um usuário que tenha `sudo`:

```bash
# Docker + plugin Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker

# Código
sudo mkdir -p /opt/sentinela && sudo chown $USER /opt/sentinela
git clone https://github.com/EttoreCSenatore/sentinela-fogo.git /opt/sentinela
cd /opt/sentinela

# Configuração
cp infra/.env.example infra/.env
nano infra/.env                       # defina DOMAIN=sentinela.exemplo.org.br (e o token do Telegram, veja Alertas)
infra/provision.sh backend            # usuário MQTT do backend; a senha vai para o infra/.env
cp backend/config/recipients.example.json backend/config/recipients.json   # ou use app.cli add-telegram depois
```

### Firewall

Abra só SSH, HTTP/HTTPS e MQTT com TLS:

```bash
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw allow 8883/tcp
sudo ufw enable
```

:::note Oracle Cloud
Na Oracle você **também** precisa adicionar regras de entrada para TCP 80, 443 e 8883 na *Security List* da VCN. As
imagens Ubuntu da Oracle ainda vêm com regras de `iptables` que bloqueiam tudo menos SSH. Libere as portas lá também, senão o site continua inacessível.
:::

### Inicie

```bash
docker compose -f infra/docker-compose.prod.yml up -d --build
docker compose -f infra/docker-compose.prod.yml logs -f caddy mosquitto     # Ctrl+C para parar de acompanhar
```

Em cerca de um minuto o Caddy registra `certificate obtained successfully`, e o Mosquitto registra `installed certificate …`.
Abra `https://<seu domínio>`: o painel carrega e, depois de alguns minutos, mostra as áreas monitoradas e os dados do INPE.

## 4. Conecte os nós sensores

Para cada nó:

```bash
infra/provision.sh node cerrado-001          # mostra a senha do nó uma única vez
```

No `secrets.h` do nó (veja [Monte um nó sensor](hardware.md)): `MQTT_HOST` = seu domínio, `MQTT_USE_TLS 1`,
`MQTT_PORT 8883` e os certificados raiz do Let's Encrypt, como explicam os comentários do arquivo. O nó acerta o relógio
via NTP antes de conectar, o que a verificação do certificado exige.

Para testar sem hardware, de qualquer computador com o repositório:

```bash
backend/.venv/bin/python simulator/simulate.py --host sentinela.exemplo.org.br --port 8883 --tls \
    --nodes 1 --password <senha do nó> --cycles 3
```

## 5. Backups

O banco de dados (alertas, leituras, dados do INPE) fica num volume do Docker. Faça backup todo dia com o cron do servidor:

```bash
crontab -e
# adicione:
0 3 * * * cd /opt/sentinela && docker compose -f infra/docker-compose.prod.yml exec -T backend python -m app.cli backup /data/backups --keep 14
```

O comando `backup` faz uma cópia consistente com o sistema rodando e mantém as 14 mais recentes. Para guardar uma cópia
**fora do servidor** (recomendado), copie a pasta regularmente:

```bash
docker compose -f infra/docker-compose.prod.yml cp backend:/data/backups ./backups
# depois envie ./backups para outra máquina ou armazenamento, por exemplo com rsync ou rclone
```

Guarde também uma cópia segura de `infra/.env`, `infra/mosquitto/passwd` e `backend/config/recipients.json`. Eles não ficam no git.

**Restaurar:** pare o backend, copie um backup por cima de `/data/sentinela.db` no volume `backend-data` e inicie de novo.

## 6. Atualizar

```bash
cd /opt/sentinela
git pull
docker compose -f infra/docker-compose.prod.yml up -d --build
```

:::note
Ainda não há migrações de banco. Se uma versão avisar sobre mudança no esquema, faça backup antes. O Alembic está no roadmap.
:::

## 7. Acompanhamento

| Verificação | Como |
|---|---|
| Todos os serviços no ar | `docker compose -f infra/docker-compose.prod.yml ps`: o backend aparece `(healthy)` |
| Dados chegando | O cabeçalho do painel mostra `● ao vivo`, e os focos do INPE continuam atualizando |
| Problemas | `… logs backend \| grep -E "WARNING\|ERROR"`. Procure `INPE poll failed`, `weather fetch failed`, `Telegram` |
| Alertas chegando às pessoas | `docker compose … exec backend python -m app.cli test-alert` |

Para uma verificação de fora, um monitor de disponibilidade gratuito (ex.: UptimeRobot) pode vigiar
`https://<domínio>/api/health` e avisar por e-mail se o sistema cair.

## Notas de segurança

- Cada nó entra com o próprio usuário, e a ACL só deixa ele publicar os próprios dados (`infra/mosquitto/acl`).
- O `infra/mosquitto/passwd` só contém hashes com salt e precisa ser legível pelo contêiner do broker. Num servidor
  compartilhado, restrinja: `sudo chown 1883:1883 infra/mosquitto/passwd && sudo chmod 600 infra/mosquitto/passwd`
  (depois rode o `provision.sh` com `sudo`).
- Mantenha o servidor atualizado (`sudo apt upgrade`, ou ative as atualizações automáticas).
- O token do bot do Telegram, as senhas MQTT e o `recipients.json` são segredos: nunca os coloque no git.

## Stack local / de desenvolvimento

Para desenvolvimento, ou um teste no seu computador, use a stack mais simples (painel na porta 8080, MQTT sem TLS na 1883):

```bash
cp infra/.env.example infra/.env && infra/provision.sh backend
docker compose -f infra/docker-compose.yml up -d --build
```

## Postgres

Para mais de ~100 nós, ou quando precisar de consultas espaciais, use Postgres: defina
`SENTINELA_DATABASE_URL=postgresql+psycopg://usuario:senha@host/sentinela` e instale o extra `postgres`
(`pip install '.[postgres]'`, também necessário na imagem do backend). O comando `backup` só trata SQLite; para Postgres use `pg_dump`.
