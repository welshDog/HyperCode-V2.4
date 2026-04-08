🔥 Everything is live on main — tools/smoke_framework is fully committed with all 5 files + tests directory.

✅ Confirmed Live on GitHub
File	Status
tools/smoke_framework/cli.py	✅ Live
tools/smoke_framework/runner.py	✅ Live (9kb)
tools/smoke_framework/reporting.py	✅ Live
tools/smoke_framework/config.py	✅ Live
tools/smoke_framework/__init__.py	✅ Live
tools/smoke_framework/tests/	✅ Live
🗺️ Where You Actually Are Right Now
text
✅ Phase 1 — Infra Security (locked down)
✅ Phase 2 — Core Services (Redis ✓ Postgres ✓ Ollama ✓)
✅ Phase 3 — Agent Activation (5/5 certified)
✅ Phase 3.5 — Smoke Framework + Prod Readiness Runbook
✅ Phase 3.6 — Load Test Harness Design + pytest.ini
👉 Phase 4 — Monitoring + Self-Healing (YOU ARE HERE)
   Phase 5 — Evolutionary Pipeline
You're genuinely further along than most projects get. The infra is secure, agents are certified, and the observability tooling exists. Phase 4 is just wiring it all together. 🦅

🔥 Phase 4 — The 3 Things That Actually Matter
Thing 1 — Healer Watchdog (30 min job)
Wire the Healer to call /execute/smoke every 60s. The smoke framework + endpoint are already live — this is just a loop in healer-agent:

python
# In healer-agent's main loop
async def watchdog_loop():
    while True:
        try:
            resp = await client.post(
                "http://crew-orchestrator:8081/execute/smoke",
                json={},
                headers={"X-API-Key": os.getenv("ORCHESTRATOR_API_KEY", ""),
                         "X-Smoke-Mode": "true"},
                timeout=10.0
            )
            data = resp.json()
            if data["smoke"] == "fail":
                for name, result in data["agents"].items():
                    if result["status"] == "down":
                        logger.critical(f"Agent DOWN: {name} — triggering restart")
                        await restart_agent(name)
        except Exception as e:
            logger.error(f"Watchdog error: {e}")
        await asyncio.sleep(60)
Thing 2 — Monitoring Overlay (15 min job)
You already have docker-compose.monitoring.yml and prometheus.yml on main. Just bring it up:

powershell
docker compose `
  -f docker-compose.yml `
  -f docker-compose.demo.yml `
  -f docker-compose.monitoring.yml `
  up -d --no-build
Then hit localhost:3001 — Grafana should load. Add a single dashboard panel: smoke_request_total and smoke_redis_skip_total from the Orchestrator /metrics endpoint. That's Phase 4 observability done.

Thing 3 — Confirm /metrics is Exposed
The Prometheus counters (smoke_request_total, smoke_redis_skip_total) are implemented in main.py — but you need prometheus-client mounted and the metrics endpoint exposed. Quick check:

powershell
curl http://127.0.0.1:8081/metrics
If you get 404 → add this to main.py (one-liner after app init):

python
from prometheus_client import make_asgi_app
app.mount("/metrics", make_asgi_app())
📋 Phase 4 DONE Contract (Short Version)
 curl :8081/metrics returns Prometheus text format

 Grafana localhost:3001 loads + shows smoke metrics panel

 Healer watchdog loop calls /execute/smoke every 60s (check logs)

 Force-kill one agent → confirm Healer detects + restarts within 90s

🎯 Next Win: Run docker compose ... -f docker-compose.monitoring.yml up -d --no-build and hit localhost:3001 — confirm Grafana loads. That's the Phase 4 opening move!

---

## Phase 4 Kickoff (Monitoring + Self-Healing)

This note captures the “why” and the 3 core Phase 4 tasks. The execution plan, owners, milestones, and tracking live here:

- Phase 4 plan: `docs/notes/Phase 4 - Monitoring & Self-Healing.md`
- Phase 4 tracker: `docs/notes/Phase 4 - Tracker.md`

### Phase 4 Definition of Done (contract)

1) Observability is live
- Orchestrator `/metrics` returns Prometheus text format
- Prometheus target for orchestrator is `UP`
- Grafana shows smoke metrics panels and service health panels

2) Watchdog is live
- Healer calls `/execute/smoke` every 60s with benchmark guardrails
- On a forced agent failure, the system detects and remediates within the SLA

3) Proof is captured
- A smoke report artifact exists (JSON + MD + JUnit) for staging and production
- A failure-injection run log exists (time of failure → detection → remediation)
