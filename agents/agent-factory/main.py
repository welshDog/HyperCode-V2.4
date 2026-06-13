"""Hyper Agent Factory — spawns and manages specialized AI agents.

Two modes, selected by SPAWN_MODE:
  - "mock"   (default): in-memory registry only — used by unit tests and dry runs.
  - "docker": really starts/stops the matching compose-built containers through
              the scoped docker socket proxies (read via docker-socket-proxy,
              write via docker-socket-proxy-healer — CONTAINERS+POST only).

The factory does NOT create containers from scratch; it wakes the profile-gated
agents that `docker compose --profile agents build` already produced. That keeps
it inside the socket-proxy permission model (no IMAGES/BUILD needed).
"""

import datetime
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-factory")

SPAWN_MODE = os.getenv("SPAWN_MODE", "mock").strip().lower()
DOCKER_READ_HOST = os.getenv("DOCKER_READ_HOST", "http://docker-socket-proxy:2375").rstrip("/")
DOCKER_WRITE_HOST = os.getenv("DOCKER_WRITE_HOST", "http://docker-socket-proxy-healer:2375").rstrip("/")
DOCKER_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Agent Factory initialized (mode={SPAWN_MODE})")
    yield
    logger.info("Agent Factory shutting down")


app = FastAPI(
    title="Hyper Agent Factory",
    description="Creates and manages specialized AI agents for HyperCode",
    version="1.0.0",
    lifespan=lifespan,
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
    container: Optional[str] = None


REGISTRY: Dict[str, AgentInstance] = {}

# blueprint_id -> (profile, compose container name, agent port)
BLUEPRINTS: Dict[str, AgentProfile] = {
    "frontend-specialist": AgentProfile(
        name="Frontend Specialist",
        role="frontend",
        capabilities=["react", "tailwind", "vite"],
        config={"model": "claude-sonnet-4-6", "container": "frontend-specialist", "port": "8012"},
    ),
    "backend-specialist": AgentProfile(
        name="Backend Specialist",
        role="backend",
        capabilities=["python", "fastapi", "postgres"],
        config={"model": "claude-sonnet-4-6", "container": "backend-specialist", "port": "8003"},
    ),
    "database-architect": AgentProfile(
        name="Database Architect",
        role="database",
        capabilities=["postgres", "alembic", "schema-design"],
        config={"model": "claude-sonnet-4-6", "container": "database-architect", "port": "8004"},
    ),
    "qa-engineer": AgentProfile(
        name="QA Engineer",
        role="qa",
        capabilities=["pytest", "playwright", "test-plans"],
        config={"model": "claude-sonnet-4-6", "container": "qa-engineer", "port": "8005"},
    ),
    "devops-engineer": AgentProfile(
        name="DevOps Engineer",
        role="devops",
        capabilities=["docker", "ci-cd", "prometheus"],
        config={"model": "claude-sonnet-4-6", "container": "devops-engineer", "port": "8006"},
    ),
    "coder-agent": AgentProfile(
        name="Coder Agent",
        role="coder",
        capabilities=["python", "refactoring", "code-review"],
        config={"model": "claude-sonnet-4-6", "container": "coder-agent", "port": "8090"},
    ),
    "tips-tricks-writer": AgentProfile(
        name="Tips & Tricks Writer",
        role="documentation",
        capabilities=["technical-writing", "neurodivergent-ux", "chunking"],
        config={"model": "claude-sonnet-4-6", "container": "tips-tricks-writer", "port": "8009"},
    ),
}


def _blueprint_port(profile: AgentProfile, fallback: int) -> int:
    try:
        return int(profile.config.get("port", ""))
    except (TypeError, ValueError):
        return fallback


async def _docker_container_state(container: str) -> Optional[dict]:
    """Inspect a container via the read-only proxy. None if it doesn't exist."""
    try:
        async with httpx.AsyncClient(timeout=DOCKER_TIMEOUT) as client:
            r = await client.get(f"{DOCKER_READ_HOST}/containers/{container}/json")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Docker read proxy unreachable: {e}")


async def _docker_post(container: str, action: str) -> None:
    """Start/stop/restart a container via the write-enabled proxy."""
    try:
        async with httpx.AsyncClient(timeout=DOCKER_TIMEOUT) as client:
            r = await client.post(f"{DOCKER_WRITE_HOST}/containers/{container}/{action}")
        # 204 = done, 304 = already in desired state
        if r.status_code not in (204, 304):
            raise HTTPException(
                status_code=502,
                detail=f"Docker {action} on {container} failed: HTTP {r.status_code} {r.text[:200]}",
            )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Docker write proxy unreachable: {e}")


@app.get("/blueprints")
async def list_blueprints():
    """List available agent blueprints that can be spawned."""
    return BLUEPRINTS


@app.post("/agents/spawn")
async def spawn_agent(blueprint_id: str, count: int = 1):
    """Spawn one or more agents from a blueprint.

    docker mode: starts the matching compose container (count is capped at 1 —
    container names are unique). mock mode: registry entry only.
    """
    if blueprint_id not in BLUEPRINTS:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    blueprint = BLUEPRINTS[blueprint_id]
    spawned: List[AgentInstance] = []

    if SPAWN_MODE == "docker":
        container = blueprint.config.get("container", blueprint_id)
        state = await _docker_container_state(container)
        if state is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Container '{container}' does not exist. Build it first: "
                    f"docker compose --profile agents up -d --no-start {container}"
                ),
            )
        await _docker_post(container, "start")
        port = _blueprint_port(blueprint, 8000)
        instance = AgentInstance(
            id=f"agent-{uuid.uuid4().hex[:8]}",
            profile=blueprint,
            status="initializing",
            port=port,
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            health_url=f"http://{container}:{port}/health",
            container=container,
        )
        REGISTRY[instance.id] = instance
        spawned.append(instance)
        logger.info(f"Started container {container} for blueprint {blueprint_id}")
        return {"status": "success", "spawned": spawned}

    # mock mode (default — used by tests)
    for _ in range(count):
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        port = 8000 + len(REGISTRY) + 10
        instance = AgentInstance(
            id=agent_id,
            profile=blueprint,
            status="initializing",
            port=port,
            created_at=datetime.datetime.now().isoformat(),
            health_url=f"http://localhost:{port}/health",
        )
        REGISTRY[agent_id] = instance
        spawned.append(instance)

    return {"status": "success", "spawned": spawned}


