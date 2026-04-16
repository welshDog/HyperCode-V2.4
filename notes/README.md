# HyperCode V2.0 — HealthFix Pack (WSL-friendly)

This folder contains **drop-in scripts + Compose overrides + alert rules + runbooks** aligned to the GitHub health audit (2026‑04‑01).

## What’s inside

- `docs/INCIDENT_RUNBOOK_2026-04-03.md` — P0/P1 incident steps (logs → recovery → cleanup → verify)
- `compose/docker-compose.override.healthfix.yml` — celery-worker tuning + memory limits for key services
- `scripts/restart-failed-agents.sh` — auto-restart the 9 failed agents (WSL / Linux)
- `scripts/disk-cleanup.sh` — safe-ish Docker disk cleanup (images/cache/volumes)
- `monitoring/prometheus/alert_rules_hypercode.yml` — Prometheus alert rules (celery, agents, disk, restarts)
- `docs/PROMETHEUS_ALERTING_WIRING.md` — how to wire the rules into Prometheus/Alertmanager
- `docs/WINDOWS_TASK_SCHEDULER_AUTORECOVERY.md` — run the recovery script every 5 minutes from Windows

## How to use (quick start)

1. Copy this folder into your repo (suggested): `HyperCode-V2.0/healthfix/`
2. Run the runbook: `docs/INCIDENT_RUNBOOK_2026-04-03.md`
3. Apply the Compose override (example):
   - From repo root:  
     `docker compose -f docker-compose.yml -f healthfix/compose/docker-compose.override.healthfix.yml up -d`

> Note: If your system uses `docker-compose` (v1) instead of `docker compose` (v2), replace commands accordingly.

