from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import uuid
import datetime
import logging
from contextlib import asynccontextmanager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-factory")

# --- LIFECYCLE ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic (e.g., connect to DB/Redis if needed)
    # For now, we just mock the registry
    logger.info("Agent Factory initialized")
    
    yield
    
    # Shutdown logic
    logger.info("Agent Factory shutting down")

app = FastAPI(
    title="Hyper Agent Factory", 
    description="Creates and manages specialized AI agents for HyperCode",
    version="0.1.0", 
    lifespan=lifespan
)

class AgentProfile(BaseModel):
    name: str
    role: str
    capabilities: List[str]
    config: Dict[str, str]

class AgentInstance(BaseModel):
    id: str
    profile: AgentProfile
    status: str  # initializing, running, idle, error, stopped
    port: int
    created_at: str
    health_url: str

# --- Mock State (Replace with Redis/Postgres) ---
REGISTRY: Dict[str, AgentInstance] = {}
BLUEPRINTS: Dict[str, AgentProfile] = {
    "frontend-specialist": AgentProfile(
        name="Frontend Specialist",
        role="frontend",
        capabilities=["react", "tailwind", "vite"],
        config={"model": "gpt-4-turbo"}
    ),
    "backend-specialist": AgentProfile(
        name="Backend Specialist",
        role="backend",
        capabilities=["python", "fastapi", "postgres"],
        config={"model": "gpt-4-turbo"}
    ),
    "tips-tricks-writer": AgentProfile(
        name="Tips & Tricks Writer",
        role="documentation",
        capabilities=["technical-writing", "neurodivergent-ux", "chunking"],
        config={"model": "claude-3-5-sonnet-20241022"}
    )
}

# --- API Endpoints ---

@app.get("/blueprints")
async def list_blueprints():
    """List available agent blueprints that can be spawned."""
    return BLUEPRINTS

@app.post("/agents/spawn")
async def spawn_agent(blueprint_id: str, count: int = 1):
    """Spawn one or more agents from a blueprint."""
    if blueprint_id not in BLUEPRINTS:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    
    blueprint = BLUEPRINTS[blueprint_id]
    spawned = []
    
    for _ in range(count):
        # In a real implementation, this would trigger a Docker/K8s job
        # For now, we mock the registry entry
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        instance = AgentInstance(
            id=agent_id,
            profile=blueprint,
            status="initializing",
            port=8000 + len(REGISTRY) + 10, # Mock port assignment
            created_at=datetime.datetime.now().isoformat(),
            health_url=f"http://localhost:{8000 + len(REGISTRY) + 10}/health"
        )
        REGISTRY[agent_id] = instance
        spawned.append(instance)
        
    return {"status": "success", "spawned": spawned}

@app.get("/agents")
async def list_agents():
    """List all running agents and their status."""
    return list(REGISTRY.values())

@app.post("/agents/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """Gracefully stop a running agent."""
    if agent_id not in REGISTRY:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    # Mock shutdown logic
    REGISTRY[agent_id].status = "stopped"
    return {"status": "success", "agent_id": agent_id, "state": "stopped"}

@app.get("/health")
async def health_check():
    return {"status": "factory_online", "active_agents": len(REGISTRY)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
