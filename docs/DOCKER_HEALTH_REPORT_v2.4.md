# HyperCode V2.4 — Docker Health Report
**Generated:** 2026-03-29
**Branch:** `feature/hyper-agents-core`
**Platform:** Windows 11 / Docker Desktop (WSL2 backend)

---

## TL;DR

| Status | Count | Services |
|--------|-------|----------|
| 🟢 Healthy | 18 | All core services |
| 🔴 Crash-loop (fixed) | 1 | `healer-agent` |
| 🟡 No healthcheck | 5 | `auto-prune`, `loki`, `project-strategist-v2`, `promtail`, `security-scanner` |
| 🔵 Profile-gated (not started) | 1 | `throttle-agent` |
| 📉 Prometheus DOWN | 2 | `hypercode-core` (no `/metrics`), `throttle-agent` (not running) |

---

## Container Status — Full Table

| Container | Status | Ports | Health |
|-----------|--------|-------|--------|
| `hypercode-core` | Up 7 min | `127.0.0.1:8000→8000` | ✅ healthy |
| `hypercode-dashboard` | Up 9 min | `127.0.0.1:8088→3000` | ✅ healthy |
| `crew-orchestrator` | Up 9 min | `0.0.0.0:8081→8080` | ✅ healthy |
| `super-hyper-broski-agent` | Up 9 min | `0.0.0.0:8015→8015` | ✅ healthy |
| `test-agent` | Up 9 min | `0.0.0.0:8013→8080` | ✅ healthy |
| `tips-tricks-writer` | Up 9 min | `0.0.0.0:8011→8009` | ✅ healthy |
| `healer-agent` | Restarting → **fixed** | `8008` | 🔴→🟢 (see §Fixes) |
| `hyperhealth-api` | Up 4 min | `127.0.0.1:8095→8090` | ✅ healthy |
| `hyperhealth-worker` | Up 7 min | `8090` | ✅ healthy |
| `hyper-mission-api` | Up 9 min | `5000` | ✅ healthy |
| `hyper-mission-ui` | Up 9 min | `127.0.0.1:8099→80` | ✅ (no healthcheck) |
| `celery-worker` | Up 9 min | `8000/tcp` | ✅ healthy |
| `celery-exporter` | Up 9 min | `0.0.0.0:9808→9808` | ✅ healthy |
| `redis` | Up 9 min | `6379/tcp` | ✅ healthy |
| `postgres` | Up 9 min | `5432/tcp` | ✅ healthy |
| `chroma` | Up 9 min | `127.0.0.1:8009→8000` | ✅ healthy |
| `minio` | Up 9 min | `127.0.0.1:9000-9001→9000-9001` | ✅ healthy |
| `cadvisor` | Up 38 sec | `0.0.0.0:8090→8080` | ✅ healthy |
| `prometheus` | Up 9 min | `0.0.0.0:9090→9090` | ✅ healthy |
| `grafana` | Up 9 min | `0.0.0.0:3001→3000` | ✅ healthy |
| `node-exporter` | Up 9 min | `0.0.0.0:9100→9100` | ✅ healthy |
| `loki` | Up 9 min | `0.0.0.0:3100→3100` | 🟡 no healthcheck |
| `tempo` | Up 9 min | `0.0.0.0:3200→3200` | ✅ running |
| `promtail` | Up 9 min | — | 🟡 no healthcheck |
| `auto-prune` | Up 9 min | — | 🟡 no healthcheck |
| `project-strategist-v2` | Up 9 min | — | 🟡 no healthcheck |
| `security-scanner` | Up 9 min | — | 🟡 no healthcheck |
| `throttle-agent` | Not started | — | 🔵 profile: agents |

---

## Endpoint Health Checks

| Endpoint | URL | Response |
|----------|-----|----------|
| hypercode-core | `http://localhost:8000/health` | `{"status":"ok","service":"hypercode-core","version":"2.0.0"}` |
| crew-orchestrator | `http://localhost:8081/health` | `{"status":"ok","service":"crew-orchestrator"}` |
| super-hyper-broski | `http://localhost:8015/health` | `{"status":"healthy","vibe":100,"energy":100}` |
| test-agent | `http://localhost:8013/health` | `{"status":"ok","uptime_seconds":633}` |
| hyperhealth-api | `http://localhost:8095/health` | `{"status":"ok","service":"hyperhealth","version":"1.1.0"}` |
| grafana | `http://localhost:3001` | 302 → login page ✅ |
| prometheus | `http://localhost:9090` | UI accessible ✅ |

---

## Prometheus Scrape Targets (9 total)

