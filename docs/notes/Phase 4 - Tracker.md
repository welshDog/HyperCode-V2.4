# Phase 4 Tracker — Monitoring & Self-Healing

Owner: Lyndz  
Status: In progress  
Start date: 2026-03-11  
Target completion: 2026-03-14  

## Milestones

| Milestone | Target date | Status | Evidence link |
|---|---:|---|---|
| M1: Monitoring overlay boots | 2026-03-11 | ✅ Done | See M1 Evidence below |
| M2: Orchestrator metrics scraped + Grafana panels | 2026-03-12 | 👉 In progress | |
| M3: Healer watchdog running + failure injection passes SLA | 2026-03-13 | ✅ Done | [m3_evidence_20260312T013733Z](../../artifacts/phase4/m3_evidence_20260312T013733Z/) |
| M4: Alerts + runbook validated, phase signoff | 2026-03-14 | 👉 In progress | See M4 Evidence below |

## Deliverables Checklist

### D1 — Monitoring overlay live
- [x] Start monitoring stack via docker compose (Prometheus + Grafana)
- [x] Confirm Prometheus UI reachable
- [x] Confirm Grafana UI reachable and Prometheus datasource exists

### D2 — Prometheus targets include crew-orchestrator
- [x] crew-orchestrator exposes `/metrics`
- [x] Prometheus scrapes crew-orchestrator `/metrics` and target is `UP`
- [x] `up{job="crew-orchestrator"}` is visible in Prometheus
- [x] `prometheus.yml` updated with crew-orchestrator scrape config

### D3 — Grafana dashboard exists (Mission Control minimum)
- [ ] Service health: `up` panel for core/orchestrator/agents
- [ ] Smoke traffic: request rate panel (by result)
- [ ] Smoke failures: failure rate panel
- [ ] Latency panel(s) if available

### D4 — Healer watchdog loop
- [x] Healer calls `/execute/smoke` every 60s with benchmark guardrails
- [x] Healer logs show success and failure paths
- [x] Remediation behavior defined and implemented (restart)

### D5 — Failure injection proof
- [x] Baseline: smoke passes on steady-state system
- [x] Force-kill an agent container
- [x] Detect within 90s and remediate within 5 minutes
- [x] Capture evidence bundle (metrics + timestamps + container events)

### D6 — Alerting and runbook
- [x] Prometheus alert rules: `monitoring/prometheus/alert_rules.yml`
- [x] Grafana alert rules: `monitoring/grafana/provisioning/alerting/alert-rules.yaml`
- [x] At least one alert validated via controlled failure (D5 dependency)
- [ ] Rollback steps documented and verified

### D7 — Load + benchmark harness
- [x] k6 load test: `tests/load/smoke_endpoint_load.js`
- [x] Redis counter sampler: `tests/load/redis_counter_sampler.py`
- [x] Python benchmark runner: `tools/benchmarks/smoke_endpoint_bench.py`

---

## Daily Standup Log

### Date: 2026-03-11 (Evening — M1 Complete 🔥)
- Done:
  - Phase 4 kickoff docs created (plan + tracker + Healer Watchdog.md)
  - `/metrics` endpoint live at `http://127.0.0.1:8081/metrics` (200 OK)
  - `smoke_request_total` counter confirmed incrementing (0.0 → 1.0 on POST)
  - `smoke_redis_skip_total` confirmed at 1.0 (zero audit leakage verified)
  - M1 evidence bundle committed to tracker
  - D1 + D2 deliverables fully checked off
- Next: Monitoring stack + Grafana panels (M2), then Healer watchdog (M3)
- Blockers: None
- Evidence captured: Full `/metrics` output + POST response in M1 Evidence section

### Date: 2026-03-11 (Night — M2 + M3 Complete 🔥🔥)
- Done:
  - Healer watchdog loop implemented (`agents/healer/main.py` — 19kb)
  - Watchdog calls `/execute/smoke` on cadence, triggers remediation for `down`/`unhealthy`
  - Prometheus scrape config updated for crew-orchestrator (`monitoring/prometheus/prometheus.yml`)
  - Grafana provisioned dashboard live (`smoke_metrics_dashboard.json`)
  - Grafana + Prometheus alert rules provisioned
  - k6 load harness + Redis sampler + Python benchmark runner all committed
  - Healer env vars wired into `docker-compose.yml`
  - `test_watchdog.py` + `test_healer_main.py` passing
  - Full test suite passes: `pytest tools/smoke_framework/tests agents/crew-orchestrator/tests agents/healer/tests -q`
  - `docker-compose.monitoring.yml` conflicts resolved
  - New User Setup Guide updated with readiness checks
  - Phase 4 Technical Implementation Plan committed
- Next: M4 — failure injection test, alert validation, phase signoff
- Blockers: None
- Evidence captured: All files committed to `main`; test suite green

### Date: YYYY-MM-DD
- Done:
- Next:
- Blockers:
- Evidence captured:

## M1 Evidence (Prometheus Metrics Integration)

Timestamp (UTC): 2026-03-11T19:33:09Z  
Executed by: Trae IDE automation (GPT-5.2)

### Full `/metrics` output

```text
smoke_request_total{mode="noop",result="pass"} 1.0
smoke_redis_skip_total 1.0
process_resident_memory_bytes 7.7348864e+07
python_info{version="3.11.8"} 1.0
```

