"""
HyperCode V2.0 — WorkerAgent Container Entrypoint
==================================================
Exposes the WorkerAgent over HTTP. Because task handlers are Python
callables and can't travel over a network, this entrypoint ships a
built-in handler registry — named operations that can be invoked by
name via the API.

Built-in handlers:
  ping        — health-check round-trip (always succeeds)
  echo        — returns the payload unchanged
  http_check  — HTTP GET to a URL, returns status code
  count       — counts to N and returns the final value
  sleep       — waits N seconds (load/timeout testing)

Port  : 8093 (configurable via AGENT_PORT env)
Health: GET /health
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

import httpx
import uvicorn
from fastapi import HTTPException
from pydantic import BaseModel

from src.agents.hyper_agents import AgentArchetype
from src.agents.hyper_agents.worker import Task, TaskPriority, TaskResult, WorkerAgent

# ── Config ────────────────────────────────────────────────────────────────────
AGENT_NAME = os.getenv("AGENT_NAME", "task-worker-01")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8093"))
CREW_URL = os.getenv("CREW_ORCHESTRATOR_URL", "http://crew-orchestrator:8081")
HYPERFOCUS_MODE = os.getenv("HYPERFOCUS_MODE", "false").lower() == "true"


# ── Built-in handler registry ─────────────────────────────────────────────────

async def _handler_ping(**_kwargs: Any) -> dict[str, Any]:
    return {"pong": True, "agent": AGENT_NAME}


async def _handler_echo(**kwargs: Any) -> dict[str, Any]:
    return {"echo": kwargs.get("data", {})}


async def _handler_http_check(**kwargs: Any) -> dict[str, Any]:
    url = kwargs.get("url", "http://localhost:8093/health")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
    return {"url": url, "status_code": resp.status_code, "ok": resp.is_success}


async def _handler_count(**kwargs: Any) -> dict[str, Any]:
    n = int(kwargs.get("n", 10))
    total = sum(range(n + 1))
    return {"n": n, "total": total}


async def _handler_sleep(**kwargs: Any) -> dict[str, Any]:
    seconds = float(kwargs.get("seconds", 1.0))
    await asyncio.sleep(seconds)
    return {"slept_seconds": seconds}


HANDLER_REGISTRY: dict[str, Any] = {
    "ping": _handler_ping,
    "echo": _handler_echo,
    "http_check": _handler_http_check,
    "count": _handler_count,
    "sleep": _handler_sleep,
}


# ── Concrete agent implementation ─────────────────────────────────────────────

class HyperWorkerAgent(WorkerAgent):
    """Deployed WorkerAgent — resolves task type to built-in handler and executes."""

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        task_type = task.get("type", "ping")
        handler = HANDLER_REGISTRY.get(task_type)
        if not handler:
            return {
                "status": "error",
                "message": f"Unknown task type '{task_type}'. Available: {sorted(HANDLER_REGISTRY)}",
            }
        payload = task.get("payload", {})
        work = Task(
            name=task_type,
            handler=handler,
            kwargs=payload,
            priority=TaskPriority[task.get("priority", "NORMAL").upper()],
            timeout=float(task.get("timeout", 30.0)),
            description=task.get("description", f"Execute: {task_type}"),
        )
        result = await self.execute_task(work)
        return {
            "task_id": result.task_id,
            "task_name": result.task_name,
            "success": result.success,
            "result": result.result,
            "error": result.error,
            "duration_ms": round(result.duration_ms, 2),
            "retries_used": result.retries_used,
            "summary": result.summary,
        }


# ── Instantiate ───────────────────────────────────────────────────────────────

agent = HyperWorkerAgent(
    name=AGENT_NAME,
    archetype=AgentArchetype.WORKER,
    port=AGENT_PORT,
    hyperfocus_mode=HYPERFOCUS_MODE,
)
app = agent.app


# ── Request models ────────────────────────────────────────────────────────────

class TaskRequest(BaseModel):
    type: str
    payload: dict[str, Any] = {}
    priority: str = "NORMAL"
    timeout: float = 30.0
    description: Optional[str] = None
    max_retries: int = 3


class EnqueueRequest(BaseModel):
    type: str
    payload: dict[str, Any] = {}
    priority: str = "NORMAL"
    timeout: float = 30.0
    description: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/execute")
async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """General-purpose task execution gateway."""
    return await agent.execute(task)


@app.post("/tasks/run")
async def run_task(req: TaskRequest) -> dict[str, Any]:
    """Submit a task and execute it immediately. Blocks until complete."""
    handler = HANDLER_REGISTRY.get(req.type)
    if not handler:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown task type '{req.type}'. Available: {sorted(HANDLER_REGISTRY)}"
        )
    try:
        priority = TaskPriority[req.priority.upper()]
    except KeyError:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown priority '{req.priority}'. Use: LOW, NORMAL, HIGH, HYPERFOCUS"
        )
    task = Task(
        name=req.type,
        handler=handler,
        kwargs=req.payload,
        priority=priority,
        timeout=req.timeout,
        description=req.description or f"Execute: {req.type}",
        max_retries=req.max_retries,
    )
    result = await agent.execute_task(task)
    return {
        "task_id": result.task_id,
        "success": result.success,
        "result": result.result,
        "error": result.error,
        "duration_ms": round(result.duration_ms, 2),
        "retries_used": result.retries_used,
        "summary": result.summary,
    }


@app.post("/tasks/enqueue", status_code=202)
async def enqueue_task(req: EnqueueRequest) -> dict[str, Any]:
    """Add a task to the priority queue. Returns immediately."""
    handler = HANDLER_REGISTRY.get(req.type)
    if not handler:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown task type '{req.type}'. Available: {sorted(HANDLER_REGISTRY)}"
        )
    try:
        priority = TaskPriority[req.priority.upper()]
    except KeyError:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown priority '{req.priority}'. Use: LOW, NORMAL, HIGH, HYPERFOCUS"
        )
    task = Task(
        name=req.type,
        handler=handler,
        kwargs=req.payload,
        priority=priority,
        timeout=req.timeout,
        description=req.description or f"Queued: {req.type}",
    )
    task_id = agent.enqueue(task)
    return {"task_id": task_id, "status": "queued", "queue_size": agent._task_queue.qsize()}


@app.post("/tasks/queue/run")
async def drain_queue() -> dict[str, Any]:
    """Process all queued tasks in priority order. Blocks until queue is empty."""
    results = await agent.run_queue()
    return {
        "processed": len(results),
        "succeeded": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "results": [
            {"task_id": r.task_id, "success": r.success, "summary": r.summary}
            for r in results
        ],
    }


@app.get("/tasks/handlers")
async def list_handlers() -> dict[str, Any]:
    """List all built-in task types available to this worker."""
    return {"handlers": sorted(HANDLER_REGISTRY.keys())}


@app.get("/handlers")
async def list_handlers_alias() -> dict[str, Any]:
    """Alias for /tasks/handlers — convenient shortcut."""
    return {"handlers": sorted(HANDLER_REGISTRY.keys())}


@app.get("/tasks/history")
async def task_history() -> dict[str, Any]:
    """Return the last N completed task results."""
    return {
        "history": [
            {
                "task_id": r.task_id,
                "task_name": r.task_name,
                "success": r.success,
                "duration_ms": round(r.duration_ms, 2),
                "summary": r.summary,
            }
            for r in agent._task_history[-50:]  # last 50
        ],
        "total_executed": agent._total_tasks_executed,
    }


@app.get("/stats")
async def stats() -> dict[str, Any]:
    """Current worker statistics."""
    return agent.stats


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup() -> None:
    await agent.initialize()
    agent.register_with_crew(crew_url=CREW_URL)


@app.on_event("shutdown")
async def shutdown() -> None:
    agent.shutdown()


# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=AGENT_PORT, log_level="info")
