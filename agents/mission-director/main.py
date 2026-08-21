# agents/mission-director/main.py
"""
mission-director -- Phase 1.

POST /v1/plan turns a goal into a previewed (or terminally-failed)
MissionProposal. Unauthenticated by design -- same trust model
fleet-controller's own /v1/plans/preview uses (containment via capability
absence, not access control); the human-auth boundary lives in
backend/app/api/v1/endpoints/missions.py (Task 4), the only sanctioned
caller. See
docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md
and this plan's "Deviations from the spec" section.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from pydantic import BaseModel

import fleet_client
import ledger_client
import plan_generator
from local_validator import LocalValidationError, validate
from models import Constraints, MissionProposal, PlanRequest
from truth_snapshot import get_snapshot_ref


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    plan_generator.init()
    ledger_client.init()
    try:
        yield
    finally:
        await plan_generator.aclose()
        await fleet_client.aclose()
        await ledger_client.aclose()


app = FastAPI(title="mission-director", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "agent": "mission-director"}


class PlanGoalRequest(BaseModel):
    mission_id: str
    goal: str


def _terminal(
    mission_id: str,
    goal: str,
    truth_snapshot_ref: str | None,
    status: str,
    plan: PlanRequest | None = None,
    rationale: str | None = None,
) -> MissionProposal:
    proposal = MissionProposal(
        schema_version=1,
        mission_id=mission_id,
        goal=goal,
        truth_snapshot_ref=truth_snapshot_ref,
        rationale=rationale,
        plan=plan,
        plan_response=None,
        status=status,
    )
    ledger_client.record_proposal(proposal)  # fire-and-forget, not awaited
    return proposal


@app.post("/v1/plan", response_model=MissionProposal)
async def create_plan(request: PlanGoalRequest) -> MissionProposal:
    mission_id = request.mission_id
    goal = request.goal

    try:
        snapshot_ref = get_snapshot_ref()
    except Exception:
        return _terminal(mission_id, goal, None, "preview_unavailable")

    try:
        llm_output = await plan_generator.generate(goal)
    except plan_generator.PlanGenerationError:
        return _terminal(mission_id, goal, snapshot_ref, "preview_unavailable")
    except plan_generator.PlanMalformedError:
        return _terminal(mission_id, goal, snapshot_ref, "rejected_malformed")

    plan_request = PlanRequest(
        schema_version=1,
        mission_id=mission_id,
        requested_actions=llm_output.requested_actions,
        constraints=Constraints(),
    )

    try:
        validate(plan_request, snapshot_ref)
    except LocalValidationError:
        return _terminal(
            mission_id, goal, snapshot_ref, "rejected_malformed", plan_request, llm_output.rationale
        )

    try:
        plan_response = await fleet_client.preview(plan_request)
    except fleet_client.FleetControllerUnavailable:
        return _terminal(
            mission_id, goal, snapshot_ref, "preview_unavailable", plan_request, llm_output.rationale
        )

    proposal = MissionProposal(
        schema_version=1,
        mission_id=mission_id,
        goal=goal,
        truth_snapshot_ref=snapshot_ref,
        rationale=llm_output.rationale,
        plan=plan_request,
        plan_response=plan_response,
        status="previewed",
    )
    ledger_client.record_proposal(proposal)
    return proposal
