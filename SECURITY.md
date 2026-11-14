# Security policy

Sentinela do Fogo sends alerts to people who may act on them, so a fake or suppressed alert matters.
Please report vulnerabilities responsibly.

## Reporting

**Do not open a public issue with details.** Open an issue titled **"Security contact request"** with no technical
information, and a maintainer will arrange a private channel. Please include what is affected (backend, firmware,
infrastructure, docs) but not how to exploit it.

We will acknowledge within a few days. This is a volunteer project, so fixes happen on a best-effort basis.

## Supported versions

Only the latest commit on `main` is supported.

## Security model in short

- **HTTP ingest** (`POST /api/readings`) needs the shared secret `SENTINELA_INGEST_TOKEN` in the `X-Ingest-Token`
  header and is disabled when no token is configured. Everything else under `/api` is read-only and public by design.
- **MQTT:** each sensor node has its own login and the broker ACL only lets it publish its own topics. Anonymous access
  is off. In production only the TLS port (8883) is exposed.
- **Secrets** (`infra/.env`, `infra/mosquitto/passwd`, `backend/config/recipients.json`, `firmware/**/secrets.h`) are git-ignored.
  Never commit bot tokens, MQTT passwords or phone numbers.
- Alerts and the dashboard are public information: they include sensor locations. Don't put a sensor where its location must stay private.

See the deployment guide in the docs for the production checklist.
