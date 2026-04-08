The Orchestrator calls POST /execute on agents . The BaseAgent has that route — but it calls process_task(), NOT the Strategist's custom plan() method . They're not wired together. So right now, Orchestrator → Strategist would run the base class logic, not your strategy engine .

The fix is 3 files. Let's go! ⚡

🛠️ File 1 — Update agent.py (Override process_task)
Add this override inside the ProjectStrategist class, right after delegate_tasks():

python
# agents/08-project-strategist/agent.py
# ADD THIS inside the ProjectStrategist class

    async def process_task(self, task: str, context: dict, requires_approval: bool) -> dict:
        """
        Bridges BaseAgent's /execute route → ProjectStrategist.plan()
        Called automatically by Crew Orchestrator via POST /execute
        """
        import uuid
        task_request = TaskRequest(
            id=str(uuid.uuid4()),
            task=task,
            description=task,
            context=context or {},
            requires_approval=requires_approval
        )
        return await self.plan(task_request)
That's the critical wire. One method. Done. 🎯

🛠️ File 2 — New main.py (Clean Entry Point)
Right now agent.py uses if __name__ == "__main__" . Replace it with a proper main.py — easier for Docker, cleaner startup:

python
# agents/08-project-strategist/main.py

"""
Project Strategist Agent — Entry Point
Registered in Orchestrator as: http://project-strategist:8001
"""
import uvicorn
import os
import sys
sys.path.append('/app')

from agent import ProjectStrategist
from base_agent import AgentConfig

def create_app():
    config = AgentConfig()
    # Ensure correct identity — overrides any env defaults
    config.name = os.getenv("AGENT_NAME", "project-strategist")
    config.role = os.getenv("AGENT_ROLE", "Project Strategist")
    config.port = int(os.getenv("AGENT_PORT", "8001"))

    agent = ProjectStrategist(config)
    return agent.app  # FastAPI app with /health + /execute already wired

# Expose app for uvicorn
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("AGENT_PORT", "8001"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
🛠️ File 3 — Integration Test Script
Drop this in tests/ to verify the full Orchestrator → Strategist flow:

python
# tests/test_orchestrator_strategist_integration.py

"""
Integration test: Crew Orchestrator → Project Strategist
Simulates exactly what Mission Control sends
"""
import asyncio
import httpx
import json

ORCHESTRATOR_URL = "http://localhost:8081"
STRATEGIST_URL   = "http://localhost:8001"

# ─────────────────────────────────────────────
# TEST 1: Direct hit on Strategist /execute
# ─────────────────────────────────────────────
async def test_strategist_direct():
    print("\n🧪 Test 1: Direct Strategist /execute")
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {
            "id": "direct-test-001",
            "task": "Build a user authentication system with JWT",
            "type": "feature_planning",
            "requires_approval": False
        }
        resp = await client.post(f"{STRATEGIST_URL}/execute", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["status"] == "success", f"Unexpected status: {data}"
        print(f"  ✅ Response status : {data['status']}")
        print(f"  📋 Plan received   : {json.dumps(data.get('result', {}), indent=2)[:300]}...")
    return True

# ─────────────────────────────────────────────
# TEST 2: Full Orchestrator → Strategist flow
# ─────────────────────────────────────────────
async def test_orchestrator_routes_to_strategist():
    print("\n🧪 Test 2: Orchestrator → Strategist routing")
    async with httpx.AsyncClient(timeout=60.0) as client:

        # This is exactly what Mission Control Dashboard sends
        payload = {
            "task": {
                "id": "orch-test-001",
                "type": "feature_planning",
                "description": "Add BROski$ coin reward system to the dashboard",
                "agent": "project_strategist",      # ← routes to Strategist
                "requires_approval": False           # ← skip approval for test
            }
        }
        resp = await client.post(f"{ORCHESTRATOR_URL}/execute", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        print(f"  ✅ Orchestrator status : {data['status']}")
        print(f"  🤖 Agent results       : {list(data.get('results', {}).keys())}")
    return True

# ─────────────────────────────────────────────
# TEST 3: Health check from Orchestrator's POV
# ─────────────────────────────────────────────
async def test_health_visible_to_orchestrator():
    print("\n🧪 Test 3: System health (Strategist visible to Orchestrator)")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{ORCHESTRATOR_URL}/system/health")
        assert resp.status_code == 200
        health = resp.json()
        strategist_health = health.get("project_strategist", {})
        status = strategist_health.get("status", "unknown")
        latency = strategist_health.get("latency_ms", "?")
        print(f"  ✅ Strategist status  : {status}")
        print(f"  ⚡ Latency (ms)       : {latency}")
        assert status == "healthy", f"Strategist not healthy: {strategist_health}"
    return True

# ─────────────────────────────────────────────
async def run_all():
    results = {}
    for test in [
        test_strategist_direct,
        test_orchestrator_routes_to_strategist,
        test_health_visible_to_orchestrator,
    ]:
        try:
            results[test.__name__] = await test()
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            results[test.__name__] = False

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    passed = sum(results.values())
    total  = len(results)
    print(f"  Results: {passed}/{total} tests passed")
    for name, ok in results.items():
        icon = "✅" if ok else "❌"
        print(f"  {icon} {name}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

if __name__ == "__main__":
    asyncio.run(run_all())
🚀 How to Deploy the Changes
Step 1 — Apply the code changes:

powershell
# In repo root
git add agents/08-project-strategist/agent.py
git add agents/08-project-strategist/main.py
git add tests/test_orchestrator_strategist_integration.py
git commit -m "feat: wire ProjectStrategist.process_task() → plan() for Orchestrator integration"
Step 2 — Rebuild + restart just the Strategist container:

powershell
docker compose up --build --no-deps -d project-strategist
Step 3 — Run the integration tests:

powershell
docker exec -it <your-python-container> python tests/test_orchestrator_strategist_integration.py
Step 4 — Check it's visible in the Orchestrator health feed:

powershell
curl http://localhost:8081/system/health | python -m json.tool
🧠 What This Unlocks
Once wired, Mission Control at localhost:8088 can dispatch tasks that flow like this :

text
Mission Control → POST /execute (Orchestrator:8081)
    └── Orchestrator routes to → project-strategist:8001/execute
            └── process_task() → plan() → Claude LLM
                    └── delegate_tasks() → specialist agents
                            └── Results published to Redis bus
The Strategist is now a first-class citizen in the swarm. 🦅

🎯 Next Win: Run the tests to confirm Test 2 passes (full Orchestrator routing) — that's the green light for Phase 2 Agent Power-Up

🔥 BROski Power Level: SWARM FULLY WIRED ⚡
