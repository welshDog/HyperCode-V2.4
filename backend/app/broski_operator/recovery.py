"""Restart recovery for HyperFlow runs (spec §5.2).

``plan_recovery`` is pure. ``recover_runs`` applies the plans at core startup.
Loop counters are not persisted, so a recovered run's loop budget restarts at zero
and the originating user id is not restored (recovered runs dispatch without one).
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Any, Optional

from app.agents.hyperflow.registry import get_flow
from app.agents.hyperflow.schema import FlowDefinition, NodeType
from app.agents.hyperflow_runner import HyperFlowRunner, get_runner
from app.broski_operator.runs import OPEN_STATUSES, OpenRun, finish_run_row, load_open_runs
from app.db.session import SessionLocal
from app.models.hyperflow import HyperFlowRun, HyperFlowRunStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecoveryPlan:
    action: str  # "resume" | "complete" | "fail" | "skip"
    node_id: Optional[str] = None
    reason: str = ""


def plan_recovery(flow: FlowDefinition, status: str, history: list[dict[str, Any]]) -> RecoveryPlan:
    """Decide what to do with a run that was live when core stopped."""
    if status not in OPEN_STATUSES:
        return RecoveryPlan("skip", reason=f"status={status}")

    last = history[-1] if history else None
    if last is None:
        next_id: Optional[str] = flow.entry
    elif last.get("status") == "awaiting_approval":
        return RecoveryPlan("resume", last["node"], "parked at approval gate")
    elif last.get("status") == "completed":
        node = flow.node(last["node"])
        success = bool((last.get("result") or {}).get("success", True))
        next_id = HyperFlowRunner(flow, "plan")._next_node(node, success, {})
        if next_id is None:
            return RecoveryPlan("complete", reason="last node was terminal")
    elif last.get("status") in ("safety_allow", "safety_skipped"):
        # The Safety Shepherd gate let this node through, then we stopped before it
        # recorded a result: that node was in flight.
        next_id = last["node"]
    else:  # a failed entry / safety_escalate / safety_block: do not guess
        return RecoveryPlan("fail", reason="interrupted by restart")

    node = flow.node(next_id)
    if node.type is NodeType.HUMAN_APPROVAL_GATE or node.idempotent:
        return RecoveryPlan("resume", next_id, "next node is safe to re-run")
    return RecoveryPlan(
        "fail", next_id, f"interrupted by restart: node '{next_id}' is not idempotent"
    )


def _finish_row(run_id: str, plan: RecoveryPlan) -> None:
    db = SessionLocal()
    try:
        run = db.get(HyperFlowRun, run_id)
        if run is None:
            logger.warning("hyperflow recovery run=%s vanished before it could be finished", run_id)
            return
        if plan.action == "complete":
            finish_run_row(db, run, HyperFlowRunStatus.COMPLETED, None)
        else:
            finish_run_row(db, run, HyperFlowRunStatus.FAILED, plan.reason)
    finally:
        db.close()


def _max_age_hours() -> float:
    try:
        return float(os.getenv("RECOVERY_MAX_AGE_HOURS", "24"))
    except ValueError:
        return 24.0


def _is_stale(last_activity: Optional[datetime], max_age_hours: float) -> bool:
    if last_activity is None:
        return False
    if last_activity.tzinfo is None:  # SQLite returns naive datetimes; they are UTC
        last_activity = last_activity.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last_activity > timedelta(hours=max_age_hours)


def _load() -> list[OpenRun]:
    db = SessionLocal()
    try:
        return load_open_runs(db)
    finally:
        db.close()


async def recover_runs() -> dict[str, int]:
    """Re-attach runs that were live when core last stopped. Returns counts per action."""
    counts = {"resume": 0, "complete": 0, "fail": 0, "skip": 0}
    max_age = _max_age_hours()
    for run_id, flow_name, status, history, last_activity in await asyncio.to_thread(_load):
        if get_runner(run_id) is not None:
            continue
        flow = get_flow(flow_name)
        try:
            if _is_stale(last_activity, max_age):
                plan = RecoveryPlan("fail", reason=f"stale at recovery (older than {max_age:g}h)")
            elif flow is None:
                plan = RecoveryPlan("fail", reason=f"flow '{flow_name}' no longer exists")
            else:
                plan = plan_recovery(flow, status, history)
            if plan.action == "resume":
                if flow is None or plan.node_id is None:
                    raise RuntimeError("resume plan without flow/node")
                runner = HyperFlowRunner(flow, run_id, history=history)
                await runner.start_at(plan.node_id)
            elif plan.action in ("complete", "fail"):
                await asyncio.to_thread(_finish_row, run_id, plan)
            counts[plan.action] += 1
            logger.info(
                "hyperflow recovery run=%s action=%s reason=%s", run_id, plan.action, plan.reason
            )
        except Exception as exc:  # one poisoned run must never block the others
            logger.exception("hyperflow recovery run=%s errored", run_id)
            plan = RecoveryPlan(
                "fail", reason=f"recovery error: {type(exc).__name__}: {str(exc)[:150]}"
            )
            try:
                await asyncio.to_thread(_finish_row, run_id, plan)
                counts["fail"] += 1
            except Exception:
                logger.exception("hyperflow recovery run=%s could not be marked failed", run_id)
    return counts
