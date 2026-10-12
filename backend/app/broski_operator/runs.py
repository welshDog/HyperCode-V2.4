"""DB helpers for operator-managed HyperFlow runs. Every function takes an explicit Session."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, NamedTuple, Optional

from sqlalchemy.orm import Session

from app.models.hyperflow import HyperFlowRun, HyperFlowRunStatus

OPEN_STATUSES = (
    HyperFlowRunStatus.RUNNING.value,
    HyperFlowRunStatus.AWAITING_APPROVAL.value,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class OpenRun(NamedTuple):
    run_id: str
    flow_name: str
    status: str
    history: list[dict[str, Any]]
    last_activity: Optional[datetime]  # updated_at, else created_at; may be tz-naive (SQLite)


def load_open_runs(db: Session) -> list[OpenRun]:
    """Every run that was live when we stopped, with its last-activity time."""
    rows = db.query(HyperFlowRun).filter(HyperFlowRun.status.in_(OPEN_STATUSES)).all()
    return [
        OpenRun(
            r.id,
            r.flow_name,
            r.status,
            list((r.state or {}).get("history", [])),
            r.updated_at or r.created_at,
        )
        for r in rows
    ]


def store_decision(
    db: Session,
    run: HyperFlowRun,
    *,
    approved: bool,
    by: str,
    node: Optional[str],
    plan_hash: Optional[str] = None,
) -> bool:
    """Persist an approval decision for the runner to pick up. False if one is already pending.

    ``node`` scopes the decision to the gate it answers so it can never approve a later gate.
    """
    state = dict(run.state or {})
    ctx = dict(state.get("context") or {})
    if "pending_decision" in ctx:
        return False
    decision = {"approved": approved, "by": by, "ts": _now(), "node": node}
    if plan_hash is not None:
        decision["plan_hash"] = plan_hash
    ctx["pending_decision"] = decision
    state["context"] = ctx
    run.state = state
    db.commit()
    return True


def finish_run_row(
    db: Session,
    run: HyperFlowRun,
    status: HyperFlowRunStatus,
    error: Optional[str],
) -> None:
    """Terminate a run directly in Postgres (used when no live runner owns it)."""
    state = dict(run.state or {})
    history = list(state.get("history", []))
    history.append(
        {
            "node": None,
            "type": "terminal",
            "status": status.value,
            "result": {"error": error} if error else {},
            "ts": _now(),
        }
    )
    state["history"] = history
    if error:
        state["error"] = error
    run.state = state
    run.status = status.value
    run.current_node = None
    run.completed_at = datetime.now(timezone.utc)
    db.commit()


def pause_info(run: HyperFlowRun) -> Optional[dict[str, Any]]:
    """The pause record stored with the run (who, when, and a snapshot of where it was), or None."""
    info = ((run.state or {}).get("context") or {}).get("paused")
    return info if isinstance(info, dict) else None


def set_paused(
    db: Session, run: HyperFlowRun, *, by: str, reason: str, snapshot: dict[str, Any]
) -> bool:
    """Durably mark the run paused. False if it already was (the first snapshot is kept)."""
    if pause_info(run) is not None:
        return False
    state = dict(run.state or {})
    ctx = dict(state.get("context") or {})
    ctx["paused"] = {"at": _now(), "by": by, "reason": reason, "snapshot": snapshot}
    state["context"] = ctx
    run.state = state
    db.commit()
    return True


def clear_paused(db: Session, run: HyperFlowRun) -> Optional[dict[str, Any]]:
    """Remove the pause record and return it (None if the run was not paused)."""
    old = pause_info(run)
    if old is None:
        return None
    state = dict(run.state or {})
    ctx = dict(state.get("context") or {})
    ctx.pop("paused", None)
    state["context"] = ctx
    run.state = state
    db.commit()
    return old