Full output committed to tracker v1 (2026-03-11T19:38:36Z commit 39ac77b).

---

## M2 Evidence (Prometheus Scrape + Grafana)

Timestamp (UTC): 2026-03-11T~21:40Z  

- `monitoring/prometheus/prometheus.yml` — crew-orchestrator scrape job added
- `monitoring/grafana/provisioning/dashboards/smoke_metrics_dashboard.json` — provisioned
- `monitoring/grafana/provisioning/alerting/alert-rules.yaml` — provisioned
- `monitoring/prometheus/alert_rules.yml` — Prometheus rules committed

---

## M3 Evidence (Healer Watchdog)

Timestamp (UTC): 2026-03-11T~21:40Z  

- `agents/healer/main.py` (19kb) — watchdog loop + remediation logic live
- `agents/healer/tests/test_watchdog.py` — unit tests passing
- `agents/healer/tests/test_healer_main.py` — integration tests passing
- `docker-compose.yml` lines 1126–1146 — env vars wired
- Env vars: `HEALER_WATCHDOG_ENABLED`, `HEALER_WATCHDOG_INTERVAL_SECONDS`, `HEALER_SMOKE_API_KEY`, `HEALER_ORCHESTRATOR_API_KEY`

### M3 Validation Run (Failure Injection + SLA Proof)

Evidence archive:
- [m3_evidence_20260312T013733Z](../../artifacts/phase4/m3_evidence_20260312T013733Z/)

SLA results:
- Detection latency: `9.3s` (≤ 90s ✅)
- Remediation time: `7.3s` (≤ 300s ✅)
- Window timestamps (UTC): baseline `2026-03-12T01:37:36.7686543Z`, kill `2026-03-12T01:37:39.1516728Z`, detect `2026-03-12T01:37:48.4612594Z`, recovered `2026-03-12T01:37:55.7950974Z`

Quantifiable service level data (captured in evidence archive):
- Uptime snapshot (Prometheus `up`): crew-orchestrator `100%` (15m/1h), hypercode-core `100%` (15m/1h)
- Smoke endpoint response-time benchmark: p50 `168.87ms`, p90 `254.61ms`, p99 `393.35ms`, errors `0/800`, throughput `246.68 rps`
- Smoke error-rate snapshot (probe_health, 5m): `0%` (no probe_health traffic in that 5m window)

**Enable commands:**
```bash
SMOKE_ENDPOINT_ENABLED=true
SMOKE_KEY_ALLOWLIST=<sha256 of HEALER_SMOKE_API_KEY>
HEALER_WATCHDOG_ENABLED=true
HEALER_SMOKE_API_KEY=<raw key>
```
```powershell
docker compose -f docker-compose.yml -f docker-compose.demo.yml --profile agents restart crew-orchestrator healer-agent
```

---

## M4 Checklist (Next — Failure Injection + Signoff)

- [ ] Run baseline smoke: all agents pass
- [ ] Force-kill one agent: `docker compose kill <agent>`
- [ ] Confirm Healer detects within 90s (check logs)
- [ ] Confirm agent restarts within 5 min
- [ ] Trigger an alert rule via controlled failure, confirm fires
- [ ] Capture full evidence bundle (logs + smoke report + metrics export)
- [ ] Update runbook with post-failure steps
- [ ] Phase 4 sign-off by Lyndz

---

## M4 Evidence (Alert Validation Drill)

Validation run:
- [m4_alert_validation_20260312T093622Z](../../artifacts/phase4/m4_alert_validation_20260312T093622Z/)

Controlled failure scenario:
- Induced scrape failure by stopping `crew-orchestrator` container
- Alert validated: `CrewOrchestratorDown` (Prometheus rule `monitoring/prometheus/alert_rules.yml`)
- Notification delivery validated via Alertmanager -> webhook (`monitoring/alertmanager/alertmanager.yml` -> `monitoring/alert-webhook/`)

Measured latencies (from `summary.json` in evidence archive):
- Alert detection latency: `95.0s` (rule `for: 60s` + scrape/eval intervals)
- Alert delivery latency (to webhook): `92.2s`
- Alert clear latency after recovery: `40.2s`
- Resolved delivery latency (to webhook): `54.7s`

---

## Load + Benchmark Harness

```powershell
# Python benchmark (quick)
python tools/benchmarks/smoke_endpoint_bench.py --api-key <BENCH_KEY> --requests 2000 --concurrency 200

# k6 load test (full)
k6 run --env BASE_URL=http://127.0.0.1:8081 --env SMOKE_KEY=<BENCH_KEY> tests/load/smoke_endpoint_load.js
```

Targets: ≥10k RPS | p99 ≤20ms | redis_write_leaks == 0

---

## Blockers Log

| Date | Blocker | Owner | Mitigation | ETA |
|---|---|---|---|---:|
|  |  |  |  |  |

## Evidence Bundle Index

- Smoke reports: `artifacts/smoke/`
- Load test results: `artifacts/load/`
- Grafana dashboard: `monitoring/grafana/provisioning/dashboards/smoke_metrics_dashboard.json`
- Prometheus alerts: `monitoring/prometheus/alert_rules.yml`
- Grafana alerts: `monitoring/grafana/provisioning/alerting/alert-rules.yaml`
- Incident/failure injection log: (path — to be captured in M4)
