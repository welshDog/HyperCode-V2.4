# Regression Test Report (Full) — 2026-03-17

## Environment

- OS: Windows
- Python: 3.13.5
- Node: v22.11.0
- npm: 11.0.0
- Go: go1.24.0 windows/amd64
- Docker: Installed, daemon not running (`docker ps` cannot connect)

## Executive Summary

- Application test suites: PASS (Python, Go, Dashboard, Hyper Mission server/client)
- Coverage gates: PASS (Smoke Framework coverage >= 80%)
- Monitoring stack verification: PARTIAL (configs present; Docker daemon not running, so runtime validation not possible)
- Performance test execution: NOT RUN (requires Dockerized stack)
- Security checks: FAIL (Bandit findings, pip-audit findings, npm audit findings)
- Static quality gates: FAIL (Black formatting, isort formatting, mypy typecheck)

## Test Execution Results

### Python (unit/integration/system)

- `python -m pytest -q`
  - Result: PASS
  - Summary: 142 passed, 7 skipped
  - Notes: Deprecation warnings from FastAPI lifecycle and `datetime.utcnow()` usage, plus pytest-asyncio loop-scope deprecations

- `python -m pytest tools/smoke_framework/tests -q --cov=tools/smoke_framework --cov-report=term-missing --cov-fail-under=80`
  - Result: PASS
  - Summary: 5 passed
  - Coverage: 81.03% (threshold 80% met)

### Backend Coverage

- `cd backend && python -m pytest tests -q --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml`
  - Result: PASS
  - Summary: 107 passed, 7 skipped
  - Coverage (app total): 75%
  - Artifact: `backend/coverage.xml`

### Go (quantum-compiler)

- `cd quantum-compiler && go test -count=1 ./...`
  - Result: PASS

### Frontend (Mission Control dashboard)

- `npm -C agents/dashboard test`
  - Result: PASS
  - Summary: 5 test files passed, 15 tests passed

### Hyper Mission System

- `npm -C hyper-mission-system/server test`
  - Result: PASS
  - Summary: 1 test suite passed, 15 tests passed
  - Coverage: 52.55% statements

- `npm -C hyper-mission-system/client test`
  - Result: PASS
  - Summary: 1 test suite passed, 1 test passed

### Architect Agent (Node package)

- `npm -C agents/architect run test:cov`
  - Result: PASS
  - Summary: 1 test suite passed, 1 test passed
  - Coverage: 100% statements

## Monitoring & Logging Validation

- Monitoring compose file present: `docker-compose.monitoring.yml`
- Logging/observability tooling present in repo (Grafana/Prometheus/Loki/Tempo configs and compose definitions)
- Docker daemon status: NOT RUNNING
  - Impact: cannot validate that monitoring/logging services are actively collecting metrics/logs/traces in this environment

## Performance Test Status

- NOT RUN
- Blocker: Docker daemon is not running; the performance workflow depends on starting the stack and executing Locust workloads

## Security Test Results (Defect Log)

### Static Analysis (Bandit)

- Result: FAIL
- Findings:
  - High: Weak hash usage (MD5) in `backend/app/cache/multi_tier.py`
  - Medium: Binding to `0.0.0.0` in `backend/app/main.py` (dev server exposure)

### Dependency Audit (pip-audit)

- `python -m pip_audit -r requirements.txt`
  - Result: FAIL (dependency resolution conflict)
  - Symptom: pip resolver reports conflicting dependencies involving `PERPLEXITY`

- `python -m pip_audit -l`
  - Result: FAIL
  - Summary: 47 known vulnerabilities across 25 installed packages (examples include aiohttp/authlib/cryptography/requests/urllib3)

### Dependency Audit (npm audit, summarized)

- agents/dashboard: low=0, moderate=0, high=2, critical=0
- hyper-mission-system/server: low=1, moderate=0, high=2, critical=0
- hyper-mission-system/client: low=4, moderate=2, high=0, critical=0
- agents/architect: low=4, moderate=7, high=12, critical=0

## Static Quality Gates (Defect Log)

- Black formatting: FAIL
  - Summary: 78 files would be reformatted

- isort formatting: FAIL
  - Summary: multiple files across backend/tools/crew-orchestrator have import order diffs

- mypy: FAIL
  - Summary: 24 errors in 11 files (notably Optional defaults, missing stubs, settings attribute mismatch)

## Test Data Integrity

- Local sqlite artifact `test.db` was removed prior to run and is ignored by `.gitignore`

## Recommended Follow-ups (Prioritized)

1. Fix security findings:
   - Replace MD5 cache key hashing or explicitly mark non-security usage
   - Review dev server bind configuration
   - Create a remediation plan for pip-audit and npm audit vulnerability sets
2. Stabilize quality gates:
   - Run `black` + `isort` to normalize formatting
   - Address the 24 mypy errors or adjust typing strategy (stubs / Optional annotations / config decisions)
3. Restore full performance coverage:
   - Ensure Docker daemon is running
   - Run `docker compose up -d` and execute the Locust suite under `tests/load/`

