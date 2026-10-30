# 📋 NEXT_SESSION_HANDOVER — 2026-10-30 (obs stack recovered, per-container metrics, dashboard proxy locked down)

> Current as of **2026-10-30 ~18:10 BST** (updated after a long afternoon of RAM-limited recovery; the 03:10 version is superseded). Earlier handovers (`-10-17`, `-10-18`, `-10-20`, `-10-22`) still apply for the host, backups and secret-file layout. **No secret values appear in this file.**

---

## 🌅 START HERE

1. `cd H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4`, `git fetch`, `git status -sb`. `main` has the commits below (`65377139`, `7ec6eb29`, `fb1406cb`, `6b235660` docs, `cbe3e7fb` Prometheus, `a2f5e497` docs, `b3b1e0e5` broski-bot metrics fix). The tree still holds old uncommitted work (CI, tests, compose edits, deleted/renamed notes under `autonomous AI synthesis engine/`, `docs/archive/HEALTH_CHECK_REPORT.md`). Do not bulk-commit or discard it; commit by path (`git commit -o <paths>`).
2. Check RAM before any start or build: `python scripts/ram_guard.py --for build`. WSL available hovered **1,160-1,230 MB** at the end (right on the 1,200 MB stop line) with Grafana, Loki, Promtail, Tempo and Pyroscope stopped and `fcc-proxy` (227 MB) + `throttle-agent` (59 MB) running again. **Do not start anything else without room.**
   **WSL stalls:** `wsl -e free -m` hangs for minutes at a time (once ~5 min) when memory is tight, especially right after a container starts. Blank reading = stall, not necessarily low RAM. Use a watcher that treats blanks patiently (5 blanks in a row) and stops on two readings under 1,200 MB.
3. **Dashboard service JWT expires about 2026-11-02.** Re-run `MSYS_NO_PATHCONV=1 python scripts/rotate_jwt_secret.py` (preflight), then `--yes`, before then.

## ✅ What was done

| Item | Result |
|---|---|
| Runtime recovery | Governor, Prometheus, Alertmanager, Loki, Promtail, node-exporter, celery-exporter started one at a time under a memory watch. Loki confirmed receiving logs (~1,830 lines/min). |
| celery-worker | Concurrency 2 tripped the RAM guard, so it is now `--concurrency=1`. Pushed as `65377139`. |
| Per-container metrics | cAdvisor v0.47.2 cannot read containers on Docker Desktop's containerd image store. Newer cAdvisor (v0.55.1, v0.60.6) ballooned to 300-430 MB, so it was rejected. New `docker-stats-exporter` (stdlib Python, ~18 MB, reads the read-only socket proxy, same metric names and labels as cAdvisor) now serves 43 containers with 0 errors. Pushed as `7ec6eb29` (service in `docker-compose.observability.yml`, Prometheus job `docker-stats`, 30 s scrape). |
| Dashboard | Pattern Review page, `*_FILE` secret reads, and a private same-origin core proxy (`/api/core`) with a path/method allow-list (`lib/coreProxyPolicy.ts`). Service JWT is added on reads only; writes need the caller's own token. 34 new tests. Pushed as `fb1406cb`. Dashboard port is `127.0.0.1:8088` only (compose `docker-compose.agents.yml:295`). |
| MemStream outage | `memstream` had been dead since 2026-10-27 13:22 UTC (exit 137, not OOM, killed externally; restart policy did not bring it back). Restarted 10-30 ~16:00 and healthy (~34 MB). Dependents: throttle-agent (observe-only), broski-bot cogs, core `recover_policy`. Core coped without it. |
| Other dead containers | `broski-economy-consumer` (exit 137, 3 days) and `coder-agent` (exit 0, 3 days) restarted with plain `docker start` (keeps their config; `coder-agent` still has `CREW_LLM_BASE_URL=http://fcc-proxy:8083`). Both healthy. |
| Alert noise | 24 h Alertmanager silence `9298b0a7-168f-43a1-8a8f-28b3863e6512` on jobs grafana/loki/promtail/pyroscope/tempo/cadvisor (created 10-30 ~16:25 UTC, expires ~10-31 16:25 UTC). Dead `cadvisor` Prometheus job removed; `node-exporter` `scrape_timeout` 10 s -> 25 s (its scrapes take ~10 s here). Pushed as `cbe3e7fb`. |
| Upgrade report 2026-10-21 | Verified stale: every item was already executed on 10-22 (Brain fix in `main`, all five images live, core right-sized, HYPER-SILLs `bef442c`). Nothing left from it. |
| Stack Resources page | New `/resources` page + `/api/resources` route + `lib/resourceSnapshot.ts`: a live WSL gauge (GREEN/AMBER/RED on the same 1,200/1,500 MB lines as `ram_guard.py`) and a per-container memory map from Prometheus (docker-stats-exporter + node-exporter). 22 tests pass; run against live Prometheus it returned 43 containers / 1,747 MB with WSL 1,261 MB AMBER. Needs the `PROMETHEUS_URL` default `http://prometheus:9090` (dashboard shares `hypercode_agents_net` with Prometheus). Not yet seen in a browser (not deployed). |
| Governor inventory | Approved by Lyndz (`governor-2026-10-29-lyndz`); a pattern packet with 2 candidates is **pending human review**. Synthesis and execution stay unauthorized. |

