"""Human approval records + the two-person rule.

Phase 2 has no dashboard — an approval is created by an authenticated call
carrying an approver_id. The governor enforces the count rule; Phase 3
adds the UI that calls this.

KNOWN PHASE 2 LIMITATION (CodeRabbit follow-up, deliberately not patched
here): /v1/approvals is gated by a single shared OPERATOR_KEY, not a
per-person credential. satisfied()'s "2 distinct approvers" count is
therefore a distinction between approver_id STRINGS in the request body,
not between authenticated IDENTITIES — anyone holding the one shared key
can submit two calls with two different approver_id values and satisfy
the DANGEROUS_CLASSES two-person rule alone. Binding approver_id to "the
authenticated caller" instead would not fix this: under one shared secret
every caller IS the same authenticated identity, so that change would only
make the rule permanently unsatisfiable. A real fix needs distinct
per-approver credentials, which is exactly what Phase 3's dashboard is for.
Until then, this endpoint's two-person guarantee is an audit-trail
distinction, not an authentication one — treat it accordingly for any
INFRASTRUCTURE_MUTATION/DESTRUCTIVE mint this gates.
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
