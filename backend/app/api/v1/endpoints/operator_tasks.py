"""BROski operator API — MCP-Tasks-shaped facade over HyperFlow runs (spec 2026-09-26).

Routes (mounted under ``/api/v1/operator``):
    POST /tasks               — start an allow-listed tool, returns a task handle at once
                                (optional ``idempotency_key``: a repeat returns the same task)
    GET  /tasks/{id}          — poll status / progress / result
    POST /tasks/{id}/input    — approve or reject a parked approval gate (humans only)
    POST /tasks/{id}/cancel   — cancel a task

Auth: ``X-Agent-Key`` (agents) or a Bearer JWT (humans). Agents can start, read and cancel
tasks but can NEVER submit an approval: the model must not approve its own risky action.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agents.hyperflow.registry import get_flow
from app.agents.hyperflow_runner import get_runner, start_flow_run
from app.api import deps
from app.broski_operator.catalog import TOOL_FLOWS, ArgumentError, tool_for_flow, validate_arguments
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
_IDEMPOTENCY_KEY = re.compile(r"[A-Za-z0-9._:-]{8,128}")
# Fixed namespace: the same caller + tool + key always maps to the same run id.
_IDEMPOTENCY_NS = uuid.uuid5(uuid.NAMESPACE_URL, "hypercode:operator:idempotency:v1")


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


def _gate_entry(run: HyperFlowRun) -> dict[str, Any]:
    """The awaiting_approval history entry for the gate the run is parked at (or {})."""
    history = (run.state or {}).get("history", [])
    return history[-1] if history and _parked_gate(run) is not None else {}


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
    entry_result = _gate_entry(run).get("result") or {}
    approval: dict[str, Any] = {
        "node": gate,
        "question": prompt,
        "options": ["approve", "reject"],
    }
    if entry_result.get("context") is not None:
        approval["context"] = entry_result["context"]
    if entry_result.get("plan_hash"):
        approval["plan_hash"] = entry_result["plan_hash"]
    return {"kind": "approval", "approval": approval}


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


def _arguments_hash(arguments: dict[str, Any]) -> str:
    canonical = json.dumps(arguments, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def _handle(run_id: str, tool: str, status: str, **extra: Any) -> dict[str, Any]:
    return {
        "taskId": run_id,
        "tool": tool,
        "status": status,
        "pollInterval": poll_interval_ms(status),
        **extra,
    }


def _deduplicated(db: Session, run_id: str, tool: str, args_hash: str) -> dict[str, Any]:
    """The run an earlier identical start created. Same key, different arguments → 409."""
    run = db.get(HyperFlowRun, run_id)
    if run is None:  # pragma: no cover — the insert conflict proves it exists
        raise HTTPException(status_code=409, detail={"error": "idempotency_conflict"})
    stored = ((run.state or {}).get("context") or {}).get("arguments_hash")
    if stored != args_hash:
        raise HTTPException(status_code=409, detail={"error": "idempotency_key_reused"})
    return _handle(run_id, tool, to_task_status(run.status), deduplicated=True)


@router.post("/tasks")
async def start_task(
    payload: dict,
    db: Session = Depends(get_db),
    principal: dict = Depends(operator_principal),
) -> Any:
    tool = payload.get("tool")
    arguments = payload.get("arguments", {})
    key = payload.get("idempotency_key")
    if not isinstance(tool, str) or not tool:
        raise HTTPException(status_code=422, detail="'tool' must be a non-empty string")
    if not isinstance(arguments, dict):
        raise HTTPException(status_code=422, detail="'arguments' must be an object")
    if key is not None and (not isinstance(key, str) or not _IDEMPOTENCY_KEY.fullmatch(key)):
        raise HTTPException(
            status_code=422,
            detail="'idempotency_key' must be 8-128 characters of letters, digits, . _ : -",
        )
    flow_name = TOOL_FLOWS.get(tool)
    if flow_name is None:
        raise HTTPException(
            status_code=404, detail={"error": "unknown_tool", "tools": sorted(TOOL_FLOWS)}
        )
    try:
        arguments = validate_arguments(tool, arguments)
    except ArgumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    flow = get_flow(flow_name)
    if flow is None:
        raise HTTPException(status_code=500, detail=f"Flow '{flow_name}' is not installed")

    if not arguments and key is None:
        run_id = str(uuid.uuid4())
        await start_flow_run(flow, run_id, user_id=principal["user_id"])
        return _handle(run_id, tool, "working")

    # Arguments and/or an idempotency key: create the run row FIRST. The primary key makes a
    # repeat (or a concurrent twin) collide here instead of starting the flow twice.
    caller = f"{principal['kind']}:{principal['user_id'] if principal['user_id'] is not None else principal['name']}"
    run_id = (
        str(uuid.uuid5(_IDEMPOTENCY_NS, f"{caller}|{tool}|{key}")) if key else str(uuid.uuid4())
    )
    args_hash = _arguments_hash(arguments)
    if db.get(HyperFlowRun, run_id) is not None:
        return _deduplicated(db, run_id, tool, args_hash)
    db.add(
        HyperFlowRun(
            id=run_id,
            flow_name=flow.name,
            flow_version=flow.version,
            status=HyperFlowRunStatus.RUNNING.value,
            current_node=flow.entry,
            state={
                "history": [],
                "context": {"arguments": arguments, "arguments_hash": args_hash},
            },
        )
    )
    try:
        db.commit()
    except IntegrityError:  # a concurrent twin won the insert
        db.rollback()
        return _deduplicated(db, run_id, tool, args_hash)
    try:
        await start_flow_run(flow, run_id, user_id=principal["user_id"])
    except Exception:
        row = db.get(HyperFlowRun, run_id)
        if row is not None:
            finish_run_row(db, row, HyperFlowRunStatus.FAILED, "could not start")
        raise
    return _handle(run_id, tool, "working")


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
    sent_hash = payload.get("plan_hash")
    if sent_hash is not None and not isinstance(sent_hash, str):
        raise HTTPException(status_code=422, detail="'plan_hash' must be a string")
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
    gate_hash = (_gate_entry(run).get("result") or {}).get("plan_hash")
    if approved and gate_hash:
        if sent_hash is None:
            db.rollback()
            raise HTTPException(status_code=422, detail={"error": "plan_hash_required"})
        if sent_hash != gate_hash:
            db.rollback()
            raise HTTPException(status_code=409, detail={"error": "plan_hash_mismatch"})
    verified_hash = sent_hash if (approved and gate_hash) else None
    if not store_decision(
        db, run, approved=approved, by=principal["name"], node=gate, plan_hash=verified_hash
    ):
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
