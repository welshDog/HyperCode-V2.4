# 🏥 HyperCode Health Report — Quick Decision Map

Overall: **Core is SOLID** ✅ — remaining issues are “plumbing” around it.

Reference:
- Detailed status report: [HEALTH_STATUS_REPORT_2026-03-16.md](../reports/status/HEALTH_STATUS_REPORT_2026-03-16.md)
- Startup/run commands: [RUNBOOK.md](../../RUNBOOK.md)

## Quick Triage Table

| ID | Issue | Severity | Fix First? | Quick Verify |
|---:|---|---|---|---|
| F2 | Local LLM broken → agent falls back externally | 🔴 High | Yes | Celery no longer logs “Local LLM error” |
| F1 | MCP containers restart loop | 🟡 Medium | After F2 | `docker ps` shows no MCP restarts |
| F3 | Prometheus → missing Alertmanager | 🟡 Medium | After F1 | Prometheus logs stop “Error sending alerts” |
| F4 | Orchestrator “agents down” false positives | 🟡 Medium | After F3 | Orchestrator list matches running containers |
| F5 | Alembic drift on legacy dev DB | 🟡 Medium | When convenient | `alembic check` reports no drift |
| F6 | MinIO transient drive stall (recovered) | 🟡 Monitor | Monitor | No repeat “drive offline” events |
| F7 | Compose `version:` warning / minor endpoint mismatches | 🟢 Low | Later | No user-visible impact |

## 🚀 Fix F2 — Local LLM (Biggest Impact)

### What to look for

If Celery logs show something like:
- `Local LLM error: [Errno -2] Name or service not known. Falling back...`

Then the worker cannot resolve/reach the configured Ollama host.

### Root cause (most common)

The stack expects **`hypercode-ollama`** reachable on `backend-net` (DNS name `hypercode-ollama`), but:
- the service isn’t running, or
- you started a different compose file where Ollama is named differently, or
- the container is on the wrong network.

### Fix steps

Fastest (no rebuild): if the running container is called `ollama` and Celery expects `hypercode-ollama`, add a network alias:

```powershell
# Adds DNS alias "hypercode-ollama" on the backend network (works immediately)
docker network disconnect hypercode_public_net ollama
docker network connect --alias hypercode-ollama hypercode_public_net ollama
```

Then validate:

```powershell
docker exec celery-worker python -c "import urllib.request; print(urllib.request.urlopen('http://hypercode-ollama:11434/api/tags', timeout=8).read()[:200])"
```

Permanent (repo default): run the `hypercode-ollama` service defined in `docker-compose.yml`.

```powershell
# 1) Confirm the expected env from Core/Celery
docker inspect hypercode-core --format "{{json .Config.Env}}" | Select-String -Pattern "OLLAMA_HOST"

# 2) Bring up the correct Ollama service from docker-compose.yml
docker compose up -d hypercode-ollama

# 3) Confirm worker + ollama are on the same network and DNS works
docker inspect hypercode-ollama --format "{{json .NetworkSettings.Networks}}"
docker inspect celery-worker --format "{{json .NetworkSettings.Networks}}"
```

Verify from inside the worker (use whichever is available):

```powershell
# Option A: curl (if installed in the image)
docker exec celery-worker sh -lc "curl -sf http://hypercode-ollama:11434/api/tags | head"
```

```powershell
# Option B: python (works even when curl isn't present)
docker exec celery-worker python -c "import urllib.request; print(urllib.request.urlopen('http://hypercode-ollama:11434/api/tags', timeout=5).read()[:200])"
```

Success criteria:
- DNS resolves (`hypercode-ollama` reachable from `celery-worker`)
- agent runs stop falling back externally

## 🛑 Fix F1 — Stop MCP Restart Loops (If You’re Running MCP)

### Important accuracy note

The core stack in `docker-compose.yml` does **not** require MCP tool containers by default. MCP tooling is typically started via:
- `docker-compose.mcp-gateway.yml`
- `docker-compose.mcp-full.yml`

If you see `mcp-filesystem` / `mcp-postgres` restarting, you’re running an MCP compose overlay and the stdio-based tools are being treated like daemons.

### Immediate stop (stops the noise now)

```powershell
docker stop mcp-filesystem mcp-postgres
```

### Long-term fix (make them on-demand)

Move MCP tool services behind an MCP gateway, or run them only when explicitly enabled (profile-based). In MCP compose overlays, use a profile so they don’t start in “default up”.

Verify:
```powershell
docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String -Pattern "mcp-"
```

## 🔔 Fix F3 — Prometheus Alertmanager Noise

### Root cause

Prometheus is configured to send alerts to `alertmanager:9093`, but Alertmanager is not running.

Evidence lives in: [monitoring/prometheus/prometheus.yml](../../monitoring/prometheus/prometheus.yml)

### Option A (proper): add Alertmanager service

Add an `alertmanager` service and attach it to the same network as Prometheus.

### Option B (quick): disable alerting targets

Comment out or remove the `alerting:` block in `monitoring/prometheus/prometheus.yml`.

Verify:
```powershell
docker logs --tail 200 prometheus | Select-String -Pattern "Error sending alerts" -CaseSensitive:$false
```

## 🤖 Fix F4 — Orchestrator False Positives (“Agents Down”)

### Root cause

The orchestrator’s expected agent list does not match the actually-running services (profiles, renamed `*-v2` containers, or not started).

### Quick fix workflow

```powershell
# 1) What does the orchestrator think is down?
docker logs --tail 100 crew-orchestrator | Select-String -Pattern "HEALTH ALERT" -CaseSensitive:$false

# 2) What is actually running?
docker ps --format "{{.Names}}" | Sort-Object
```

Remediation:
- Update the orchestrator agent registry to match the active profile, or
- only evaluate health for “enabled” agents (profile-aware).

Verify:
- Orchestrator alerts match the container list for the active profile.

## 🗄️ Fix F5 — Alembic Drift (Legacy Dev DB)

### What’s true now

- Fresh DB migrations work (`alembic upgrade head`).
- A legacy dev DB created via `create_all` can drift from the Alembic baseline.

### Fastest safe option (dev-only): reset the Postgres data folder

This repo uses a bind mount for Postgres data (`postgres-data` maps to `${HC_DATA_ROOT}/postgres`).

```powershell
docker compose down

# Confirm what HC_DATA_ROOT is on your machine (it controls where DB data lives)
# - If you're using a .env file, it should contain HC_DATA_ROOT=...
# - Otherwise it's coming from your shell environment
Get-ChildItem .env* -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
if (Test-Path .env) { Select-String -Path .env -Pattern "^HC_DATA_ROOT=" }
Write-Output "HC_DATA_ROOT(env)=$env:HC_DATA_ROOT"

# Dev wipe: delete the Postgres data directory at ${HC_DATA_ROOT}/postgres
# Example: Remove-Item -Recurse -Force "D:\\HyperCodeData\\postgres"

# Then bring up DB + core and run migrations
docker compose up -d postgres redis hypercode-core
docker exec hypercode-core alembic upgrade head
python seed_data.py
```

Verify:
```powershell
docker exec hypercode-core alembic check
```

## 📊 Performance (Good Baseline)

From the latest status report:

| Endpoint | p95 Latency | Rating |
|---|---:|---|
| `/health` | ~13.7ms | 🟢 Excellent |
| `/api/v1/tasks/` (auth) | ~35.5ms | 🟢 Very good |

## Suggested Next Win

Do these two first because they remove the most noise and restore local-first AI:
- F2 (Local LLM reachability)
- F1 (MCP restart loop, only if MCP overlays are running)
