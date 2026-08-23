# agents/mission-director/models.py
"""
Plan schema for mission-director Phase 1.

RequestedAction/Constraints/PlanRequest/PlanResponse/canonical_hash are a
file copy of agents/fleet-controller/models.py, byte-for-byte on the
shared types -- no cross-agent package imports in this repo (see
docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md §2).
Keep these two files' shared types in sync by hand if fleet-controller's
schema ever changes.
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
    capability: Optional[str] = None


def canonical_hash(plan: PlanRequest) -> str:
    """sha256 over canonical (sorted-key, whitespace-free) JSON. Identical
    convention to fleet-controller/models.py's canonical_hash -- kept
    dependency-free (stdlib only) so both copies stay trivially
    comparable."""
    canonical = json.dumps(plan.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


# ---- Mission Director additions (Phase 1 + Phase 2) ----


class ImpactView(BaseModel):
    """Advisory only -- never validated as fact, never fed back into
    Safety Shepherd's policy. See
    docs/superpowers/specs/2026-08-24-fleet-dependency-graph-design.md."""

    profile: str
    upstream: list[str] = Field(default_factory=list)
    downstream_already_running: list[str] = Field(default_factory=list)
    available: bool = True
    reason: Optional[str] = None


class MissionProposal(BaseModel):
    schema_version: Literal[1]
    mission_id: str
    goal: str
    truth_snapshot_ref: Optional[str] = None
    rationale: Optional[str] = None
    plan: Optional[PlanRequest] = None
    plan_response: Optional[PlanResponse] = None
    impact: list[ImpactView] = Field(default_factory=list)
    status: Literal[
        "proposed",
        "previewed",
        "approved",
        "rejected",
        "preview_unavailable",
        "rejected_malformed",
    ]
    superseded_from: Optional[str] = None


class ReviewDecision(BaseModel):
    decision: Literal["approve", "reject"]
