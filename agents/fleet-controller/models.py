"""
Plan schema for fleet-controller Phase 0.

kind is a closed Literal set on purpose: an unknown action kind is rejected
by pydantic at the wire level (422) before any handler code runs. There is
no "start"/"stop"/"build"/"exec"/"rm"/"prune"/"migrate"/"dispatch" kind in
this schema at all yet — those are later phases.
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
    """Body of `POST /v1/plans/preview`."""

    schema_version: Literal[1]
    mission_id: str
    requested_actions: list[RequestedAction]
    constraints: Constraints = Field(default_factory=Constraints)
    capability: Optional[str] = None   # inbound governor token (Phase 2)


class SafetyView(BaseModel):
    """The Safety Shepherd verdict, as returned to the caller."""

    decision: str
    reason: str
    rule: Optional[str] = None
    category: Optional[str] = None
    shepherd_available: bool = True


class ExecutionView(BaseModel):
    """Always `performed=False` in Phase 0 — no code path can execute yet."""

    performed: bool = False
    would_execute: list[str] = Field(default_factory=list)


class CapabilityView(BaseModel):
    """Recorded (not enforced) breakdown of a capability's verify_or_none() result."""

    presented: bool
    valid: bool
    reason: str


class PlanResponse(BaseModel):
    """Response of `POST /v1/plans/preview`."""

    plan_id: str
    plan_hash: str
    mode: Literal["DRY_RUN"] = "DRY_RUN"
    safety: SafetyView
    execution: ExecutionView
    # The verified capability token itself (echoed back), or null — original
    # Phase 0 type, kept for mission-director's mirrored PlanResponse model
    # (agents/mission-director/models.py), which parses this response and
    # would break on a type change here.
    capability: Optional[str] = None
    # Phase 2: recorded, not enforced — full verify_or_none() breakdown.
    capability_check: Optional[CapabilityView] = None


def canonical_hash(plan: PlanRequest) -> str:
    """sha256 over canonical (sorted-key, whitespace-free) JSON.

    separators=(",", ":") matters: the json.dumps default inserts spaces,
    which would make the hash sensitive to formatting, not just content.
    Stable regardless of field order in the original request; changes the
    instant any field's value changes (proven by test, not just asserted).

    `capability` is excluded on purpose: a capability token is minted
    against a plan_hash computed BEFORE the token exists to attach to the
    plan, so the hash must identify the plan's mutation content only — never
    the token riding alongside it. Including it would make the hash
    self-referential (a token can never match a hash of a plan that already
    carries that same token).
    """
    canonical = json.dumps(
        plan.model_dump(mode="json", exclude={"capability"}), sort_keys=True, separators=(",", ":")
    )
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