## 🔴 Current state

- **STOPPED on purpose (RAM):** Grafana (grows to ~285 MB; a 10-30 start caused the long WSL stall), Loki (a start was auto-aborted on blank readings), Promtail (so no new logs reach Loki), cAdvisor (retired; container kept, scrape job removed), Tempo, Pyroscope, grafana-agent, prometheus-cloud, `coder-studio`.
- **Running healthy:** core, Prometheus, Alertmanager, node-exporter, celery-exporter, `docker-stats-exporter`, Governor, MemStream, `broski-economy-consumer`, `coder-agent`, `fcc-proxy`, `throttle-agent`. 0 unhealthy at 18:08. (`fcc-proxy` and `throttle-agent` were stopped for ~1 h to try to make build room, then restarted with `docker start` at 18:05.)
- Grafana data sources (checked from config + from inside the container): Prometheus and Postgres reachable; Loki, Tempo, Pyroscope down only because their containers are stopped. Provisioning file `monitoring/grafana/provisioning/datasources/datasource.yml` is fine.
- **The dashboard container runs the PRE-LOCKDOWN build (image built 2026-10-28 19:37 from the working tree), NOT old code.** It has Pattern Review and the `/api/core` proxy, but the proxy is still OPEN: any GET to `/api/core/api/v1/*` is forwarded with the service JWT (verified 10-30: `users/me` returns the account fields, `governance/ledger` and `operator/morning` return data). Localhost-only (`127.0.0.1:8088`), so exposure is this machine. The allow-list lockdown (`fb1406cb`) and the new `/resources` page are in `main` but not deployed. **One dashboard rebuild + recreate closes the exposure and ships the page.** It needs a GREEN RAM guard.

## ⚠️ Known gaps

