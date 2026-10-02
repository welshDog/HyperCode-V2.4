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
from app.crew.dispatch import parse_verdict, scan_forbidden
from app.crew.evidence import build_bundle, evidence_for
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
                # A failed rollback must not hide the original insert error, which is re-raised below.
                logger.debug("crew seal: ledger rollback failed", exc_info=True)
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


_SEAL_NODE = "seal"
_BUILD_NODE = "build"
_VERIFY_NODE = "verify"


def _str_of(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    return value if isinstance(value, str) else ""


def _dict_of(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


async def crew_guard(params: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Guardian: decide ALLOW/BLOCK on what the crew produced. Deterministic, executes nothing.

    Fails closed — a missing stage, an unreadable verdict or any tripwire hit is a BLOCK, and a
    BLOCK is reported (``allowed: false``), not raised, so the human sees exactly why.
    """
    history = (ctx or {}).get("history", [])
    run_id = str((ctx or {}).get("run_id", ""))
    sealed = _last_data(history, _SEAL_NODE) or {}
    build = _last_data(history, _BUILD_NODE) or {}
    verify = _last_data(history, _VERIFY_NODE) or {}
    plan = _dict_of(sealed, "plan")
    plan_hash = _str_of(sealed, "plan_hash")
    build_text = _str_of(build, "summary")
    verify_text = _str_of(verify, "summary")

    hits = scan_forbidden(build_text)
    verdict = parse_verdict(verify_text)
    checks = [
        _check("plan_sealed", sealed.get("sealed") is True and bool(plan_hash), "approved plan is sealed"),
        _check("plan_non_mutating", plan.get("risk_hint") != "mutation", "plan risk hint is not 'mutation'"),
        _check("build_present", bool(build_text.strip()), "builder returned a proposal"),
        _check("build_clean", not hits, "no forbidden command in the proposal" if not hits
               else "proposal contains: " + ", ".join(hits)),
        _check("verify_present", bool(verify_text.strip()), "verifier returned a review"),
        _check("verifier_verdict", verdict == "PASS", f"verifier verdict: {verdict}"),
    ]
    failed = [c["name"] for c in checks if not c["passed"]]
    allowed = not failed

    items = []
    if build_text:
        items.append(evidence_for("diff", run_id, _BUILD_NODE, build_text))
    if verify_text:
        items.append(evidence_for("log", run_id, _VERIFY_NODE, verify_text))
    return {
        "ok": True,
        "allowed": allowed,
        "verdict": "ALLOW" if allowed else "BLOCK",
        "failed_checks": failed,
        "checks": checks,
        "evidence_bundle": build_bundle(run_id, plan_hash, items),
        "performed": False,
    }


def _settle_sync(run_id: str, history: list[dict[str, Any]]) -> dict[str, Any]:
    from app.crew.quests import settle_run
    from app.services.broski_service import seed_achievements

    db = SessionLocal()
    try:
        seed_achievements(db)  # idempotent: makes sure the crew achievements exist before they can unlock
        result = settle_run(db, run_id, history)
        return {
            "status": result.status, "xp": result.xp, "coins": result.coins, "reason": result.reason,
            "already_settled": result.already_settled, "achievements": result.achievements,
        }
    except Exception:
        try:
            db.rollback()
        except Exception:
            logger.debug("crew settle: rollback failed", exc_info=True)
        raise
    finally:
        db.close()


async def crew_settle(params: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Quest Settler: reward the approving human for a guard-ALLOWed run, once. Executes nothing.

    Runs as a flow node inside core — there is no endpoint, MCP tool or agent path to it. A reward
    problem must never undo finished work, so a failure is reported (``status: error``) rather than raised;
    re-running is safe because ``run_id:quest_id`` is UNIQUE.
    """
    history = (ctx or {}).get("history", [])
    run_id = str((ctx or {}).get("run_id", ""))
    try:
        out = await asyncio.to_thread(_settle_sync, run_id, history)
    except Exception:
        logger.warning("crew settle failed for run %s", run_id, exc_info=True)
        # ok stays True: a failed reward must never turn finished, guard-approved work into a failed run.
        return {"ok": True, "performed": False, "status": "error", "xp": 0, "coins": 0,
                "reason": "settlement failed; safe to retry", "achievements": []}
    return {"ok": True, "performed": False, **out}
