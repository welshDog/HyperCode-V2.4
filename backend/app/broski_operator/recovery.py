"""Restart recovery for HyperFlow runs (spec §5.2).

``plan_recovery`` is pure. ``recover_runs`` applies the plans at core startup.
Loop counters are not persisted, so a recovered run's loop budget restarts at zero
and the originating user id is not restored (recovered runs dispatch without one).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional

from app.agents.hyperflow.registry import get_flow
from app.agents.hyperflow.schema import FlowDefinition, NodeType
from app.agents.hyperflow_runner import HyperFlowRunner, get_runner
from app.broski_operator.runs import OPEN_STATUSES, finish_run_row, load_open_runs
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
    else:  # a failed entry: retry/fallback was in flight — do not guess
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
            return
        if plan.action == "complete":
            finish_run_row(db, run, HyperFlowRunStatus.COMPLETED, None)
        else:
            finish_run_row(db, run, HyperFlowRunStatus.FAILED, plan.reason)
    finally:
        db.close()


def _load() -> list[tuple[str, str, str, list[dict[str, Any]]]]:
    db = SessionLocal()
    try:
        return load_open_runs(db)
    finally:
        db.close()


async def recover_runs() -> dict[str, int]:
    """Re-attach runs that were live when core last stopped. Returns counts per action."""
    counts = {"resume": 0, "complete": 0, "fail": 0, "skip": 0}
    for run_id, flow_name, status, history in await asyncio.to_thread(_load):
        if get_runner(run_id) is not None:
            continue
        flow = get_flow(flow_name)
        if flow is None:
            plan = RecoveryPlan("fail", reason=f"flow '{flow_name}' no longer exists")
        else:
            plan = plan_recovery(flow, status, history)
        counts[plan.action] += 1
        if plan.action == "resume":
            assert flow is not None and plan.node_id is not None
            runner = HyperFlowRunner(flow, run_id, history=history)
            await runner.start_at(plan.node_id)
        elif plan.action in ("complete", "fail"):
            await asyncio.to_thread(_finish_row, run_id, plan)
        logger.info("hyperflow recovery run=%s action=%s reason=%s", run_id, plan.action, plan.reason)
    return counts