- Dashboard write buttons (approval respond, HyperSync handoff/redeem) will 401: the dashboard has no login and sends no token. Same result as before the proxy; fixed only by adding a login.
- **`broski-bot` metrics: code fix PUSHED (`b3b1e0e5`), NOT LIVE.** Root cause: the container runs `python -m cogs.bot`, which never started a metrics server (it only existed in `src/bot.py`), AND `prometheus_client` was not in `requirements.txt`, so the live image does not even contain the library. Fix: new `agents/broski-bot/metrics_server.py` (fail-open, `:8000`, `PROMETHEUS_PORT`/`PROMETHEUS_ENABLED`, gauges `broski_bot_ready`/`broski_bot_guilds`), 3 lines in `cogs/bot.py`, `prometheus-client==0.19.0` pinned, 5 tests (pass). **Remaining step: rebuild + recreate the image.** The bot still runs the old image and its Prometheus target is still down. Its logs also show `autofeed: pets bridge roster unavailable (401)` (live container has `PETS_BRIDGE_API_KEY` empty, so a recreate from compose keeps it empty; not made worse) and repeated `Health check failed:` lines: not investigated.
- `HighRequestLatency` on `hypercode-core` was firing at 16:40 although a direct probe took 0.05 s. Probably a WSL-stall artefact; re-check.
- Alertmanager receiver `alert-webhook` has no service behind it.
- Loki has no per-container label (labels are only `filename`/`job`/`service_name`).
- Grafana data sources were never checked through Grafana: its admin password env is empty in the container, so API login is impossible. I did not reset it. `docs/STATUS.md` (older notes) says the Grafana login is user `welshdog`: try that first, no reset needed.
- cAdvisor is stopped and no longer scraped; the exporter replaces it. The compose service still exists. Two spare images can be deleted: `ghcr.io/google/cadvisor:v0.60.6`, `gcr.io/cadvisor/cadvisor:v0.55.1` (~107 MB each).
- `DEV_REPORT.md` claims a Governor secret mount mismatch. That is stale: Governor started fine.
- Dashboard vitest on this host: 7 "worker failed to start" timeouts on a full run (218 tests still pass). Likely RAM starvation; re-run when memory is free.

## 🪤 Traps hit this session

- Governor needs the fleet compose: the 4-file set plus `-f docker-compose.fleet.yml --profile agents --profile fleet`. Root compose does not include the fleet file.
- Never pass included files with `-f` again; use `--no-deps` for single services; never `docker compose down` to stop obs (stop by name).
- Healthcheck timeouts on tiny Python containers: the 5 s check falsely reported the exporter unhealthy under 0.1 CPU. Compose now uses a 20 s timeout and `cpus: "0.25"`.
- A memory watcher that stops on one low reading trips on host noise; use two consecutive low readings. **A watcher that ignores blank readings is blind** (it ran blind for a whole Grafana start on 10-30); a watcher that stops on any blank aborts on harmless start-up stalls. Treat blanks as a failure only after ~5 in a row.
- **Rebuild prep done for `broski-bot`:** the running image is tagged `hypercode-v24-broski-bot:rollback-20261030` (local). Build with `COMPOSE_PARALLEL_LIMIT=1 docker compose <4-file set> --profile discord build broski-bot`, recreate with `... --profile discord up -d --no-deps broski-bot`. `DISCORD_TOKEN` fingerprint before: len 72, sha256 prefix `1eed0bea` (compare after, never print the value). The service is behind `profiles: ["discord"]` in `docker-compose.core.yml`.
- **Why it was not built on 10-30:** `ram_guard.py --for build` never read GREEN in two polls (10 min, then 5.4 min); WSL available peaked at 1,435 MB (needs 1,500) and mostly sat at 1,160-1,250 MB, with `fcc-proxy` stopped it reached ~1,430 MB. The build itself is small (python:3.11-slim + 4 packages).
- To bring back a stopped container with its old config (env, proxy settings) use `docker start <name>`, not a compose recreate.
- Containers killed with exit 137 and `OOMKilled=false` were stopped from outside (Docker/WSL restart) and are NOT brought back by `unless-stopped`: check `docker ps -a --filter status=exited` after any Docker or WSL restart.
- PowerShell array-of-arrays syntax errors: use Bash for those.

## 🎯 ONE next task

**Two images are waiting on one RAM window:** `hypercode-dashboard` (closes the open proxy, ships `/resources`; do this FIRST, it is the security fix) and `broski-bot` (opens its metrics port). Rebuild and recreate `broski-bot` so its metrics port opens (code is already in `main`). It needs a GREEN RAM guard: stop `fcc-proxy` (and ideally close Windows apps) first, poll `python scripts/ram_guard.py --for build`, build, recreate with `--no-deps`, check `http://broski-bot:8000/metrics` and the Prometheus `broski-bot` target, then restart `fcc-proxy`. Roll back with the `rollback-20261030` tag if it misbehaves. After that, bring logs back one at a time: Loki, then Promtail, then Grafana last, with a watcher that treats blanks patiently. The 24 h alert silence expires ~10-31 16:25 UTC: re-silence or start the stack before then.
