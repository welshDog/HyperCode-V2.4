# Phase 4 — Monitoring & Self-Healing (Project Plan)

## Summary

Phase 4 turns existing monitoring components and the smoke execution system into an operationally reliable “detect → diagnose → remediate” loop. This phase is complete when we can:

1) observe the system in real time via Prometheus/Grafana
2) automatically detect failures using a controlled smoke signal
3) reliably recover from a forced agent failure within a defined SLA

## Objectives

1. Make observability the default
- Prometheus scrapes all critical services, including crew-orchestrator
- Grafana dashboards show health, errors, latency, and smoke outcomes

2. Operationalize a watchdog loop
- Healer runs a 60s watchdog calling `/execute/smoke`
- Healer triggers a defined remediation action on agent down/unhealthy signals

3. Prove reliability with failure injection
- Force-kill an agent and demonstrate detection + remediation within SLA
- Capture artifacts (logs, metrics snapshots, and smoke reports) as evidence

## Deliverables

### D1 — Monitoring overlay is live
- Docker monitoring compose stack running (Prometheus + Grafana + any existing exporters)
- Prometheus scrape target list includes crew-orchestrator `/metrics`
- Grafana datasource is connected to Prometheus

### D2 — Grafana dashboards and panels
- A minimum “Mission Control” dashboard with:
  - `up` status for each service
  - smoke requests (rate) and failures (rate)
  - smoke latency p95/p99 if available
  - redis health indicators (if scraped)

### D3 — Healer watchdog implementation
- Healer process executes a watchdog loop every 60s
- The watchdog:
  - calls `/execute/smoke` using benchmark guardrails
  - parses response and identifies down agents
  - triggers the agreed remediation behavior for down agents

### D4 — Runbook and proof artifacts
- Evidence bundle committed to `artifacts/` (or uploaded in CI artifacts):
  - smoke reports (JSON, MD, JUnit)
  - a failure-injection log with timestamps
  - screenshots or exported dashboard JSON (optional)

## Success Criteria (Measurable)

### Monitoring success criteria
- `curl http://127.0.0.1:8081/metrics` returns Prometheus text format
- Prometheus shows crew-orchestrator target as `UP` for at least 30 minutes
- Grafana dashboard renders smoke metrics panels with non-zero data after a smoke run

### Self-healing success criteria
- Watchdog interval: ≤ 60s between checks
- Detection SLA: agent failure detected within 90s (two checks max)
- Remediation SLA: agent restored (healthy) within 5 minutes (configurable)
- Audit leakage: 0 user-task pollution caused by smoke or watchdog activity

### Reliability success criteria (failure injection test)
- Procedure:
  1) start full stack with monitoring enabled
  2) confirm baseline `up` and smoke passes
  3) force-kill one agent container
  4) verify detection and remediation within SLA
- Evidence:
  - Healer logs include “detected down” and “remediated”
  - Grafana/Prometheus shows the agent target down and recovery

## Responsibilities (RACI)

| Workstream | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| Monitoring overlay boot + configs | Platform/Infra (Lyndz) | Lyndz | Backend/Agents | Team |
| Prometheus scrape targets + rules | Platform/Infra (Lyndz) | Lyndz | Backend/Agents | Team |
| Grafana dashboard panels | Platform/Infra (Lyndz) | Lyndz | Backend/Agents | Team |
| Healer watchdog implementation | Backend/Agents (Lyndz) | Lyndz | Platform/Infra | Team |
| Failure injection test + evidence | Backend/Agents (Lyndz) | Lyndz | Platform/Infra | Team |

## Timeline and Milestones

This plan assumes a 3-day execution window. If infrastructure constraints exist (remote hosts, limited CI runtime), extend to 5 business days.

### Milestone 1 (Day 0): Observability boot
- Monitoring stack starts via docker compose
- Prometheus UI reachable and shows base targets
- Grafana reachable and has Prometheus datasource

### Milestone 2 (Day 1): Orchestrator metrics + dashboard
- crew-orchestrator `/metrics` scraped and `UP`
- Grafana has at least one dashboard with:
  - service `up` panel
  - smoke request rate panel
  - smoke failure rate panel

### Milestone 3 (Day 2): Watchdog + failure injection
- Healer watchdog loop deployed and running
- Force-kill test passes SLA with evidence captured

### Milestone 4 (Day 3): Hardening and signoff
- Alert rules configured and validated (test alert or controlled failure)
- Runbook steps verified end-to-end
- Phase 4 declared complete

## Tracking Mechanisms

Primary tracker: `docs/notes/Phase 4 - Tracker.md`

Rules:
- Every deliverable has:
  - an owner
  - a due date
  - a link to evidence (logs, screenshots, report artifacts)
- Status updated daily:
  - Not started → In progress → Blocked → Done
- Anything blocked > 24h requires:
  - a written blocker statement
  - a mitigation plan

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Prometheus not scraping orchestrator | No visibility; Phase 4 blocked | Add orchestrator target to scrape config; verify `/metrics` |
| Watchdog causes unintended writes | Audit contamination | Enforce smoke mode guardrails; validate no-task-history delta |
| Auto-remediation flaps | Instability | Add cooldown, backoff, and “max restarts per window” caps |
| False positives from transient network | Unnecessary restarts | Use retries and require consecutive failures before remediation |

## Operational Guardrails (must remain true)

- Smoke endpoint is disabled by default in production
- Smoke access is allowlisted; benchmark key never logged
- Watchdog must not create user tasks or approvals
- Any remediation must be rate-limited and observable via logs/metrics
