# Production-Grade Delivery: Smoke Execution + Release Readiness Runbook

This document turns the smoke execution framework and `/execute/smoke` endpoint into an actionable, measurable production readiness standard. It defines how to validate reliability, scalability, and security before release, and how to deploy, monitor, and roll back safely.

## What Was Delivered (Code Map)

| File / Area | Purpose |
|---|---|
| `agents/crew-orchestrator/main.py` | `/execute/smoke` endpoint with strict guardrails + Prometheus metrics |
| `tools/smoke_framework/cli.py` | CLI runner for dev/staging/production smoke validation |
| `tools/smoke_framework/runner.py` | Parallel probes, retries, timeouts, and no-audit-leak validation checks |
| `tools/smoke_framework/reporting.py` | JSON + Markdown + JUnit report generation |
| `agents/crew-orchestrator/tests/test_execute_smoke.py` | Endpoint behavior + guardrail tests |
| `.github/workflows/ci.yml` | Smoke framework coverage gate + tightened lint/security scan scope |
| `docker-compose.yml` + `.env.example` | Smoke env vars wired for local + docker deployments |

## Scope and Non-Goals

### Scope

- Provide a **safe** smoke execution endpoint (`/execute/smoke`) that is:
  - explicitly gated and disabled by default
  - restricted to benchmark keys
  - designed to perform “no-op” validation without generating approvals or polluting task/audit history
- Provide a smoke runner that can:
  - validate service health in parallel
  - run deterministic smoke checks with retries/timeouts
  - generate machine-readable artifacts suitable for CI/CD gates

### Non-goals

- This is not a replacement for functional or end-to-end testing of full workflows.
- Performance thresholds here are **measurable targets** for the smoke endpoint; they do not guarantee overall system capacity.

## Production Readiness Definition (Measurable Success Criteria)

### Release must satisfy all “hard gates”

1. **Correctness**
   - All unit tests pass (`pytest`) and smoke framework tests pass.
   - Smoke runner returns `ok=true` for target environment.
2. **Security**
   - Smoke endpoint is disabled unless explicitly enabled.
   - Only allowlisted benchmark keys can access smoke mode.
   - No secrets are logged (API keys never appear in logs/artifacts).
3. **Audit Integrity**
   - Smoke execution does not create approvals or user tasks.
   - Task list length before/after smoke validation remains unchanged.
4. **Reliability**
   - Health probes succeed for required services.
   - On transient failures, retries succeed within configured budget (timeouts + retries).
5. **Scalability**
   - Load test target achieved for the smoke endpoint on production-like hardware with defined thresholds (see Performance Benchmarks).

### “Soft gates” (required before production, but may be environment-dependent)

- Grafana dashboards exist and show key metrics for each service.
- Alert rules are configured and tested (see Monitoring and Alerting).
- Runbook exists for incident response and rollback (see Rollback Strategy).

## `/execute/smoke` Endpoint: Implementation Guidelines

### Guardrails (must remain true)

The endpoint is designed as a benchmark and validation surface only.

- **Disabled by default**: if not enabled, the endpoint returns 404.
- **Requires explicit smoke header**: `X-Smoke-Mode: true`.
- **Requires a benchmark key**: `X-API-Key`, hashed and compared to allowlist.
- **TTL revocation**: keys expire and become revoked after the TTL window.
- **No approval path**: it must never trigger approval flows.
- **No Redis task writes**: it must not push tasks to history or create task keys.

### Environment variables

Configure these at runtime (local, staging, prod):

- `SMOKE_ENDPOINT_ENABLED` (default `false`)
- `SMOKE_KEY_ALLOWLIST` (comma-separated SHA-256 hashes of allowed benchmark keys)
- `SMOKE_KEY_TTL_SECONDS` (default `900`; set `0` to expire immediately for testing)

### Prometheus metrics requirements

Expose metrics on the orchestrator at `/metrics` and ensure scrape config includes the service.

Minimum metrics to alert on:

- `smoke_request_total{mode,result}` with `result` including pass/fail/partial
- `smoke_redis_skip_total` to verify bypass behavior

## Smoke Execution Framework: How to Run and Interpret

### Local run (developer machine)

```powershell
python -m tools.smoke_framework.cli `
  --env dev `
  --orchestrator-url http://127.0.0.1:8081 `
  --core-url http://127.0.0.1:8000 `
  --smoke-api-key YOUR_BENCH_KEY `
  --json-progress `
  --out-dir artifacts/smoke
