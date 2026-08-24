"""
Mission Director Phase 1 -- human-facing surface.

Both routes here are the ONLY sanctioned way to reach mission-director's
propose/review flow: they reuse deps.get_current_active_user literally,
unmodified, which is what makes "human-submitted only, no self-triggering"
a structural fact rather than a documented convention -- no agent identity
in this repo can authenticate as a user. mission-director itself
(agents/mission-director/) holds no auth of its own; its /v1/plan route is
reachable only inside the docker network, mirroring fleet-controller's own
zero-auth /v1/plans/preview precedent. See
docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md and
docs/superpowers/plans/2026-08-21-mission-director-phase1-plan.md's
"Deviations from the spec" section for why the routes live here instead
of inside the mission-director container as the spec originally sketched.
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Literal, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.db.session import get_db
from app.models import models
from app.models.governance import GovernanceLedger
from app.services import mission_store

router = APIRouter()

# The only three statuses /v1/plan's create_plan route ever actually sets
# (agents/mission-director/main.py) -- anything else (or a missing/wrong-typed
# "status") means the response is untrusted, spoofed, or from a buggy build,
# and must be treated exactly like the existing malformed-response fallback.
_VALID_PLAN_STATUSES = {"previewed", "preview_unavailable", "rejected_malformed"}


def _mission_director_url() -> str:
    return (os.getenv("MISSION_DIRECTOR_URL") or "http://mission-director:8080").rstrip("/")


class ProposeRequest(BaseModel):
    goal: str


class ReviewRequest(BaseModel):
    decision: Literal["approve", "reject"]
    # Only required to approve a mission whose recorded Safety Shepherd
    # verdict is ESCALATE -- forces a deliberate, audited override instead
    # of a silent one-click downgrade to ALLOW. Ignored for reject and for
    # ALLOW/missing verdicts.
    escalation_reason: Optional[str] = None


def _safety_decision(plan_response: Optional[dict[str, Any]]) -> Optional[str]:
    if not isinstance(plan_response, dict):
        return None
    safety = plan_response.get("safety")
    if not isinstance(safety, dict):
        return None
    return safety.get("decision")


def _serialize(row) -> dict[str, Any]:
    return {
        "mission_id": row.mission_id,
        "status": row.status,
        "goal": row.goal,
        "truth_snapshot_ref": row.truth_snapshot_ref,
        "plan": row.plan,
        "plan_response": row.plan_response,
        "impact": row.impact or [],
        "superseded_from": row.superseded_from,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.post("/propose", status_code=200)
async def propose_mission(
    body: ProposeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    mission_id = f"mission_{uuid.uuid4().hex[:12]}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            resp = await http_client.post(
                f"{_mission_director_url()}/v1/plan",
                json={"mission_id": mission_id, "goal": body.goal},
            )
        resp.raise_for_status()
        proposal = resp.json()
        if not isinstance(proposal, dict) or "status" not in proposal or "mission_id" not in proposal or "goal" not in proposal:
            raise ValueError("malformed response from mission-director: missing required fields")
        if proposal.get("status") not in _VALID_PLAN_STATUSES:
            raise ValueError("malformed response from mission-director: unrecognized status")
        plan_response = proposal.get("plan_response")
        if plan_response is not None:
            if not isinstance(plan_response, dict) or plan_response.get("execution", {}).get("performed") is not False:
                raise ValueError("malformed response from mission-director: execution.performed not False")
    except Exception:
        proposal = {
            "schema_version": 1,
            "mission_id": mission_id,
            "goal": body.goal,
            "truth_snapshot_ref": None,
            "rationale": None,
            "plan": None,
            "plan_response": None,
            "impact": [],
            "status": "preview_unavailable",
            "superseded_from": None,
        }

    # Always persist and return the LOCALLY-generated mission_id, never the
    # value echoed back by mission-director -- a buggy or spoofed response
    # could otherwise overwrite it and collide with a different real mission.
    row = mission_store.create(
        db,
        mission_id=mission_id,
        status=proposal["status"],
        goal=proposal["goal"],
        truth_snapshot_ref=proposal.get("truth_snapshot_ref"),
        plan=proposal.get("plan"),
        plan_response=proposal.get("plan_response"),
        impact=proposal.get("impact"),
        superseded_from=proposal.get("superseded_from"),
    )
    return _serialize(row)


@router.post("/{mission_id}/review", status_code=200)
def review_mission(
    mission_id: str,
    body: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    row = mission_store.get_by_id(db, mission_id)
    if row is None:
        raise HTTPException(status_code=404, detail="mission not found")
    if row.status != "previewed":
        raise HTTPException(
            status_code=409,
            detail=f"mission status is {row.status!r}, must be 'previewed' to review",
        )

    safety_decision = _safety_decision(row.plan_response)
    if body.decision == "approve":
        if safety_decision == "BLOCK":
            raise HTTPException(
                status_code=409,
                detail="mission cannot be approved: Safety Shepherd verdict is BLOCK",
            )
        if safety_decision == "ESCALATE" and not (body.escalation_reason or "").strip():
            raise HTTPException(
                status_code=422,
                detail="mission cannot be approved: Safety Shepherd verdict is ESCALATE, "
                "an escalation_reason is required to override it",
            )

    new_status = "approved" if body.decision == "approve" else "rejected"
    updated = mission_store.update_status(db, mission_id, new_status)

    ledger_payload: dict[str, Any] = {"mission_id": mission_id, "decision": body.decision}
    if safety_decision == "ESCALATE" and body.escalation_reason:
        ledger_payload["escalation_reason"] = body.escalation_reason
    ledger_row = GovernanceLedger(
        user_id=str(current_user.id),
        action="mission.review",
        tool_used=None,
        payload=ledger_payload,
        decision=new_status,
        agent_name="mission-director",
        approved_by=str(current_user.id),
    )
    db.add(ledger_row)
    db.commit()

    return _serialize(updated)
