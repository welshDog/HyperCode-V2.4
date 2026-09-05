"""
Plan schema for governor (copied from fleet-controller/models.py —
file-copy convention, never cross-agent import; see plan_validator.py).

kind is a closed Literal set on purpose: an unknown action kind is rejected
by pydantic at the wire level (422) before any handler code runs.
"""
from __future__ import annotations

import hashlib
import json
from typing import Literal, Optional

from pydantic import BaseModel, Field


class RequestedAction(BaseModel):
    """One preview-only action a plan asks the fleet to evaluate."""

    action_id: str
    kind: Literal["compose_profile.preview", "crew.workflow.preview"]
    profile: Optional[str] = None


class Constraints(BaseModel):
    """Caps and allow/deny lists a plan must stay within."""

    max_services: int = 25
    allow_profiles: list[str] = Field(default_factory=list)
    deny_profiles: list[str] = Field(default_factory=list)


class PlanRequest(BaseModel):
    """A full plan submission: schema version, mission, actions, constraints."""

    schema_version: Literal[1]
    mission_id: str
    requested_actions: list[RequestedAction]
    constraints: Constraints = Field(default_factory=Constraints)


def canonical_hash(plan: PlanRequest) -> str:
    """sha256 over canonical (sorted-key, whitespace-free) JSON.

    separators=(",", ":") matters: the json.dumps default inserts spaces,
    which would make the hash sensitive to formatting, not just content.
    Stable regardless of field order in the original request; changes the
    instant any field's value changes (proven by test, not just asserted).
    """
    canonical = json.dumps(plan.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


class MintRequest(BaseModel):
    """Body of `POST /v1/capabilities/mint`."""

    plan: PlanRequest
    plan_hash: str
    mode: Literal["DRY_RUN", "LIVE"]
    action: str
    target: Optional[str] = None
    proposer_id: str = "mission-director"


class MintResponse(BaseModel):
    """Result of a mint attempt: the token (if minted) plus the Shepherd verdict."""

    capability: Optional[str] = None
    jti: Optional[str] = None
    verdict: dict
    minted: bool
    reason: str


class VerifyRequest(BaseModel):
    """Body of `POST /v1/capabilities/verify` — the caller's expected context.

    `burn` defaults to `False` (a repeatable read); only the executor
    should ever pass `True`, immediately before acting.
    """

    token: str
    expected_sub: str
    expected_plan_hash: str
    expected_action: str
    expected_target: Optional[str] = None
    expected_mode: str
    burn: bool = False


class RevokeRequest(BaseModel):
    """Body of `POST /v1/capabilities/revoke` — revoke by `jti` or whole `mission_id`."""

    jti: Optional[str] = None
    mission_id: Optional[str] = None
    reason: str


class ApprovalRequest(BaseModel):
    """Body of `POST /v1/approvals` — one human decision on a mission's plan."""

    mission_id: str
    plan_hash: str
    approver_id: str
    # CodeRabbit follow-up: plain str let a case typo ("Approved") through
    # with a 200 + approval_id, silently never counting toward
    # satisfied()'s exact "approved" match -- the caller believed the
    # approval was recorded when it could never satisfy the rule. Literal
    # turns that into an immediate 422 instead of a silent no-count.
    decision: Literal["approved", "rejected"]
    reason: str


class KillRequest(BaseModel):
    """Body of `POST /v1/kill` — a non-empty reason is mandatory."""

    reason: str = Field(min_length=1)
