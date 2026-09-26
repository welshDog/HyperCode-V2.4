"""BROski operator API — MCP-Tasks-shaped facade over HyperFlow runs (spec 2026-09-26).

Routes (mounted under ``/api/v1/operator``):
    POST /tasks               — start an allow-listed tool, returns a task handle at once
    GET  /tasks/{id}          — poll status / progress / result
    POST /tasks/{id}/input    — approve or reject a parked approval gate (humans only)
    POST /tasks/{id}/cancel   — cancel a task

Auth: ``X-Agent-Key`` (agents) or a Bearer JWT (humans). Agents can start, read and cancel
tasks but can NEVER submit an approval: the model must not approve its own risky action.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.hyperflow.registry import get_flow
from app.agents.hyperflow_runner import get_runner, start_flow_run
from app.api import deps
from app.broski_operator.catalog import TOOL_FLOWS, tool_for_flow
from app.broski_operator.runs import finish_run_row, store_decision
from app.broski_operator.status import (
    TERMINAL_RUN_STATUSES,
    build_result,
    poll_interval_ms,
    progress_percent,
    to_task_status,
)
from app.db.session import get_db
from app.middleware.agent_auth import get_agent_from_key
from app.models.hyperflow import HyperFlowRun, HyperFlowRunStatus

router = APIRouter()

_MAX_REASON = 200


async def operator_principal(
    agent: Optional[dict] = Depends(get_agent_from_key),
    user: Any = Depends(deps.get_optional_current_user),
) -> dict[str, Any]:
    """Agent key or human JWT. Neither → 401."""
    if agent is not None:
        return {"kind": "agent", "name": agent["agent_name"], "user_id": None, "is_superuser": False}
    if user is not None:
        if not getattr(user, "is_active", True):
            raise HTTPException(status_code=403, detail="Inactive user")
        return {
            "kind": "user",
            "name": getattr(user, "email", "user"),
            "user_id": user.id,
            "is_superuser": bool(getattr(user, "is_superuser", False)),
        }
    raise HTTPException(
        status_code=401, detail="Authentication required (Bearer token or X-Agent-Key)"
    )


def _parked_gate(run: HyperFlowRun) -> Optional[str]:
    """Node id of the human gate the run is parked at RIGHT NOW, else None.

    None also covers a Safety Shepherd escalation wait (status awaiting_approval but
    no gate history entry), which must never be approvable through this API.
    """
    history = (run.state or {}).get("history", [])
    if not history:
        return None
    last = history[-1]
    if (
        last.get("status") == "awaiting_approval"
        and last.get("type") == "human_approval_gate"
        and last.get("node")
        and last.get("node") == run.current_node
    ):
        return last["node"]
    return None


def _approval_request(run: HyperFlowRun) -> dict[str, Any]:
    gate = _parked_gate(run)
    if gate is None:
        return {
            "kind": "safety_escalation",
            "question": "Waiting on a Safety Shepherd escalation decision; not approvable via the operator API",
            "options": [],
        }
    history = (run.state or {}).get("history", [])
    prompt = "Approve?"
    for entry in reversed(history):
        if entry.get("status") == "awaiting_approval":
            prompt = (entry.get("result") or {}).get("prompt", prompt)
            break
    return {
        "kind": "approval",
        "approval": {
            "node": gate,
            "question": prompt,
            "options": ["approve", "reject"],
        },
    }


def _serialize(run: HyperFlowRun) -> dict[str, Any]:
    state = run.state or {}
    history = state.get("history", [])
    flow = get_flow(run.flow_name)
    task_status = to_task_status(run.status)
    when = run.updated_at or run.created_at
    body: dict[str, Any] = {
        "taskId": run.id,
        "tool": tool_for_flow(run.flow_name),
        "status": task_status,
        "progress": progress_percent(len(flow.nodes) if flow else 0, history, run.status),
        "pollInterval": poll_interval_ms(task_status),
        "updatedAt": when.isoformat() if when else None,
        "result": None,
        "error": None,
        "inputRequests": None,
    }
    if task_status == "completed":
        body["result"] = build_result(history)
    elif task_status in ("failed", "cancelled"):
        body["error"] = state.get("error")
    elif task_status == "input_required":
        body["inputRequests"] = _approval_request(run)
    return body


def _get_run(db: Session, task_id: str) -> HyperFlowRun:
    run = db.get(HyperFlowRun, task_id)
    if run is None or tool_for_flow(run.flow_name) is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return run


@router.post("/tasks")
async def start_task(
    payload: dict,
    principal: dict = Depends(operator_principal),
) -> Any:
    tool = payload.get("tool")
    arguments = payload.get("arguments", {})
    if not isinstance(tool, str) or not tool:
        raise HTTPException(status_code=422, detail="'tool' must be a non-empty string")
    if not isinstance(arguments, dict):
        raise HTTPException(status_code=422, detail="'arguments' must be an object")
    if arguments:
        raise HTTPException(status_code=422, detail="This tool does not accept arguments yet")
    flow_name = TOOL_FLOWS.get(tool)
    if flow_name is None:
        raise HTTPException(
            status_code=404, detail={"error": "unknown_tool", "tools": sorted(TOOL_FLOWS)}
        )
    flow = get_flow(flow_name)
    if flow is None:
        raise HTTPException(status_code=500, detail=f"Flow '{flow_name}' is not installed")
    run_id = str(uuid.uuid4())
    await start_flow_run(flow, run_id, user_id=principal["user_id"])
    return {
        "taskId": run_id,
        "tool": tool,
        "status": "working",
        "pollInterval": poll_interval_ms("working"),
    }


@router.get("/tasks/{task_id}")
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    _principal: dict = Depends(operator_principal),
) -> Any:
    return _serialize(_get_run(db, task_id))


def _locked_run(db: Session, task_id: str) -> HyperFlowRun:
    run = (
        db.query(HyperFlowRun)
        .filter(HyperFlowRun.id == task_id)
        .with_for_update()
        .one_or_none()
    )
    if run is None or tool_for_flow(run.flow_name) is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="Task not found")
    return run


@router.post("/tasks/{task_id}/input")
async def submit_input(
    task_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    principal: dict = Depends(operator_principal),
) -> Any:
    if principal["kind"] != "user":
        raise HTTPException(
            status_code=403,
            detail="Approvals require an authenticated human user, not an agent key",
        )
    if not principal.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Approvals require a superuser")
    decision = payload.get("decision")
    if decision not in ("approve", "reject"):
        raise HTTPException(status_code=422, detail="'decision' must be 'approve' or 'reject'")
    wanted_node = payload.get("node")
    if wanted_node is not None and not isinstance(wanted_node, str):
        raise HTTPException(status_code=422, detail="'node' must be a string")
    run = _locked_run(db, task_id)
    gate = _parked_gate(run) if run.status == HyperFlowRunStatus.AWAITING_APPROVAL.value else None
    if gate is None:
        status = to_task_status(run.status)
        db.rollback()
        raise HTTPException(
            status_code=409, detail={"error": "not_awaiting_input", "status": status}
        )
    if wanted_node is not None and wanted_node != gate:
        db.rollback()
        raise HTTPException(status_code=409, detail={"error": "gate_mismatch", "expected": gate})
    approved = decision == "approve"
    if not store_decision(db, run, approved=approved, by=principal["name"], node=gate):
        db.rollback()
        raise HTTPException(status_code=409, detail={"error": "decision_already_pending"})
    runner = get_runner(task_id)
    if runner is not None and getattr(runner, "parked_gate", None) == gate:
        runner.resume(approved)
    return {"taskId": task_id, "accepted": True, "decision": decision}


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    principal: dict = Depends(operator_principal),
) -> Any:
    reason = payload.get("reason") or "cancelled by operator"
    if not isinstance(reason, str) or len(reason) > _MAX_REASON:
        raise HTTPException(status_code=422, detail=f"'reason' must be a string <= {_MAX_REASON} chars")
    run = _get_run(db, task_id)
    if run.status in TERMINAL_RUN_STATUSES:
        raise HTTPException(
            status_code=409,
            detail={"error": "already_terminal", "status": to_task_status(run.status)},
        )
    label = f"{reason} (by {principal['name']})"
    runner = get_runner(task_id)
    if runner is not None and await runner.cancel(label):
        db.refresh(run)
    else:
        # The runner may have finished meanwhile: re-read under lock before overwriting.
        run = _locked_run(db, task_id)
        db.refresh(run)
        if run.status in TERMINAL_RUN_STATUSES:
            status = to_task_status(run.status)
            db.rollback()
            raise HTTPException(
                status_code=409, detail={"error": "already_terminal", "status": status}
            )
        finish_run_row(db, run, HyperFlowRunStatus.CANCELLED, label)
        db.refresh(run)
    return {"taskId": task_id, "status": to_task_status(run.status), "reason": label}