@app.get("/agents")
async def list_agents():
    """List all known agents; in docker mode, refresh live container state."""
    if SPAWN_MODE == "docker":
        for instance in REGISTRY.values():
            if not instance.container or instance.status == "stopped":
                continue
            try:
                state = await _docker_container_state(instance.container)
            except HTTPException:
                instance.status = "error"
                continue
            if state is None:
                instance.status = "error"
                continue
            running = state.get("State", {}).get("Running", False)
            health = state.get("State", {}).get("Health", {}).get("Status")
            if not running:
                instance.status = "stopped"
            elif health == "healthy" or health is None:
                instance.status = "running"
            elif health == "starting":
                instance.status = "initializing"
            else:
                instance.status = "error"
    return list(REGISTRY.values())


@app.post("/agents/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """Gracefully stop a running agent."""
    if agent_id not in REGISTRY:
        raise HTTPException(status_code=404, detail="Agent not found")

    instance = REGISTRY[agent_id]
    if SPAWN_MODE == "docker" and instance.container:
        await _docker_post(instance.container, "stop")
        logger.info(f"Stopped container {instance.container}")

    instance.status = "stopped"
    return {"status": "success", "agent_id": agent_id, "state": "stopped"}


@app.get("/health")
async def health_check():
    return {"status": "factory_online", "active_agents": len(REGISTRY)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 9000)))