```

Artifacts produced:

- `artifacts/smoke/smoke_dev.json` (CI-friendly summary)
- `artifacts/smoke/smoke_dev.md` (human-readable)
- `artifacts/smoke/smoke_dev.junit.xml` (test-style reporting)

### Staging run (release candidate validation)

```powershell
python -m tools.smoke_framework.cli `
  --env staging `
  --orchestrator-url https://staging-orchestrator.yourdomain `
  --core-url https://staging-core.yourdomain `
  --smoke-api-key $env:SMOKE_API_KEY `
  --json-progress `
  --out-dir artifacts/smoke
```

### Built-in “no audit leakage” validation

By default, the runner checks that `/tasks` count does not change during the smoke run (no task history pollution).

Optional stronger check (requires Redis access):

```powershell
python -m tools.smoke_framework.cli `
  --env dev `
  --smoke-api-key YOUR_BENCH_KEY `
  --redis-url redis://127.0.0.1:6379 `
  --verify-no-redis-writes
```

## Quality Gates (CI and Release)

### CI gates (must pass on every PR)

1. **Formatting**
   - `black backend tools --check`
2. **Static checks**
   - `flake8 backend tools --count --select=E9,F63,F7,F82 --show-source --statistics`
3. **Security scan**
   - `bandit -r backend tools agents/crew-orchestrator -ll -ii`
4. **Tests**
   - `pytest`
5. **Smoke framework coverage**
   - `pytest tools/smoke_framework/tests -q --cov=tools/smoke_framework --cov-report=term-missing --cov-fail-under=80`

### Release gates (must pass on staging before prod)

1. Smoke runner succeeds against staging endpoints (report `ok=true`).
2. Smoke endpoint remains guarded and access-controlled.
3. Monitoring dashboard is live and alerts are configured.
4. Load test meets performance thresholds (see Performance Benchmarks).

## Deployment Procedures (Staging → Production)

This runbook assumes Docker Compose-based deployments, but the sequencing applies to any target.

### Pre-deploy checklist

- Secrets configured (no `.env` checked in):
  - `ORCHESTRATOR_API_KEY` (if used)
  - `SMOKE_ENDPOINT_ENABLED=false` for production by default
  - `SMOKE_KEY_ALLOWLIST` set only for controlled benchmarking windows
- Confirm health endpoints exist and are reachable:
  - `core /health`
  - `crew-orchestrator /health`
  - optional: healer, dashboard

### Deploy to staging

1. Build and deploy images (or pull known tag).
2. Wait for services to become healthy.
3. Run smoke runner against staging.
4. Enable smoke endpoint temporarily only if a benchmark window is active:
   - set `SMOKE_ENDPOINT_ENABLED=true`
   - set `SMOKE_KEY_ALLOWLIST=<sha256 hashes>`
   - set `SMOKE_KEY_TTL_SECONDS` to short window (e.g., 900s)
5. Run load tests (optional on every build; required for release candidates).
6. Disable smoke endpoint after window ends:
   - set `SMOKE_ENDPOINT_ENABLED=false`

### Promote to production

1. Deploy the same image tag validated in staging.
2. Run smoke runner against production endpoints (health-only first).
3. Monitor error rates, latency, and resource usage for a soak period.
4. Only run performance benchmarks during an approved window, and disable afterward.

## Monitoring and Alerting Requirements

### Dashboards (minimum set)

Create Grafana dashboards (or panels) that show:

- Request volume and error rates per service
- Latency percentiles per endpoint (p50/p90/p99)
- Redis health and memory usage (if applicable)
- Smoke endpoint outcomes:
  - `smoke_request_total` rate by `result`
  - `smoke_redis_skip_total` rate

### Alerts (minimum set)

Recommended alert rules:

- Smoke endpoint: `result="fail"` rate above threshold (e.g., >0.1% over 5 minutes)
- Orchestrator health endpoint failing for >N minutes
- Core health endpoint failing for >N minutes
- Latency regression:
  - p99 > threshold for sustained window (environment-specific)
- Redis saturation:
  - memory usage high watermark
  - connection errors

### Operational verification

On every production deploy, verify:

- `/metrics` endpoint is scrapeable
- Dashboards show current traffic
- Alerts can fire (use a controlled test alert if available)

## Rollback Strategy (Fast, Safe, Observable)

### Rollback triggers

Rollback is required if any of the following are observed after deploy:

- Health checks failing or flapping
- sustained elevated error rate
- p99 latency regression beyond tolerance
- evidence of audit leakage (task history growth during smoke)
- security anomaly (unexpected smoke traffic or access attempts)

### Rollback actions (ordered)

1. **Disable smoke endpoint immediately** (defense-in-depth):
   - set `SMOKE_ENDPOINT_ENABLED=false`
2. Roll back to last known-good image tag (or compose revision).
3. Validate health endpoints.
4. Run smoke runner to confirm baseline behavior.
5. Confirm dashboards/alerts return to normal.

### Post-rollback protocol

- Capture artifacts:
  - smoke report JSON/MD/JUnit
  - error logs (sanitized)
  - metrics snapshots from Grafana
- Create a short RCA with:
  - what changed (tag/commit)
  - failure mode
  - mitigation and follow-up gates to prevent recurrence

## Performance Benchmarks (Smoke Endpoint)

### Why benchmark `/execute/smoke`

The smoke endpoint is intentionally minimal and guarded. It is a good early signal for infrastructure performance and request path overhead without polluting user audit history.

### Baseline targets (production-like hardware)

Targets should be measured with:

- same container image and config as production
- similar network path (LB/TLS termination)
- realistic concurrency settings

Suggested baseline thresholds:

- Throughput: **≥ 10,000 RPS** sustained during hold window
- Latency: **p99 ≤ 20ms** (smoke endpoint only)
- Error rate: **< 0.1%**
- Audit leakage: **0** (no task history growth)

If hardware or network differs significantly, keep thresholds but record the benchmark profile and scale expectations accordingly.

## Load Testing Protocol (k6 + Redis Audit Verification)

### Tooling choice

| Tool | Best for | Use |
|---|---|---|
| k6 | thresholds-as-code, repeatable CI runs, JSON output | Primary load harness |
| bombardier | quick raw ceiling sanity check | Optional quick check |

### Recommended implementation (add as repo harness)

Add a load harness that:

1. Executes `/execute/smoke` with benchmark headers at high RPS.
2. Defines thresholds that fail the run when targets are missed.
3. Verifies “no audit leakage” before/after test (task count delta).
4. Optionally samples Redis task history length during the run.

#### Example k6 script layout (thresholds-as-code)

Create: `tests/load/smoke_endpoint_load.js`

- Use `ramping-arrival-rate` scenario.
- Encode thresholds:
  - `http_req_duration: p(99)<20`
  - `http_req_failed: rate<0.001`
  - a custom counter for detected audit leakage

#### Optional Redis sampler (strong proof under load)

Create: `tests/load/redis_counter_sampler.py`

- Sample:
  - `tasks:history` length
  - `task:*` key counts (optional)
- Save samples to `artifacts/load/redis_samples.json`
- Fail the run if deltas are non-zero

### Suggested CI policy for load tests

Load testing can be expensive. Recommended policy:

- Run on `main` branch only or nightly schedule.
- Require staging environment endpoints or spin up services in CI.
- Upload JSON output as artifacts for historical comparison.

## Comprehensive Testing Protocols (Before Release)

### Reliability testing

- Restart tests:
  - rolling restart orchestrator, core, redis
  - confirm recovery without manual intervention
- Transient failure simulation:
  - temporarily block healer/dashboard endpoints
  - confirm runner retries and reports degrade states clearly

### Scalability testing

- Execute k6 smoke load test on production-like environment.
- Capture:
  - p50/p90/p99
  - CPU/memory for orchestrator container
  - Redis ops/sec (if relevant)

### Security testing

- Verify smoke endpoint access controls:
  - disabled by default returns 404
  - missing `X-Smoke-Mode` is rejected
  - missing/unknown API key is rejected
- Verify log hygiene:
  - no request headers or API keys are emitted to logs

## Release Checklist (Single-Page Summary)

1. CI green (format + flake8 + bandit + tests + coverage gate).
2. Staging deployed and smoke runner returns `ok=true`.
3. Monitoring live (dashboards populated; alerts enabled).
4. (If required) Load test passes threshold targets on staging/prod-like environment.
5. Rollback plan reviewed and verified.
6. Production deploy completed and smoke runner validated.
