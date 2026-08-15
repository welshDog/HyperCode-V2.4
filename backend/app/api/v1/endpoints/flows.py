"""HyperFlow control plane — start, inspect, stream, and resume mission graphs (P0-1).

Routes (mounted under ``/api/v1/flows`` in ``app.api.api``):
    GET   /flows                     — list available flow definitions
    POST  /flows/runs                — start a run from a named flow (auth)
    GET   /flows/runs/{id}           — current run status (from Postgres)
    GET   /flows/runs/{id}/events    — SSE stream of node transitions
    POST  /flows/runs/{id}/resume    — satisfy a human_approval_gate (auth)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents.hyperflow.goal_matcher import match_goal
from app.agents.hyperflow.registry import available_flows, get_flow
from app.agents.hyperflow_runner import (
    cache_redis_url,
    get_runner,
    run_cache_key,
    run_channel,
    start_flow_run,
)
from app.api import deps
from app.db.session import get_db
from app.models.hyperflow import HyperFlowRun

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("")
async def list_flows() -> Any:
    flows = available_flows()
    return [
        {
            "name": fd.name,
            "version": fd.version,
            "entry": fd.entry,
            "nodes": [{"id": n.id, "type": n.type.value} for n in fd.nodes],
        }
        for fd in flows.values()
    ]


@router.post("/runs")
async def create_run(
    payload: dict,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    name = payload.get("flow")
    description = payload.get("description")

    if description is not None and not isinstance(description, str):
        raise HTTPException(status_code=422, detail="'description' must be a string")

    if not name and not description:
        raise HTTPException(status_code=422, detail="'flow' or 'description' is required")

    match_score: float | None = None
    if not name:
        result = match_goal(description, available_flows())
        if result.flow_name is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "no_confident_flow_match",
                    "candidates": [
                        {"flow": c.flow, "score": c.score, "intent": c.intent}
                        for c in result.candidates
                    ],
                },
            )
        name = result.flow_name
        match_score = result.score

    fd = get_flow(name)
    if fd is None:
        raise HTTPException(status_code=404, detail=f"Unknown flow '{name}'")

    run_id = str(uuid.uuid4())
    await start_flow_run(fd, run_id, user_id=getattr(current_user, "id", None))
    response: dict[str, Any] = {"run_id": run_id, "flow": fd.name, "status": "running"}
    if match_score is not None:
        response["matched_flow"] = fd.name
        response["match_score"] = match_score
    return response


def _serialize_run(run: HyperFlowRun) -> dict[str, Any]:
    return {
        "run_id": run.id,
        "flow": run.flow_name,
        "version": run.flow_version,
        "status": run.status,
        "current_node": run.current_node,
        "history": (run.state or {}).get("history", []),
        "error": (run.state or {}).get("error"),
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


@router.get("/active")
def list_active_runs(limit: int = 10, db: Session = Depends(get_db)) -> Any:
    """Active HyperFlow runs (running or awaiting approval), most-recent first.

    Backs the Mission Graph dashboard panel (P0-3).
    """
    limit = max(1, min(50, limit))
    runs = (
        db.query(HyperFlowRun)
        .filter(HyperFlowRun.status.in_(["running", "awaiting_approval"]))
        .order_by(HyperFlowRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"count": len(runs), "runs": [_serialize_run(r) for r in runs]}


@router.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)) -> Any:
    run = db.get(HyperFlowRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _serialize_run(run)


@router.post("/runs/{run_id}/resume")
async def resume_run(
    run_id: str,
    payload: dict,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    runner = get_runner(run_id)
    if runner is None:
        raise HTTPException(
            status_code=409,
            detail="Run is not awaiting approval in this worker (or already finished)",
        )
    approved = bool(payload.get("approved", True))
    runner.resume(approved)
    return {"run_id": run_id, "approved": approved}


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str, request: Request):
    """SSE stream of node transitions for a run.

    Seeds with the cached snapshot (Redis DB 1), then live via pub/sub.
    """
    async def event_generator():
        r = await aioredis.from_url(cache_redis_url(), decode_responses=True)
        pubsub = r.pubsub()
        try:
            snapshot = await r.get(run_cache_key(run_id))
            if snapshot:
                yield f"data: {snapshot}\n\n"

            await pubsub.subscribe(run_channel(run_id))
            async for message in pubsub.listen():
                if await request.is_disconnected():
                    break
                if message.get("type") != "message":
                    continue
                yield f"data: {message['data']}\n\n"
        except Exception:
            logger.exception("hyperflow SSE stream error for run %s", run_id)
        finally:
            await pubsub.unsubscribe(run_channel(run_id))
            await pubsub.close()
            await r.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
