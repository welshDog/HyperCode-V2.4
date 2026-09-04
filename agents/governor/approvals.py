"""Human approval records + the two-person rule.

Phase 2 has no dashboard — an approval is created by an authenticated call
carrying an approver_id. The governor enforces the count rule; Phase 3
adds the UI that calls this.
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

import redis_state

DANGEROUS_CLASSES = {"INFRASTRUCTURE_MUTATION", "DESTRUCTIVE"}


def _key(mission_id: str) -> str:
    return f"gov:appr:{mission_id}"


async def record(*, mission_id: str, plan_hash: str, approver_id: str, decision: str, reason: str) -> str:
    approval_id = f"appr_{uuid.uuid4().hex}"
    entry = {
        "approval_id": approval_id,
        "plan_hash": plan_hash,
        "approver_id": approver_id,
        "decision": decision,
        "reason": reason,
    }
    await redis_state.get_redis().rpush(_key(mission_id), json.dumps(entry))
    return approval_id


async def satisfied(*, mission_id: str, plan_hash: str, proposer_id: str, risk_class: str) -> Optional[str]:
    raw = await redis_state.get_redis().lrange(_key(mission_id), 0, -1)
    approvers = {
        e["approver_id"]
        for e in (json.loads(x) for x in raw)
        if e.get("decision") == "approved"
        and e.get("plan_hash") == plan_hash
        and e.get("approver_id") != proposer_id
    }
    need = 2 if risk_class in DANGEROUS_CLASSES else 1
    return f"appr-set:{mission_id}" if len(approvers) >= need else None
