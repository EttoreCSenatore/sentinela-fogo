---
sidebar_position: 10
title: Roadmap
---

# Roadmap

This is the plan we follow. Items marked **(K)** were adapted from [Kaladrius](https://github.com/facchini-miguel/kaladrius),
a mature open-source clinic management system built by a solo maintainer. It solves a different problem, but it has
already answered many questions about running a small open-source project responsibly. See
[What we learned from Kaladrius](#what-we-learned-from-kaladrius) below.

Rule of thumb for the order: **operate what exists before adding features**, and **no hardware spending** until the
software side is trustworthy.

## Done ✅

- Backend: MQTT + HTTP ingest, INPE hotspots (IBGE state filter), Open-Meteo weather, FMA+ and INPE *Risco de Fogo* (observed + 3-day forecast), sensor detection, REST + SSE API
- Alerts: Telegram live; WhatsApp, SMS and webhook built
- Dashboard (React + Leaflet), virtual stations for 4 pilot sites, sensor simulator
- ESP32 firmware (compiles, never run on a board) and a step-by-step build guide
- Docker dev stack and production stack (Caddy HTTPS, MQTT over TLS, backups), deployment guide
- Security hardening, GitHub protections (private reporting, Dependabot, branch protection)
- Bilingual docs (en / pt-BR) with screenshots; FMA+ validated against the literature and INPE

## Milestone 1: Go live and be able to trust it (next)

Goal: the system runs 24/7 on a real server and tells us when it breaks, before users do.

- [ ] Deploy to Oracle Cloud free tier (São Paulo) + DuckDNS; send a real Telegram alert to a real group *(needs the user's VM and domain)*
- [ ] Rotate the Telegram bot token and remove the `devpass` test logins before exposing anything
- [ ] **(K) Health and version endpoints:** `/api/health` checks the database and data freshness; `/api/version` for monitors and the dashboard footer
- [ ] **(K) External heartbeats** (Healthchecks.io, free): one check each for system up, daily backup, restore test, certificate expiry. A signal that *stops arriving* also warns, which covers the whole server being down. Documented in an *Operations → Monitoring* page
- [ ] **Data-freshness warnings** (specific to us): warn the maintainers when INPE hotspots, INPE risk or weather have not updated in N hours, and when a sensor node goes silent
- [ ] **(K) Weekly automated restore test:** restore the newest backup into a throwaway database and check it. A backup only counts if it restores
- [ ] **(K) Off-server backup copy** (rclone to free object storage) instead of only a local folder
- [ ] **(K) systemd timers** (backup, restore test, update) installed by `infra/provision.sh`, with a lock so runs never overlap
- [ ] **(K) Operations docs:** *Upgrade*, *Backup and restore*, *Monitoring*, *Rolling back* as separate pages (today they are sections of Deployment)

## Milestone 2: Engineering discipline

Goal: with two people, nothing important lives only in someone's head, and a bad change cannot reach production quietly.

- [ ] **(K) Decision log:** one numbered table (`#`, date, decision, reason, status), superseded rows kept, never deleted. Move the current ADR page into it and record past choices (self-hosted, FMA+ + INPE, SQLite first, no hardware yet, Oracle)
- [ ] **(K) Alembic migrations** + a CI job that runs every migration up and down on a scratch database, and fails when a model change has no migration (`alembic check`)
- [ ] **(K) CI hardening:** pin third-party Actions to commit SHAs (tag in a comment), `persist-credentials: false`, coverage floor (start at the current level, raise over time), lint (`ruff`) as a required check
- [ ] **(K) Dependabot:** 7-day cooldown for version updates (security updates still immediate), include indirect dependencies, one group per ecosystem
- [ ] **(K) Reproducible dependencies:** compiled lock file for the backend (`pip-tools` or `uv`), CI fails if it is stale
- [ ] **(K) Docs checks in CI:** broken links fail the build; a check that every English page has its pt-BR twin
- [ ] **(K) Repository hygiene:** `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CODEOWNERS`, `NOTICE` (name/logo not covered by MIT), issue and PR templates
- [ ] **(K) Semantic versioning and releases:** `0.x` tags, a `releases.yaml` (or `CHANGELOG.md`) as the single source, GitHub Releases generated from it, version shown in the dashboard footer
- [ ] Publish the backend and dashboard images to GHCR from CI, so servers pull instead of building (important on the Oracle ARM VM)

## Milestone 3: Better risk science (no hardware)

Goal: make the alerts as accurate as the open data allows.

- [ ] Calibrate FMA+ classes per biome (percentiles of FMA+ on days with nearby INPE hotspots)
- [ ] Biome boundaries (IBGE) for per-biome statistics and thresholds
- [ ] **Historical replay:** feed a real past fire episode (INPE hotspots + weather of that day) through the pipeline and check that the alert would have fired. This replaces the hardware test for now. **(K)** Kaladrius's `simulate_activity` and `advance_dates` fake-data commands are the model
- [ ] Alert quality metrics: false alarms vs. missed events per site, published in the docs
- [ ] Automatic sites from ICMBio conservation units
- [ ] History charts per site (FMA+ and weather over time)

## Milestone 4: People who respond

Goal: alerts lead to action, with accountability and privacy.

- [ ] Responder view: alert acknowledgement, notes and a status (new → acknowledged → resolved) for brigades and Defesa Civil
- [ ] **(K) Audit trail:** who acknowledged or changed what, and when; alert-delivery log per recipient and channel
- [ ] **LGPD for recipients:** phone numbers and chat IDs are personal data. Document what is stored, why and for how long, with a retention command that deletes old readings and delivery logs **(K)** `apply_retention`
- [ ] **(K) Login hardening** for the responder view: rate limiting and lockout, optional two-factor
- [ ] Per-recipient preferences: channels, severity thresholds, quiet hours for non-critical notices
- [ ] WhatsApp template messages
- [ ] **(K) Demo mode:** a public demo with sample data that resets nightly, with the logins on the landing page
- [ ] **(K) Docs: Security and privacy page, FAQ, glossary** (fire-danger terms in pt/en)
- [ ] Spanish docs (optional) for Latin American neighbours with the same fire seasons

## Milestone 5: Physical nodes

- [ ] Assemble the BOM, calibrate the MQ-2, field-test battery and solar
- [ ] Per-node calibration offsets in the backend
- [ ] OTA firmware updates (signed)
- [ ] Postgres + PostGIS when we pass ~100 nodes
- [ ] LoRaWAN AU915 gateway + ChirpStack → HTTP ingest
- [ ] Camera nodes + open smoke-detection model
- [ ] **(K) Packaging:** a one-command installer or a `.deb` with an apt repository for self-hosters, with automatic rollback if the new version does not answer its health page within 5 minutes

## What we learned from Kaladrius

| Area | Kaladrius | Sentinela today | What we do |
|---|---|---|---|
| **Domain** | Clinic management (schedule, patients, finance) | Wildfire early warning | Different problem; we only borrow the project practices |
| **Stack** | Django, PostgreSQL, HTMX; mobile app apart | FastAPI, SQLite, React, MQTT | Keep ours; adopt Postgres later for spatial queries |
| **Decisions** | 200+ numbered, dated, superseded-not-deleted | One ADR | Adopt the log (M2) |
| **Migrations** | CI reports the SQL, tests up and down, flags data-deleting ones | Columns added at startup | Alembic + CI test (M2) |
| **CI** | Actions pinned to SHAs, coverage floor 90%, lock check, translations check, docs build | Tests + builds; Actions by tag | Pin, floors, lock check (M2) |
| **Dependencies** | Dependabot with 7-day cooldown, locked, grouped | Dependabot grouped | Add cooldown and locks (M2) |
| **Updates** | VM pulls new image every 5 min, **auto-rollback** when health fails, refused versions remembered | `git pull` + compose by hand | Image publishing in M2, auto-update with rollback in M5 |
| **Backups** | Daily, weekly **restore test**, in-app warning if stale | Daily backup, no restore test | Restore test + stale-backup warning (M1) |
| **Monitoring** | Healthchecks.io for 8 signals, resource samples, Prometheus textfiles, planned stops do not page | Health endpoint only | Heartbeats + data-freshness warnings (M1) |
| **Privacy** | Per-clinic isolation, audit log, retention command, LGPD-driven decisions | Recipient data in a JSON file | Audit + retention (M4) |
| **Docs** | 3 languages, manual by role, operations, decisions, FAQ, brand | 2 languages, technical + build guides | Operations split, FAQ, glossary, security page |
| **Releases** | Semver, `releases.yaml`, version in UI, GitHub Releases | No versions yet | Start at 0.1.0 (M2) |
| **Distribution** | `.deb`, `.rpm`, Arch, Docker Compose, Google Cloud | Docker Compose, provision script | Image on GHCR first, packages later |
| **Demo** | Public demo, nightly reset, demo logins | Local dashboard only | Public demo (M4) |

### What we deliberately do not copy

- **Multi-tenancy and a proprietary-to-open path.** Sentinela is single-deployment and MIT from day one.
- **A big decision log from the start.** We start with the table and add rows as we decide, not 200 rows of back-filled history.
- **Their custom monitoring stack.** We use free Healthchecks.io plus the dashboard, and add Prometheus only if we need charts.
- **A native mobile app.** The dashboard as an installable PWA plus Telegram covers the first users.

### Where we are already ahead

- Live open data (INPE, IBGE, Open-Meteo) and a validated, published risk model
- Real-time push to the browser (SSE) and an authenticated MQTT broker with per-node ACLs
- Firmware, a hardware guide and a simulator, so the system is usable before any hardware exists
