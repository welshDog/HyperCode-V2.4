# HyperCode V2.0 — System Health Status Report (2026-03-16)

## Executive Summary

The platform is currently **functional and stable for the core workflow** (Core API → DB → Celery → Agent → DB). Core API responds quickly, DB and Redis are healthy, and the end-to-end task pipeline successfully completed a translator job and persisted output.

However, several **degraded components** are generating noise, reducing reliability, or increasing operational risk:
- MCP tool containers (`mcp-filesystem`, `mcp-postgres`) are in a restart loop (misfit for “always-on” Docker services).
- Local LLM connectivity is broken (Celery falls back to external LLM), increasing cost and adding an external dependency.
- Prometheus is configured to alert to a missing Alertmanager, producing continuous errors.
- Crew Orchestrator reports multiple agents down due to profile/naming mismatches (monitoring false positives).
- Alembic drift exists on the long-lived DB created prior to migrations (fresh migrations are good; legacy DB requires cleanup).
- MinIO reported an intermittent disk I/O stall (recovered automatically, but needs monitoring).

Overall risk level: **Medium** (core path works; observability + AI + MCP plumbing need cleanup).

## Scope & Method

Health check included:
- **Functionality verification:** Core API endpoints + end-to-end task execution.
- **Performance assessment:** repeated latency sampling for Core endpoints.
- **Error log analysis:** targeted scans for ERROR/CRITICAL/Traceback across services.
- **Dependency validation:** DB/Redis readiness, Python package integrity, Alembic migration behavior.

## Current State Snapshot (Evidence)

### Core Services

- **Core API:** `healthy`, bound to `127.0.0.1:8000`
- **Postgres:** `healthy`, accepting connections
- **Redis:** `healthy`, `PONG`
- **Celery Worker:** `healthy`, executed a task successfully

### Key Endpoint Checks (HTTP status + time_total)

- Core `/health`: `200`, ~0.028s
- Core `/api/v1/docs`: `200`, ~0.017s
- Mission Control dashboard: `200`, ~0.049s
- Grafana login: `200`, ~0.237s
- Prometheus `/-/ready`: `200`, ~0.064s
- Loki `/ready`: `200`, ~0.009s
- Tempo `/ready`: `200`, ~0.005s
- MinIO `/minio/health/ready`: `200`, ~0.011s

### Performance Metrics (Local)

- Core `/health` latency: `n=40` avg `0.0089s`, p50 `0.00821s`, p95 `0.013766s`, max `0.017373s`
- Core `/api/v1/tasks/` latency (authenticated): `n=20` avg `0.0239s`, p50 `0.018515s`, p95 `0.035519s`, max `0.103504s`

## Functional Verification (End-to-End)

### Task Pipeline

Verified successful path:
1. `seed_data.py` authenticated + ensured project.
2. `run_swarm_test.py` created Task `id=3`.
3. Celery worker processed `hypercode.tasks.process_agent_job`, updated DB status to DONE, and saved output.
4. Core API returned Task `id=3` with `status=done` and populated `output`.

Evidence (Celery worker log highlights):
- `Task hypercode.tasks.process_agent_job[...] received`
- `[Worker] Updated Task 3 status to DONE`
- `[Worker] Saved output to /app/outputs/translate_3.md`
- `... succeeded in 12.86s`

## Detailed Findings

### F1 — MCP Tool Containers Restarting (mcp-filesystem / mcp-postgres)

- **Severity:** Medium (noise + resource churn; can mask real failures)
- **Symptoms/Evidence:**
  - `mcp-filesystem` state `restarting`, RestartCount ~`342`
  - logs repeatedly show: `Secure MCP Filesystem Server running on stdio`
  - `mcp-postgres` state `restarting`, RestartCount ~`352`
- **Root Cause:**
  - These MCP tool servers are **stdio-oriented** (intended to be spawned and managed by an MCP host/gateway), not long-running daemons. In Docker, they exit cleanly when no session is attached, and restart policies loop them forever.
- **Recommended Remediation:**
  - Option A (recommended): move these services behind the MCP gateway/orchestrator and remove/disable them from the always-on compose profile.
  - Option B: wrap them with an HTTP bridge that keeps the process alive (or configure an MCP gateway that manages stdio sessions).
- **Validation Criteria:**
  - `docker ps` shows `mcp-filesystem` and `mcp-postgres` are either stopped/disabled **or** running without restarts for 30+ minutes.
  - MCP tool calls succeed through the intended gateway path (no direct stdio container required).

### F2 — Local LLM Connectivity Broken (Celery falls back to external)

- **Severity:** High (cost + reliability + external dependency; breaks “local-first” posture)
- **Symptoms/Evidence:**
  - Celery logs: `[BRAIN] Local LLM error: [Errno -2] Name or service not known. Falling back...`
  - An `ollama` container exists, but `hypercode-ollama` is not running; `ollama` is on a different network.
- **Root Cause:**
  - Service naming/network mismatch: core/agents are configured to call `hypercode-ollama`, but the active container is `ollama` on `hypercode_public_net`, so DNS resolution from the backend network fails.
