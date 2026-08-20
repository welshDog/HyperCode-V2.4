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

import ledger_client
import safety_client
from models import ExecutionView, PlanRequest, PlanResponse, SafetyView, canonical_hash
from plan_validator import PlanValidationError, validate_plan


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    ledger_client.init()
    try:
        yield
    finally:
        await safety_client.aclose()
        await ledger_client.aclose()


app = FastAPI(title="fleet-controller", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "agent": "fleet-controller"}


@app.post("/v1/plans/preview", response_model=PlanResponse)
async def preview_plan(plan: PlanRequest) -> PlanResponse:
    try:
        validate_plan(plan)
    except PlanValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.detail) from exc

    plan_hash = canonical_hash(plan)
    plan_id = f"plan_{uuid.uuid4().hex[:12]}"
    result = await safety_client.check_infrastructure_mutation(plan, plan_hash)

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
    )
    ledger_client.record_preview(plan, plan_id, plan_hash, result)  # fire-and-forget, not awaited
    return response
