"""
HyperCode V2.0 — ArchitectAgent Container Entrypoint
=====================================================
Exposes the ArchitectAgent over HTTP with goal planning,
step management, and dependency resolution endpoints.

Ports : 8091 (configurable via AGENT_PORT env)
Health: GET /health
"""

from __future__ import annotations

import os
from typing import Any, List, Optional

import uvicorn
from fastapi import HTTPException
from pydantic import BaseModel

from src.agents.hyper_agents import AgentArchetype, AgentStatus
from src.agents.hyper_agents.architect import ArchitectAgent

# ── Config ────────────────────────────────────────────────────────────────────
AGENT_NAME = os.getenv("AGENT_NAME", "lead-architect-01")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8091"))
CREW_URL = os.getenv("CREW_ORCHESTRATOR_URL", "http://crew-orchestrator:8081")


# ── Concrete agent implementation ─────────────────────────────────────────────

class HyperArchitectAgent(ArchitectAgent):
    """Deployed ArchitectAgent — routes task dicts to planning methods."""

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "stats")

        if action == "create_goal":
            goal_id = self.create_goal(task["description"])
            return {"goal_id": goal_id, "status": "created", "message": f"Goal ready: {task['description']}"}

        if action == "add_step":
            step_id = self.add_step(
                task["goal_id"],
                task["description"],
                depends_on=task.get("depends_on"),
                assigned_to=task.get("assigned_to"),
            )
            return {"step_id": step_id, "status": "added"}

        if action == "complete_step":
            self.complete_step(task["goal_id"], task["step_id"])
            return {"status": "completed", "progress": self.goal_progress(task["goal_id"])}

        if action == "fail_step":
            self.fail_step(task["goal_id"], task["step_id"], error=task.get("error"))
            return {"status": "failed"}

        return {"status": "ok", "stats": self.stats}


# ── Instantiate ───────────────────────────────────────────────────────────────

agent = HyperArchitectAgent(name=AGENT_NAME, archetype=AgentArchetype.ARCHITECT, port=AGENT_PORT)
app = agent.app


# ── Request models ────────────────────────────────────────────────────────────

class GoalRequest(BaseModel):
    description: str


class StepRequest(BaseModel):
    description: str
    depends_on: Optional[List[str]] = None
    assigned_to: Optional[str] = None


class RegisterAgentRequest(BaseModel):
    agent_id: str
    role: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/execute")
async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """General-purpose task execution gateway."""
    return await agent.execute(task)


@app.post("/goals", status_code=201)
async def create_goal(req: GoalRequest) -> dict[str, Any]:
    """Create a new high-level goal."""
    goal_id = agent.create_goal(req.description)
    return {"goal_id": goal_id, "status": "created"}


@app.get("/goals/{goal_id}")
async def get_goal(goal_id: str) -> dict[str, Any]:
    """Retrieve full goal detail including step statuses."""
    goal = agent.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal '{goal_id}' not found.")
    return {
        "goal_id": goal.goal_id,
        "title": goal.title,
        "status": goal.status.value,
        "progress": round(goal.progress, 4),
        "steps": [
            {
                "step_id": s.step_id,
                "description": s.description,
                "status": s.status.value,
                "assigned_to": s.assigned_to,
                "depends_on": sorted(s.depends_on),
            }
            for s in goal.steps
        ],
    }


@app.post("/goals/{goal_id}/steps", status_code=201)
async def add_step(goal_id: str, req: StepRequest) -> dict[str, Any]:
    """Add an execution step to an existing goal."""
    try:
        step_id = agent.add_step(
            goal_id, req.description,
            depends_on=req.depends_on,
            assigned_to=req.assigned_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"step_id": step_id, "status": "added"}


@app.get("/goals/{goal_id}/steps/ready")
async def get_ready_steps(goal_id: str) -> dict[str, Any]:
    """Return steps that are unblocked and ready to execute."""
    steps = agent.get_ready_steps(goal_id)
    return {
        "goal_id": goal_id,
        "ready_steps": [
            {"step_id": s.step_id, "description": s.description, "assigned_to": s.assigned_to}
            for s in steps
        ],
    }


@app.post("/goals/{goal_id}/steps/{step_id}/complete")
async def complete_step(goal_id: str, step_id: str) -> dict[str, Any]:
    """Mark a step as completed and recalculate goal progress."""
    agent.complete_step(goal_id, step_id)
    return {"status": "completed", "progress": round(agent.goal_progress(goal_id), 4)}


@app.post("/goals/{goal_id}/steps/{step_id}/fail")
async def fail_step(goal_id: str, step_id: str, error: Optional[str] = None) -> dict[str, Any]:
    """Mark a step as failed. Goal will also be marked FAILED."""
    agent.fail_step(goal_id, step_id, error=error)
    return {"status": "failed", "goal_id": goal_id, "step_id": step_id}


@app.post("/agents/register")
async def register_agent(req: RegisterAgentRequest) -> dict[str, Any]:
    """Register a sub-agent in the architect's registry."""
    agent.register_sub_agent(req.agent_id, req.role)
    return {"status": "registered", "agent_id": req.agent_id}


@app.get("/goals")
async def list_goals() -> dict[str, Any]:
    """List all goals with their current status and progress."""
    goals = []
    for goal_id, goal in agent._goals.items():
        goals.append({
            "goal_id": goal.goal_id,
            "title": goal.title,
            "status": goal.status.value,
            "progress": round(goal.progress, 4),
            "step_count": len(goal.steps),
        })
    return {"goals": goals, "total": len(goals)}


@app.get("/agents")
async def list_registered_agents() -> dict[str, Any]:
    """List all agents registered with the architect."""
    return {
        "agents": [
            {"agent_id": aid, "role": role}
            for aid, role in agent.registered_agents.items()
        ]
    }


@app.get("/stats")
async def stats() -> dict[str, Any]:
    """Current architect statistics."""
    return agent.stats


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup() -> None:
    agent.set_ready()
    agent.register_with_crew(crew_url=CREW_URL)


@app.on_event("shutdown")
async def shutdown() -> None:
    agent.shutdown()


# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=AGENT_PORT, log_level="info")
