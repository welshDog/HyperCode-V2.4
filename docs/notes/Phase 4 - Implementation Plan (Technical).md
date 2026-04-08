# Phase 4 — Implementation Plan (Technical)

## Scope

This plan implements the Phase 4 deliverables (Monitoring + Self-Healing) as working code, configuration, tests, and evidence artifacts.

In-scope:
- Healer watchdog loop (calls `/execute/smoke` every 60s and remediates)
- Prometheus scrape integration for crew-orchestrator `/metrics`
- Grafana dashboard + alert rules for smoke and service health
- Unit + integration tests and repeatable performance benchmarks

Out-of-scope:
- Full incident paging integrations (Slack/PagerDuty)
- Kubernetes-native remediation policies (Docker-only behavior is sufficient for Phase 4)

## Technical Specifications

### A) Healer Watchdog

Behavior:
- Runs as a background coroutine inside Healer’s lifespan.
- Interval: configurable (default 60s).
- Executes a smoke probe with benchmark guardrails:
  - `POST {ORCHESTRATOR_URL}/execute/smoke` with `{"mode":"probe_health"}`
  - headers: `X-API-Key`, `X-Smoke-Mode: true`
- On down/unhealthy agents:
  - resolves agent URLs via `GET {ORCHESTRATOR_URL}/agents`
  - triggers recovery via existing `attempt_heal_agent(...)` pipeline

Configuration (Healer):
- `HEALER_WATCHDOG_ENABLED` (default false)
- `HEALER_WATCHDOG_INTERVAL_SECONDS` (default 60)
- `HEALER_SMOKE_API_KEY` (required when enabled)
- `HEALER_ORCHESTRATOR_API_KEY` (optional; used if `/agents` is protected)

Failure handling:
- If smoke key is missing, watchdog performs no work (safe noop) and logs once on startup.
- Any request/parse error results in a safe “skip cycle” without crashing the service.

Code:
- `agents/healer/main.py` implements `watchdog_loop()` and `watchdog_cycle()`.

### B) Prometheus Scrape Integration

Prometheus is configured to scrape:
- `crew-orchestrator:8080/metrics` (`job="crew-orchestrator"`)
- `hypercode-core:8000/metrics` (`job="hypercode-core"`)

Config:
- `monitoring/prometheus/prometheus.yml`

Deployment:
- Prometheus restart required to apply config changes (lifecycle reload not enabled in the current runtime command).

### C) Grafana Dashboard + Alerts

Dashboard:
- A provisioned dashboard provides:
  - `up{job="crew-orchestrator"}` stat
  - smoke request rate by mode/result
  - smoke failure rate
  - redis skip rate

File:
- `monitoring/grafana/provisioning/dashboards/smoke_metrics_dashboard.json`

Alerts:
- Crew orchestrator down: `up{job="crew-orchestrator"} == 0`
- Smoke failures detected: `sum(rate(smoke_request_total{result="fail"}[5m])) > 0`

Files:
- `monitoring/grafana/provisioning/alerting/alert-rules.yaml`
- `monitoring/prometheus/alert_rules.yml`

## Resource Requirements

### Runtime services
- `crew-orchestrator` exposing `/metrics` and `/execute/smoke`
- `healer-agent` with access to Docker socket (for restarts)
- `redis` (healer and orchestrator dependencies)
- `prometheus` + `grafana` monitoring overlay

### Dependencies
- Python: `httpx`, `redis.asyncio`, `fastapi`, `uvicorn`
- Observability: Prometheus + Grafana (already in repo)
- Optional load tooling: `k6`

## Milestones (Implementation-Oriented)

### M1 — Metrics Integration (Done)
- `/metrics` operational and contains `smoke_request_total`
- Counter increments after a smoke request
- Evidence captured in `docs/notes/Phase 4 - Tracker.md`

### M2 — Prometheus + Grafana operational visibility
- Prometheus targets show `crew-orchestrator` as `UP`
- Grafana dashboard auto-provisions and displays smoke panels
- Alerts are provisioned and visible in Grafana

### M3 — Watchdog + failure injection
- Healer watchdog enabled and calling smoke on cadence
- Force-kill an agent container and confirm:
  - detection ≤ 90s
  - remediation ≤ 5 minutes
- Capture logs + screenshots + smoke report artifacts

### M4 — Hardening and signoff
- Alerts tested via controlled failure
- Documentation updated and onboarding includes readiness checks
- Phase 4 tracker completed with evidence links

## Testing Plan

### Unit tests
- Healer health endpoint basics
- Docker adapter behavior (restart threshold logic)
- Watchdog cycle triggers healing only for down/unhealthy agents

Command:
- `pytest agents/healer/tests -q`

### Integration tests
- Smoke endpoint is callable and increments metrics
- Prometheus target includes crew-orchestrator
- Grafana provisions dashboard and alert rules (validated via logs and UI)

## Benchmarking Plan

### Local benchmark (Python)

Command:

```powershell
python tools/benchmarks/smoke_endpoint_bench.py --api-key <BENCH_KEY> --requests 2000 --concurrency 200
```

Output:
- JSON-ish dict containing `rps`, `p50_ms`, `p90_ms`, `p99_ms`, and `errors`

### Load benchmark (k6, optional)

Files:
- `tests/load/smoke_endpoint_load.js`
- `tests/load/redis_counter_sampler.py`

Command:

```powershell
k6 run --env BASE_URL=http://127.0.0.1:8081 --env SMOKE_KEY=<BENCH_KEY> tests/load/smoke_endpoint_load.js
```

## Operational Steps (Repeatable)

1) Start stack:
- `docker compose -f docker-compose.yml -f docker-compose.demo.yml --profile agents up -d --no-build`

2) Start monitoring overlay (if not already running in your environment):
- `docker compose -f docker-compose.yml -f docker-compose.demo.yml -f docker-compose.monitoring.yml up -d --no-build`

3) Restart Prometheus after config changes:
- `docker restart prometheus`

4) Enable watchdog:
- set env vars:
  - `HEALER_WATCHDOG_ENABLED=true`
  - `HEALER_SMOKE_API_KEY=<BENCH_KEY>`
  - `SMOKE_ENDPOINT_ENABLED=true`
  - `SMOKE_KEY_ALLOWLIST=<sha256 of BENCH_KEY>`
- restart `healer-agent` and `crew-orchestrator`
