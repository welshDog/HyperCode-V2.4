import requests
import time
import sys
import uuid

CORE_URL = "http://localhost:8000"
AGENT_NAME = f"test-agent-{uuid.uuid4().hex[:8]}"

def verify_fix():
    print(f"🚀 Starting verification test against {CORE_URL}")
    
    # 1. Register Agent
    print(f"🔄 Attempting to register {AGENT_NAME}...")
    payload = {
        "name": AGENT_NAME,
        "role": "tester",
        "capabilities": ["testing"],
        "topics": [],
        "health_url": "http://localhost:9999/health"
    }
    
    try:
        r = requests.post(f"{CORE_URL}/agents/register", json=payload)
        if r.status_code != 201:
            print(f"❌ Registration failed: {r.status_code} - {r.text}")
            sys.exit(1)
        
        data = r.json()
        agent_id = data.get("id")
        print(f"✅ Registered successfully. ID: {agent_id}")
        
    except Exception as e:
        print(f"❌ Connection error during registration: {e}")
        sys.exit(1)

    # 2. Send Heartbeats Loop
    print("💓 Sending heartbeats to verify persistence (Session Affinity/Single Replica)...")
    
    success_count = 0
    loops = 5
    
    for i in range(loops):
        heartbeat_payload = {
            "agent_id": agent_id,
            "status": "idle",
            "load": 0.1
        }
        
        try:
            r = requests.post(f"{CORE_URL}/agents/heartbeat", json=heartbeat_payload)
            
            if r.status_code == 200:
                print(f"   [{i+1}/{loops}] Heartbeat OK")
                success_count += 1
            elif r.status_code == 404:
                print(f"❌ [{i+1}/{loops}] Heartbeat FAILED: 404 Agent Not Found (Root Cause Detected!)")
                print("   This indicates the request hit a Core replica that doesn't have the agent in memory.")
            else:
                print(f"⚠️ [{i+1}/{loops}] Heartbeat Warning: {r.status_code}")
                
        except Exception as e:
             print(f"❌ Connection error during heartbeat: {e}")
        
        time.sleep(1)

    if success_count == loops:
        print("\n✅ PASSED: All heartbeats succeeded. The infinite registration loop is fixed.")
        sys.exit(0)
    else:
        print(f"\n❌ FAILED: Only {success_count}/{loops} heartbeats succeeded.")
        sys.exit(1)

if __name__ == "__main__":
    verify_fix()
