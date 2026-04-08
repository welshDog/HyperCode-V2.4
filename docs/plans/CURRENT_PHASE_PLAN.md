# Current Phase Plan: Boot, Stability & Mission Control 🚀

This document outlines the actionable work plan for Phase 0 (Boot/Verify), Phase 1 (Stability), and Phase 5 (Mission Control).

## ⚡ Phase 0: Boot + Verify
**Goal:** Establish a verified baseline for the system's health and performance.

### 0.1 Start-up Ritual
**Description:** Bring up the full Hyper Station environment, including Mission Control and Grafana, and confirm all core services are healthy.
**Status:** **Pending**
**Tasks:**
- [x] Fix 'monitoring/tempo/tempo.yaml' syntax error.
- [x] Verify 'docker-compose.yml' env mapping and tempo service definition.
- [ ] Launch Hyper Station (all containers up).
- [ ] Verify Mission Control UI is accessible and responsive.
- [ ] Verify Grafana dashboards are populating with live data.
- [ ] Confirm core services (Orchestrator, Healer) are reporting "Healthy" status.
**Acceptance Criteria:**
- `docker ps` shows all expected containers running.
- No critical errors in startup logs.
- Mission Control and Grafana endpoints return 200 OK.

### 0.2 Baseline Snapshot
**Description:** Record current uptime metrics and existing alerts to establish a baseline for spotting regressions.
**Status:** **Pending**
**Tasks:**
- [ ] Document current uptime percentage for key services.
- [ ] List all currently firing alerts or warnings.
- [ ] Record resource usage (CPU/Memory) for main containers.
**Acceptance Criteria:**
- Baseline report created (e.g., in `docs/reports/baseline_YYYY-MM-DD.md`).
- Known issues list updated with any immediate findings.

---

## 🛠️ Phase 1: Stabilize the Core
**Goal:** Harden the system against failures and eliminate configuration drift.

**Phase 1 Wiring Plan:** See `docs/plans/PHASE1_WIRE_IT_UP.md`

### 1.1 Config Consolidation
**Description:** Align services to a centralized settings approach to reduce hardcoding and "works on my machine" issues.
**Status:** Pending
**Tasks:**
- [ ] Audit codebase for hardcoded configuration values (API keys, paths, timeouts).
- [ ] Refactor services to use centralized configuration (env vars / config service).
- [ ] Standardize logging formats across services.
**Acceptance Criteria:**
- Zero hardcoded secrets or environment-specific paths in source code.
- Services successfully load configuration from the shared source.

### 1.2 Agent Resilience Patterns
**Description:** Implement reliability patterns (circuit breaker + backoff) for Healer and Orchestrator agents.
**Status:** Pending
**Tasks:**
- [ ] Implement Circuit Breaker pattern in Orchestrator for external calls.
- [ ] Implement exponential backoff strategies for Healer agents.
- [ ] Add retry logic with jitter for dependency failures.
**Acceptance Criteria:**
- System automatically recovers from simulated dependency outages.
- Logs demonstrate correct retry behavior with backoff.

---

## 🚀 Phase 5: Mission Control (Product Surface)
**Goal:** Deliver tangible improvements to the user-facing product surface.

### 5.1 Dashboard Metrics Panel (Mission Control Wins)
**Description:** Ship a noticeable improvement to the Mission Control dashboard/terminal, focusing on usability and speed.
**Status:** **Completed**
**Tasks:**
- [x] Implement Dashboard Metrics Panel (MetricsPanel.tsx).
- [x] Update 'api.ts' with strict types.
- [x] Create unit tests for MetricsPanel.
- [x] Verify Dashboard Build.
**Acceptance Criteria:**
- Dashboard loads and displays metrics under the performance threshold.
- User feedback confirms improved usability/clarity.
- New panel successfully displays the targeted metrics.
- Build passes verification.

### 5.2 API Iteration Loop
**Description:** Pick 1–2 endpoints under active development, add comprehensive tests, and lock their contracts.
**Status:** Pending
**Tasks:**
- [ ] Select 1-2 critical endpoints (e.g., `/status`, `/agent/task`).
- [ ] Write integration tests covering success and failure scenarios.
- [ ] Freeze the API contract (OpenAPI/Swagger spec).
**Acceptance Criteria:**
- >90% test coverage for the selected endpoints.
- OpenAPI documentation accurately reflects the implementation.
- Breaking changes are prevented by CI checks.