| Job | Target | Status |
|-----|--------|--------|
| `cadvisor` | `cadvisor:8080/metrics` | ✅ UP |
| `celery-exporter` | `celery-exporter:9808/metrics` | ✅ UP |
| `crew-orchestrator` | `crew-orchestrator:8080/metrics` | ✅ UP |
| `hypercode-core` | `hypercode-core:8000/metrics` | ❌ DOWN — 404, no `/metrics` route |
| `minio` | `minio:9000/minio/v2/metrics/cluster` | ✅ UP |
| `node-exporter` | `node-exporter:9100/metrics` | ✅ UP |
| `prometheus` | `localhost:9090/metrics` | ✅ UP |
| `test-agent` | `test-agent:8080/metrics` | ✅ UP |
| `throttle-agent` | `throttle-agent:8014/metrics` | ❌ DOWN — container not started (profile: agents) |

**7/9 targets UP (78%)**

---

## Issues Found & Fixes Applied

### 🔴 FIXED — healer-agent crash-loop

**Root cause 1:** `mape_k_api.py:16` — comment said "Absolute import" but code used relative import `from .mape_k_engine import KnowledgeBase`. When `main.py` loads `mape_k_api` as a top-level module via `sys.path`, it has no parent package, so Python raises `ImportError: attempted relative import with no known parent package`.

**Fix:** Changed to `from mape_k_engine import KnowledgeBase` (absolute, matching the `sys.path.insert` already present).

**Root cause 2:** `mape_k_engine.py:26` — mixed indentation in `try` block: line 26 used 3 spaces, line 27 used 4 spaces → `IndentationError: unexpected indent`.

**Fix:** Standardised to 4-space indent throughout the `try` block.

### 📉 KNOWN — hypercode-core has no `/metrics` endpoint

Prometheus config (`prometheus.yml`) scrapes `hypercode-core:8000/metrics` but the FastAPI app returns `404`. The core API is healthy — it just doesn't expose Prometheus metrics.

**Action required:** Add `prometheus-fastapi-instrumentator` to `hypercode-core` to expose `/metrics`.

### 🔵 KNOWN — throttle-agent not started

`throttle-agent` is gated behind `profiles: ["agents"]` in `docker-compose.yml`. Prometheus still has it as a scrape target, causing a permanent DOWN state when running the default profile.

**Options:**
- Start it: `docker compose --profile agents up -d throttle-agent`
- Or remove its Prometheus target until it's deployed

### 🟡 INFO — node-exporter broken pipe errors

`node-exporter` logs hundreds of `write: broken pipe` errors. These are **harmless** — Prometheus closed the HTTP connection mid-stream after reading what it needed. Not an error state; node-exporter remains healthy.

### 🟡 INFO — cadvisor startup warnings

cadvisor logs warnings about missing `/etc/machine-id`, `/sys/class/dmi/id/product_name`, and missing CRI-O/Podman sockets. All **expected** on Docker Desktop (Windows WSL2) — these are Linux-specific paths unavailable in this environment. cadvisor is healthy and scraping container metrics correctly.

### 🟡 INFO — security-scanner image not found

`security-scanner` (Trivy) cannot find `hypercode-core:latest` as a local Docker image — it was likely built with a different tag or only exists in the registry. Not a runtime blocker; the container exits cleanly after each scan attempt.

---

## Services Without Healthchecks

These containers have no `healthcheck` configured in `docker-compose.yml`. They show as "running" but Docker cannot verify they're actually serving traffic:

| Service | Suggested healthcheck |
|---------|----------------------|
| `auto-prune` | N/A — cron-style job, expected |
| `loki` | `curl -f http://localhost:3100/ready` |
| `project-strategist-v2` | `curl -f http://localhost:<port>/health` |
| `promtail` | `wget -q http://localhost:9080/ready` |
| `security-scanner` | N/A — one-shot scanner, expected |

---

## Pre-Launch Checklist for v2.4

- [x] Core API (`hypercode-core`) — healthy, responding
- [x] Dashboard (`hypercode-dashboard`) — healthy on port 8088→3000
- [x] Crew Orchestrator — healthy, metrics exposed to Prometheus
- [x] Redis — healthy
- [x] Postgres — healthy
- [x] Celery worker + exporter — healthy
- [x] BROski agent — healthy, vibe:100
- [x] Grafana + Prometheus + Loki + Tempo — all up
- [x] healer-agent import bugs — **fixed**
- [ ] `hypercode-core` — add `/metrics` Prometheus endpoint
- [ ] `throttle-agent` — start with agents profile OR remove from Prometheus config
- [ ] Add healthchecks to `loki`, `project-strategist-v2`, `promtail`

---

*Report generated by Claude Code (claude-sonnet-4-6) — HyperCode V2.4 pre-launch audit*
