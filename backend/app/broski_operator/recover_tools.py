"""Local tools for `hypercode.recover` (Phase 2a): deterministic propose + verified seal.

Read-only: only GETs through the read-only Docker socket proxy and a read of the healer's
restart counter in Redis. The seal writes one Governance Ledger row (fail-soft) and nothing else.
Nothing here restarts anything.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import redis.asyncio as aioredis

from app.broski_operator import recover
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.governance import GovernanceLedger

logger = logging.getLogger(__name__)

_DOCKER_TIMEOUT = 8.0
_HEX_ID = re.compile(r"[0-9a-f]{12,64}")
_COOLDOWN_LIMIT = 3
_COOLDOWN_WINDOW = 300
_COOLDOWN_TIMEOUT_S = 2.0
_PROPOSE_NODE = "propose"
_GATE_NODE = "approve"


class RecoverSealError(RuntimeError):
    """A sealing precondition failed. Messages are short and contain no untrusted text."""


def _last_data(history: list[dict[str, Any]], node_id: str) -> Optional[dict[str, Any]]:
    for entry in reversed(history):
        if entry.get("node") == node_id and entry.get("status") == "completed":
            data = (entry.get("result") or {}).get("data")
            return data if isinstance(data, dict) else None
    return None


def _last_result(history: list[dict[str, Any]], node_id: str) -> Optional[dict[str, Any]]:
    for entry in reversed(history):
        if entry.get("node") == node_id and entry.get("status") == "completed":
            return entry.get("result") or {}
    return None


async def _fetch_summaries() -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(
            f"{settings.DOCKER_SOCKET_PROXY_URL}/containers/json", params={"all": "true"}
        )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []


async def _get_detail(cid: str) -> Optional[dict[str, Any]]:
    if not isinstance(cid, str) or not _HEX_ID.fullmatch(cid):
        return None  # never build a URL path from anything but a Docker hex id
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.DOCKER_SOCKET_PROXY_URL}/containers/{cid}/json")
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else None
    except Exception:
        return None


async def _cooldown(name: str) -> dict[str, Any]:
    """Informational read of the healer's restart counter (2b enforces the limit)."""
    info: dict[str, Any] = {"count": None, "limit": _COOLDOWN_LIMIT, "window_s": _COOLDOWN_WINDOW}
    try:
        r = aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
        try:
            raw = await r.get(f"healer:restarts:{name}")
        finally:
            await r.aclose()
        info["count"] = int(raw) if raw is not None else 0
    except Exception:
        pass
    return info


async def recover_propose(params: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    history = (ctx or {}).get("history", [])
    run_id = str((ctx or {}).get("run_id", ""))
    notes: list[str] = []
    inspect_data = _last_data(history, "inspect")
    if inspect_data:
        notes.extend(str(a) for a in list(inspect_data.get("attention") or [])[:10])
    try:
        summaries = await asyncio.wait_for(_fetch_summaries(), timeout=_DOCKER_TIMEOUT)
        candidates = await recover.gather_candidates(summaries, _get_detail)
    except Exception as exc:  # fail-soft: an unreachable proxy is a finding, not a crash
        return {
            "ok": False, "has_proposal": False, "proposal": None, "candidates": [],
            "not_eligible": [],
            "notes": notes + [f"docker proxy unreachable ({type(exc).__name__})"],
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    for cand in candidates[:5]:
        try:
            cand["cooldown"] = await asyncio.wait_for(_cooldown(cand["container"]), timeout=_COOLDOWN_TIMEOUT_S)
        except (asyncio.TimeoutError, Exception):
            cand["cooldown"] = {"count": None, "limit": _COOLDOWN_LIMIT, "window_s": _COOLDOWN_WINDOW}
    report = recover.build_report(candidates, run_id, notes)
    report["checked_at"] = datetime.now(timezone.utc).isoformat()
    return report


def _write_ledger(entry: dict[str, Any]) -> bool:
    db = SessionLocal()
    try:
        db.add(
            GovernanceLedger(
                user_id="broski-operator",
                action="recover_plan_approved",
                tool_used="hypercode.recover",
                payload=entry["payload"],
                decision="approved",
                agent_name="broski-operator",
                approved_by=entry["approved_by"],
            )
        )
        db.commit()
        return True
    except Exception:
        db.rollback()
        logger.warning("recover seal: governance ledger insert failed", exc_info=True)
        return False
    finally:
        db.close()


async def recover_seal(params: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    history = (ctx or {}).get("history", [])
    run_id = str((ctx or {}).get("run_id", ""))
    proposed = _last_data(history, _PROPOSE_NODE) or {}
    proposal = proposed.get("proposal")
    if not isinstance(proposal, dict) or not isinstance(proposal.get("plan"), dict):
        raise RecoverSealError("no proposal to seal")
    plan = proposal["plan"]
    claimed = proposal.get("plan_hash")
    if not claimed or recover.plan_hash(plan) != claimed:
        raise RecoverSealError("plan hash does not match the plan")
    gate = _last_result(history, _GATE_NODE)
    if not gate or gate.get("approved") is not True:
        raise RecoverSealError("plan was not approved")
    approver = gate.get("by")
    if not approver:
        raise RecoverSealError("no recorded approver")
    if gate.get("plan_hash") != claimed:
        raise RecoverSealError("approval was not for this plan hash")
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
        "note": "restart is NOT executed in Phase 2a; the governed executor (2b) consumes this plan",
    }