- **Recommended Remediation:**
  - Ensure the Ollama service runs as `hypercode-ollama` on the same network(s) as Celery + core (e.g., `backend-net`), and align `OLLAMA_HOST` accordingly.
  - Update “health” checks/docs to use an actual Ollama endpoint (e.g. `/api/tags`) rather than `/api/health` if unsupported.
- **Validation Criteria:**
  - From inside `celery-worker`, an HTTP GET to the configured `OLLAMA_HOST` succeeds.
  - Celery logs no longer show “Local LLM error” during agent runs.
  - End-to-end task completion succeeds with local model enabled and without external fallback.

### F3 — Prometheus Alerting Misconfigured (Alertmanager missing)

- **Severity:** Medium (continuous error noise; alerts not delivered)
- **Symptoms/Evidence:**
  - Prometheus logs: `Error sending alerts ... dial tcp: lookup alertmanager ... no such host`
- **Root Cause:**
  - Prometheus is configured with an Alertmanager target, but no `alertmanager` service exists in the running compose stack.
- **Recommended Remediation:**
  - Add an Alertmanager container to the compose stack and configure Prometheus to point at it, or remove/disable Alertmanager notifier configuration.
- **Validation Criteria:**
  - Prometheus logs contain no repeated “Error sending alerts” for 30+ minutes.
  - Test alert fires and is received by the configured alert receiver.

### F4 — Crew Orchestrator “Agents Down” Alerts (False positives)

- **Severity:** Medium (monitoring reliability issue; reduces trust in alerts)
- **Symptoms/Evidence:**
  - Crew orchestrator logs repeatedly: `HEALTH ALERT: 8 agents down: [...]`
- **Root Cause:**
  - Agent services are profile-gated and/or renamed (`*-v2` vs expected canonical names). Orchestrator appears to expect agents that are not currently running under the active compose profile/naming scheme.
- **Recommended Remediation:**
  - Align naming to a single canonical agent registry, or update orchestrator health logic to detect “enabled agents” rather than a hard-coded list.
  - Ensure `docker compose --profile agents up -d` is used when orchestrator expects the full crew.
- **Validation Criteria:**
  - Orchestrator health endpoint reports only truly-down agents.
  - “Agents down” alerts match `docker compose ps` reality.

### F5 — Alembic Drift on Long-Lived Database (legacy create_all)

- **Severity:** Medium (schema drift risk; blocks reliable migrations on existing DB)
- **Symptoms/Evidence:**
  - `alembic current` shows head, but `alembic check` reports “New upgrade operations detected” (nullable/default mismatches).
  - Fresh DB migration path was validated separately and is clean.
- **Root Cause:**
  - The existing DB was created/modified outside of the current Alembic baseline (historical `create_all`), then stamped, leaving schema differences (e.g., nullability/defaults) compared to the migration baseline.
- **Recommended Remediation:**
  - Preferred: recreate dev DB volume and run `alembic upgrade head` from scratch.
  - Alternative: add a follow-up migration that **alters legacy tables** to match the baseline (set NOT NULL, defaults, backfill where needed).
- **Validation Criteria:**
  - `docker exec hypercode-core alembic check` returns “No new upgrade operations detected.” on the primary DB.
  - `alembic upgrade head` succeeds on a clean DB and the existing dev DB.

### F6 — MinIO Intermittent Drive Offline (Recovered)

- **Severity:** Medium (data-plane risk if repeated; currently self-healed)
- **Symptoms/Evidence:**
  - MinIO log: `taking drive /data offline: unable to write+read for 44.592s`, then `bringing drive /data online`
- **Root Cause (likely):**
  - Transient disk I/O stall in Docker Desktop volume storage path.
- **Recommended Remediation:**
  - Monitor recurrence; ensure Docker Desktop has sufficient disk space and stable storage backend.
  - Consider explicit resource limits and avoiding heavy concurrent disk activity during builds.
- **Validation Criteria:**
  - No repeated “drive offline” events over a sustained run (e.g., 24h).
  - MinIO readiness stays `200` and object operations succeed under load.

### F7 — Minor Operational Noise

- **Severity:** Low
- **Items:**
  - `docker-compose.yml` includes obsolete `version` key (warning only).
  - Ollama health endpoint used in some checks returns `404` (health check path mismatch, not necessarily service failure).

## Prioritized Action Items (with timelines)

1. **Fix local LLM connectivity (F2)** — High priority, same-day
2. **Stop MCP tool restart loops (F1)** — High priority, same-day
3. **Resolve Prometheus → Alertmanager config mismatch (F3)** — Medium priority, 1–2 days
4. **Fix Orchestrator agent health false positives (F4)** — Medium priority, 1–2 days
5. **Eliminate Alembic drift on main dev DB (F5)** — Medium priority, 1–3 days (depending on whether DB reset is acceptable)
6. **Investigate MinIO intermittent I/O stall (F6)** — Medium priority, monitor + 1 week hardening if recurring
7. **Clean up low-level warnings (F7)** — Low priority, opportunistic

## Security Notes (Operational)

- Ensure `ENVIRONMENT=production` is only used when production secrets are set (JWT secret, MinIO creds, etc.). The stack previously failed hard when `ENVIRONMENT=production` was set with defaults.
- Avoid exposing internal services broadly; Core is correctly bound to localhost-only (`127.0.0.1:8000`).

