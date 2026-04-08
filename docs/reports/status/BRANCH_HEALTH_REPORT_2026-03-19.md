# Branch Health Check Report (2026-03-19)

## Scope

This report covers the current branch relative to `origin/main`, including code, Docker/compose wiring, scripts, and docs changes.

## Summary

- Python test suite is green with moderate line coverage but low branch coverage.
- Dashboard build and Vitest suite are green; Dashboard ESLint currently fails with multiple errors.
- Container vulnerability scan on the new Super Hyper BROski agent image shows HIGH vulnerabilities in transitive Python packages that should be upgraded.
- NemoClaw onboarding remains blocked by OpenShell sandbox creation not producing sandbox resources; new scripts reduce re-run thrash and add targeted diagnostics.

## Work Completed (Change Inventory)

Notable areas touched:

- NemoClaw/OpenShell integration tooling and docs (`scripts/nemoclaw/*`, `docs/integrations/nemoclaw.md`, incident report).
- New agent + compose wiring (Super Hyper BROski agent on port 8015).
- Dashboard enhancements (health endpoint, standalone scripts, dependency changes, tests).
- Observability + docs/process additions (workflows, docs inventory/process, dashboards, Prometheus rules).

## Code Quality

### Python Formatting

- `black --check` passed on:
  - `agents/healer/main.py`
  - `agents/test-agent/main.py`
  - `agents/throttle-agent/main.py`
  - `agents/super-hyper-broski-agent/main.py`
- `isort --check-only` passed on the same set.
- `python -m compileall` passed on the same set.

### Python Typing

- `mypy` is not currently reliable as a repo-wide quality gate for `agents/**/main.py` scripts (duplicate module name collisions unless run per-file).
- Running `mypy` per file still produces existing typing issues in agent code; treat this as technical debt unless the repo intends to enforce typing for agents.

### Dashboard Linting (Blocker)

`agents/dashboard`:

- `npm run lint` fails with 30 errors / 11 warnings.
- Primary error themes:
  - `@typescript-eslint/no-explicit-any` in several tests and components.
  - `react-hooks/set-state-in-effect` across multiple components (state updates directly inside `useEffect`).
  - `react/no-unescaped-entities` in one component.

Recommendation: either (a) refactor the affected effects and replace `any` with narrow types, or (b) downgrade these rules to warnings for tests-only paths to unblock merges.

## Tests

### Python (pytest)

- Result: `142 passed, 7 skipped` (plus warnings).
- Coverage (backend/app):
  - Line coverage: **75.12%** (1419 / 1889)
  - Branch coverage: **46.37%** (166 / 358)

### Dashboard (Vitest)

- Result: `11 passed`, `41 passed` assertions.

## Build / Deployment

### Docker Compose

- `docker compose config -q` succeeds (compose file parses cleanly).

### Dashboard Build

- `npm run build` succeeds.
- Note: Next.js warns about multiple lockfiles; it inferred a workspace root outside the dashboard folder.

### Super Hyper BROski Agent

- Built and started successfully under the `agents` profile.
- Verified endpoints:
  - `GET /health`
  - `GET /vibe-check`
  - `GET /metrics`

## Dependency / Vulnerability Scans

### Dashboard npm audit

- `npm audit` reports:
  - 2 HIGH: `undici`, `flatted`
  - 1 MODERATE: `next` (multiple advisories)

### Container scan (Trivy) — Super Hyper BROski Agent image

Target: `hypercode-v20-super-hyper-broski-agent:latest`

- 4 HIGH findings reported, but 3 unique vulnerabilities (one duplicated across result sections):
  - `jaraco.context` → CVE-2026-23949 (fixed in 6.1.0)
  - `starlette` → CVE-2025-62727 (fixed in 0.49.1)
  - `wheel` → CVE-2026-24049 (fixed in 0.46.2)

Recommendation: bump pinned versions (or allow safe minimums) and rebuild the image to reduce HIGH findings before merge.

## Performance Benchmarks (Lightweight)

Super Hyper BROski agent (localhost, 50 sequential requests):

- `/health`: avg ~16.17 ms
- `/metrics`: avg ~20.12 ms

These are not load tests; they are regression-friendly sanity checks.

## Documentation Completeness

- Added/updated operational docs:
  - NemoClaw integration guide + diagnostics helpers.
  - Incident report for NemoClaw over-execution.
  - Cooling playbook and strategy docs.
  - Additional docs inventory/process files and status reports.

Gaps:

- Dashboard lint failures should be reflected in docs/CI expectations (either fix lint or relax policy).
- NemoClaw “stable onboarding path” remains blocked; docs should clearly state “gateway OK, sandbox creation pending” until resolved.

## Features Implemented vs Requirements (Checklist)

- [x] Deep-dive NemoClaw over-execution analysis (logs + agents audit).
- [x] Prevent runaway NemoClaw onboarding reruns (lock + rate limit + port conflict cleanup + non-interactive mode).
- [x] Add diagnostic/monitoring helpers for NemoClaw + OpenShell (diagnose, gateway health, sandbox health).
- [x] Add unit tests for sandbox health parsing with mocked `openshell` outputs.
- [x] Cooling strategy/report docs aligned to real running state.
- [x] Super Hyper BROski agent deployed on port 8015 with health + metrics.

## Blockers Before Merge

- Dashboard ESLint failing (30 errors). This is a hard CI blocker if lint is enforced.
- HIGH vulnerabilities in the BROski agent image (transitive python deps).
- NemoClaw onboarding remains unstable/stalled at sandbox creation (environment/infra issue rather than HyperCode core logic).

## Recommended Next Actions (Pre-merge)

1) Decide policy for Dashboard lint:
   - fix errors (preferred), or
   - relax specific rules for test files and known hydration patterns.
2) Upgrade BROski agent deps to eliminate HIGH Trivy findings and rebuild.
3) For NemoClaw: use `openshell-sandbox-health.*` + `gateway-health.*` as preflight gates, and debug why `openshell sandbox create` fails to create sandbox resources (controller events + CLI verbose output).

