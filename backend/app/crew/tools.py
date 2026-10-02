"""Local HyperFlow tools for ``hypercode.crew`` (Day 2): propose the plan, then seal it.

Nothing here builds, mutates or contacts another service. ``crew_plan`` is deterministic;
``crew_seal`` re-verifies the human approval and writes one Governance Ledger row (fail-soft).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.broski_operator.recover_tools import _last_data, _last_result
from app.crew.plan import CrewStartArgs, build_crew_plan, crew_plan_hash
from app.db.session import SessionLocal
from app.models.governance import GovernanceLedger

logger = logging.getLogger(__name__)

_PLAN_NODE = "plan"
_GATE_NODE = "approve"
_SUMMARY_GOAL = 100


class CrewSealError(RuntimeError):
    """A sealing precondition failed. Messages are short and contain no untrusted text."""


def _no_proposal(note: str) -> dict[str, Any]:
    return {
        "ok": False, "has_proposal": False, "proposal": None, "notes": [note],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


async def crew_plan(params: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Build the plan for the goal stored with the run. Fails closed without a valid goal."""
    run_id = str((ctx or {}).get("run_id", ""))
    raw = (ctx or {}).get("arguments")
    try:
        args = CrewStartArgs.model_validate(raw if isinstance(raw, dict) else {})
    except Exception:
        return _no_proposal("no valid goal stored with this run")
    plan = build_crew_plan(args.goal, run_id)
    return {
        "ok": True,
        "has_proposal": True,
        "proposal": {
            "plan": plan,
            "plan_hash": crew_plan_hash(plan),
            "summary": f"crew run: {args.goal[:_SUMMARY_GOAL]}",
        },
        "notes": [],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def _write_ledger(entry: dict[str, Any]) -> bool:
    try:
        db = SessionLocal()
        try:
            db.add(
                GovernanceLedger(
                    user_id="broski-operator",
                    action="crew_plan_approved",
                    tool_used="hypercode.crew",
                    payload=entry["payload"],
                    decision="approved",
                    agent_name="broski-operator",
                    approved_by=entry["approved_by"],
                )
            )
            db.commit()
            return True
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            raise
        finally:
            db.close()
    except Exception:
        logger.warning("crew seal: governance ledger insert failed", exc_info=True)
        return False


async def crew_seal(params: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Verify the approval is for exactly this plan, then record it. Executes nothing."""
    history = (ctx or {}).get("history", [])
    run_id = str((ctx or {}).get("run_id", ""))
    proposed = _last_data(history, _PLAN_NODE) or {}
    proposal = proposed.get("proposal")
    if not isinstance(proposal, dict) or not isinstance(proposal.get("plan"), dict):
        raise CrewSealError("no plan to seal")
    plan = proposal["plan"]
    claimed = proposal.get("plan_hash")
    if not claimed or crew_plan_hash(plan) != claimed:
        raise CrewSealError("plan hash does not match the plan")
    gate = _last_result(history, _GATE_NODE)
    if not gate or gate.get("approved") is not True:
        raise CrewSealError("plan was not approved")
    approver = gate.get("by")
    if not approver:
        raise CrewSealError("no recorded approver")
    if gate.get("plan_hash") != claimed:
        raise CrewSealError("approval was not for this plan hash")
    ledger_ok = await asyncio.to_thread(
        _write_ledger,
        {
            "approved_by": str(approver),
            "payload": {"plan": plan, "plan_hash": claimed, "run_id": run_id, "performed": False},
        },
    )
    return {
        "ok": True,
        "sealed": True,
        "performed": False,
        "plan": plan,
        "plan_hash": claimed,
        "approved_by": str(approver),
        "ledger": bool(ledger_ok),
        "note": "plan approved and recorded; no build stage exists yet",
    }
