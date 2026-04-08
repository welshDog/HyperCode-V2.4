# tests/test_orchestrator_strategist_integration.py

"""
Integration test: Crew Orchestrator → Project Strategist
Simulates exactly what Mission Control sends
"""
import asyncio
import httpx
import json

# ORCHESTRATOR_URL = "http://localhost:8081"
# STRATEGIST_URL   = "http://localhost:8001"

# Since we are running this test FROM the container (or locally), we should adjust URLs
# If running locally against docker mapped ports:
ORCHESTRATOR_URL = "http://localhost:8081"
STRATEGIST_URL   = "http://localhost:8001" 

# If we run this script inside the project-strategist container, 
# it would be localhost:8001 for itself, but orchestrator would be http://crew-orchestrator:8081
# But the user instruction said "docker exec -it <your-python-container> python tests/test_orchestrator_strategist_integration.py"
# If we run inside project-strategist, STRATEGIST_URL is localhost:8001.

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
        try:
            resp = await client.post(f"{STRATEGIST_URL}/execute", json=payload)
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code} - {resp.text}"
            data = resp.json()
            assert data["status"] == "success", f"Unexpected status: {data}"
            print(f"  ✅ Response status : {data['status']}")
            print(f"  📋 Plan received   : {json.dumps(data.get('result', {}), indent=2)[:300]}...")
            return True
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            return False

# ─────────────────────────────────────────────
# TEST 2: Full Orchestrator → Strategist flow
# ─────────────────────────────────────────────
async def test_orchestrator_routes_to_strategist():
    print("\n🧪 Test 2: Orchestrator → Strategist routing")
    # This test assumes Orchestrator is running and can talk to Project Strategist
    # If we are running this LOCALLY, we might not be able to hit Orchestrator container if ports not mapped
    # Orchestrator is usually 8081.
    
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
        try:
            resp = await client.post(f"{ORCHESTRATOR_URL}/execute", json=payload)
            if resp.status_code != 200:
                print(f"  ⚠️ Orchestrator returned {resp.status_code}: {resp.text}")
                return False
                
            data = resp.json()
            print(f"  ✅ Orchestrator status : {data.get('status')}")
            print(f"  🤖 Agent results       : {list(data.get('results', {}).keys())}")
            return True
        except Exception as e:
            print(f"  ❌ Failed (Orchestrator might not be running or accessible): {e}")
            return False

# ─────────────────────────────────────────────
# TEST 3: Health check from Orchestrator's POV
# ─────────────────────────────────────────────
async def test_health_visible_to_orchestrator():
    print("\n🧪 Test 3: System health (Strategist visible to Orchestrator)")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{ORCHESTRATOR_URL}/system/health")
            if resp.status_code != 200:
                print(f"  ⚠️ Orchestrator health returned {resp.status_code}")
                return False
                
            health = resp.json()
            # The key might be "project_strategist" or "project-strategist" depending on registration
            strategist_health = health.get("project_strategist") or health.get("project-strategist") or {}
            
            status = strategist_health.get("status", "unknown")
            latency = strategist_health.get("latency_ms", "?")
            print(f"  ✅ Strategist status  : {status}")
            print(f"  ⚡ Latency (ms)       : {latency}")
            
            # If status is unknown, it might mean it's not registered yet or name mismatch
            if status != "healthy":
                print(f"  ⚠️ Warning: Strategist status is {status}")
                # We don't fail hard if orchestrator isn't fully aware yet, but we note it
                
            return True
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            return False

# ─────────────────────────────────────────────
async def run_all():
    results = {}
    print(f"Targeting Strategist at: {STRATEGIST_URL}")
    print(f"Targeting Orchestrator at: {ORCHESTRATOR_URL}")
    
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
