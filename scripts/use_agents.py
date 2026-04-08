import asyncio
import aiohttp
import json
import sys
import uuid
from typing import List

CORE_URL = "http://localhost:8000"

async def assemble_crew(agent_roles: List[str], mission_desc: str):
    """
    Assembles a crew using the Core API and assigns them a mission.
    """
    print(f"🚀 Assembling Crew: {', '.join(agent_roles)}...")
    
    # 1. Define Crew Manifest
    manifest = {
        "name": f"Builder-Crew-{uuid.uuid4().hex[:6]}",
        "agents": [
            {"name": f"{role.capitalize()}-Agent", "role": role} 
            for role in agent_roles
        ],
        "network_config": {"shared_context": True}
    }
    
    async with aiohttp.ClientSession() as session:
        # 2. Call Assembly Endpoint
        try:
            # Try localhost first
            async with session.post(f"{CORE_URL}/crews/assemble", json=manifest) as resp:
                if resp.status not in (200, 201):
                    print(f"❌ Assembly Failed: {await resp.text()}")
                    return
                data = await resp.json()
                crew_id = data["crew_id"]
                print(f"✅ Crew Assembled! ID: {crew_id}")
                
        except Exception as e:
             print(f"❌ Connection Error: {e}")
             print("   (Ensure hypercode-core is running on localhost:8000)")
             return

        # 3. Submit Mission to Orchestrator (Simulated via Direct Task)
        # Note: In full implementation, we'd post to /orchestrator/missions
        # For this pilot, we'll print the instructions for the human to paste into the Agent's Chat
        
        print("\n📋 **Mission Briefing**")
        print(f"   Task: {mission_desc}")
        print("\n👉 **Action:**")
        print("   The orchestration endpoint is ready. To execute this mission:")
        print("   POST /orchestrator/missions with payload:")
        
        mission_payload = {
            "crew_id": crew_id,
            "goal": mission_desc,
            "tasks": [
                {"role": role, "description": f"Execute part of: {mission_desc}"}
                for role in agent_roles
            ]
        }
        print(json.dumps(mission_payload, indent=2))
        
        # Optional: Auto-submit if we had the endpoint ready in this script
        # await session.post(f"{CORE_URL}/orchestrator/missions", json=mission_payload)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python use_agents.py [role1,role2] \"Mission Description\"")
        print("Example: python use_agents.py security_engineer \"Audit config.py for hardcoded secrets\"")
        sys.exit(1)
        
    roles = sys.argv[1].split(",")
    mission = sys.argv[2]
    
    asyncio.run(assemble_crew(roles, mission))
