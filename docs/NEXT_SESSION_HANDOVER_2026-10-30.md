# 📋 NEXT_SESSION_HANDOVER — 2026-10-30 (obs stack recovered, per-container metrics, dashboard proxy locked down)

> Current as of **2026-10-30 ~03:10 BST**. Earlier handovers (`-10-17`, `-10-18`, `-10-20`, `-10-22`) still apply for the host, backups and secret-file layout. **No secret values appear in this file.**

---

## 🌅 START HERE

1. `cd H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4`, `git fetch`, `git status -sb`. `main` has the two commits below. The tree still holds old uncommitted work (CI, tests, compose edits, deleted/renamed notes under `autonomous AI synthesis engine/`, `docs/archive/HEALTH_CHECK_REPORT.md`). Do not bulk-commit or discard it; commit by path (`git commit -o <paths>`).
2. Check RAM before any start or build: `python scripts/ram_guard.py --for build`. WSL available was about **1,450 MB** at the end, with Grafana and Tempo stopped.
3. **Dashboard service JWT expires about 2026-11-02.** Re-run `MSYS_NO_PATHCONV=1 python scripts/rotate_jwt_secret.py` (preflight), then `--yes`, before then.

## ✅ What was done

| Item | Result |
|---|---|
| Runtime recovery | Governor, Prometheus, Alertmanager, Loki, Promtail, node-exporter, celery-exporter started one at a time under a memory watch. Loki confirmed receiving logs (~1,830 lines/min). |
| celery-worker | Concurrency 2 tripped the RAM guard, so it is now `--concurrency=1`. Pushed as `65377139`. |
| Per-container metrics | cAdvisor v0.47.2 cannot read containers on Docker Desktop's containerd image store. Newer cAdvisor (v0.55.1, v0.60.6) ballooned to 300-430 MB, so it was rejected. New `docker-stats-exporter` (stdlib Python, ~18 MB, reads the read-only socket proxy, same metric names and labels as cAdvisor) now serves 43 containers with 0 errors. Pushed as `7ec6eb29` (service in `docker-compose.observability.yml`, Prometheus job `docker-stats`, 30 s scrape). |
| Dashboard | Pattern Review page, `*_FILE` secret reads, and a private same-origin core proxy (`/api/core`) with a path/method allow-list (`lib/coreProxyPolicy.ts`). Service JWT is added on reads only; writes need the caller's own token. 34 new tests. Pushed as `fb1406cb`. Dashboard port is `127.0.0.1:8088` only (compose `docker-compose.agents.yml:295`). |
| Governor inventory | Approved by Lyndz (`governor-2026-10-29-lyndz`); a pattern packet with 2 candidates is **pending human review**. Synthesis and execution stay unauthorized. |

## 🔴 Current state (not running)

- **Grafana and Tempo are STOPPED** (stopped to free RAM for the exporter build). Grafana needs about 290 MB; starting it from 1,450 MB would land under the 1,200 MB stop line. Free room first (candidates: retire cAdvisor, about 28 MB; pause Promtail, about 50 MB), then start Grafana, then Tempo, one at a time with the watcher.
- Pyroscope, grafana-agent and prometheus-cloud were already stopped.
- **The dashboard container is the OLD code.** `fb1406cb` is pushed but not rebuilt. A rebuild needs a GREEN RAM guard.

## ⚠️ Known gaps

- Dashboard write buttons (approval respond, HyperSync handoff/redeem) will 401: the dashboard has no login and sends no token. Same result as before the proxy; fixed only by adding a login.
- `broski-bot` Prometheus target is down (connection refused :8000).
- Alertmanager receiver `alert-webhook` has no service behind it.
- Loki has no per-container label (labels are only `filename`/`job`/`service_name`).
- Grafana data sources were never checked through Grafana: its admin password env is empty in the container, so API login is impossible. I did not reset it. `docs/STATUS.md` (older notes) says the Grafana login is user `welshdog`: try that first, no reset needed.
- cAdvisor v0.47.2 still runs but produces no per-container series; the exporter replaces it. Two spare images can be deleted: `ghcr.io/google/cadvisor:v0.60.6`, `gcr.io/cadvisor/cadvisor:v0.55.1` (~107 MB each).
- `DEV_REPORT.md` claims a Governor secret mount mismatch. That is stale: Governor started fine.
- Dashboard vitest on this host: 7 "worker failed to start" timeouts on a full run (218 tests still pass). Likely RAM starvation; re-run when memory is free.

## 🪤 Traps hit this session

- Governor needs the fleet compose: the 4-file set plus `-f docker-compose.fleet.yml --profile agents --profile fleet`. Root compose does not include the fleet file.
- Never pass included files with `-f` again; use `--no-deps` for single services; never `docker compose down` to stop obs (stop by name).
- Healthcheck timeouts on tiny Python containers: the 5 s check falsely reported the exporter unhealthy under 0.1 CPU. Compose now uses a 20 s timeout and `cpus: "0.25"`.
- A memory watcher that stops on one low reading trips on host noise; use two consecutive low readings.
- PowerShell array-of-arrays syntax errors: use Bash for those.

## 🎯 ONE next task

Free about 100 MB (retire cAdvisor, pause Promtail), then restart Grafana under the memory watcher so the dashboards pick up the new per-container metrics.
