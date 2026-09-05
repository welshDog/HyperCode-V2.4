"""
fleet-controller — Phase 0.

Accepts a typed infrastructure-change proposal, validates it, asks Safety
Shepherd, and returns a preview. execution.performed is False in every
response this service can ever produce: there is no Docker client, no
crew-orchestrator dispatch credential, and no code path anywhere in this
file that can set it to True. See
docs/superpowers/specs/2026-08-20-fleet-controller-phase0-design.md
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException

import capability_verify
import ledger_client
import safety_client
from models import (
    CapabilityView,
    ExecutionView,
    PlanRequest,
    PlanResponse,
    SafetyView,
    canonical_hash,
)
from plan_validator import PlanValidationError, validate_plan


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start the ledger client on startup; close both clients on shutdown."""
    ledger_client.init()
    try:
        yield
    finally:
        await safety_client.aclose()
        await ledger_client.aclose()


app = FastAPI(title="fleet-controller", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    """Liveness only — no readiness/dependency checks."""
    return {"status": "healthy", "agent": "fleet-controller"}


@app.post("/v1/plans/preview", response_model=PlanResponse)
async def preview_plan(plan: PlanRequest) -> PlanResponse:
    """Validate the plan, get a Safety Shepherd verdict, offline-verify any
    presented capability, and return a preview. `execution.performed` is
    always False — this endpoint can never actually execute anything.
    """
    try:
        validate_plan(plan)
    except PlanValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.detail) from exc

    plan_hash = canonical_hash(plan)
    plan_id = f"plan_{uuid.uuid4().hex[:12]}"
    result = await safety_client.check_infrastructure_mutation(plan, plan_hash)

    cap_action = plan.requested_actions[0].kind
    cap_target = plan.requested_actions[0].profile
    cap_ok, cap_reason = capability_verify.verify_or_none(
        plan.capability, plan_hash=plan_hash, action=cap_action, target=cap_target, mode="DRY_RUN"
    )
    capability_view = CapabilityView(presented=plan.capability is not None, valid=cap_ok, reason=cap_reason)

    response = PlanResponse(
        plan_id=plan_id,
        plan_hash=plan_hash,
        safety=SafetyView(
            decision=result.decision,
            reason=result.reason,
            rule=result.rule,
            category=result.category,
            shepherd_available=result.shepherd_available,
        ),
        execution=ExecutionView(performed=False, would_execute=[]),
        capability=plan.capability if capability_view.valid else None,
        capability_check=capability_view,
    )
    ledger_client.record_preview(plan, plan_id, plan_hash, result, capability_view)  # fire-and-forget, not awaited
    return response
