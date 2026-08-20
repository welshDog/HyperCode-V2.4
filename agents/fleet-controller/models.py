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
    action_id: str
    kind: Literal["compose_profile.preview", "crew.workflow.preview"]
    profile: Optional[str] = None


class Constraints(BaseModel):
    max_services: int = 25
    allow_profiles: list[str] = Field(default_factory=list)
    deny_profiles: list[str] = Field(default_factory=list)


class PlanRequest(BaseModel):
    schema_version: Literal[1]
    mission_id: str
    requested_actions: list[RequestedAction]
    constraints: Constraints = Field(default_factory=Constraints)


class SafetyView(BaseModel):
    decision: str
    reason: str
    rule: Optional[str] = None
    category: Optional[str] = None
    shepherd_available: bool = True


class ExecutionView(BaseModel):
    performed: bool = False
    would_execute: list[str] = Field(default_factory=list)


class PlanResponse(BaseModel):
    plan_id: str
    plan_hash: str
    mode: Literal["DRY_RUN"] = "DRY_RUN"
    safety: SafetyView
    execution: ExecutionView
    # Reserved for Phase 2 (capability tokens) — never set in Phase 0.
    capability: Optional[str] = None


def canonical_hash(plan: PlanRequest) -> str:
    """sha256 over canonical (sorted-key, whitespace-free) JSON.

    separators=(",", ":") matters: the json.dumps default inserts spaces,
    which would make the hash sensitive to formatting, not just content.
    Stable regardless of field order in the original request; changes the
    instant any field's value changes (proven by test, not just asserted).
    """
    canonical = json.dumps(plan.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
