# agents/mission-director/main.py
"""Mission Director Phase 1 preview-only service.

The human-authenticated proposal/review surface lives in HyperCode core at
``/api/v1/missions``. This internal service converts a supplied goal into a
truth-grounded proposal, asks fleet-controller for a DRY_RUN preview, and
returns the result. It deliberately exposes no execute or queue-publish route.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI
from pydantic import BaseModel

import fleet_client
import impact_snapshot
import ledger_client
import plan_generator
from local_validator import LocalValidationError, validate
from models import Constraints, ImpactView, MissionProposal, PlanRequest
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


def _terminal(
    mission_id: str,
    goal: str,
    truth_snapshot_ref: str | None,
    status: str,
    plan: PlanRequest | None = None,
    rationale: str | None = None,
    impact: list[ImpactView] | None = None,
) -> MissionProposal:
    proposal = MissionProposal(
        schema_version=1,
        mission_id=mission_id,
        goal=goal,
        truth_snapshot_ref=truth_snapshot_ref,
        rationale=rationale,
        plan=plan,
        plan_response=None,
        impact=impact or [],
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

    profiles = sorted(
        {action.profile for action in llm_output.requested_actions if action.profile is not None}
    )
    impact = impact_snapshot.get_impact(profiles)

    try:
        validate(plan_request, snapshot_ref)
    except LocalValidationError:
        return _terminal(
            mission_id,
            goal,
            snapshot_ref,
            "rejected_malformed",
            plan_request,
            llm_output.rationale,
            impact,
        )

    try:
        plan_response = await fleet_client.preview(plan_request)
    except fleet_client.FleetControllerUnavailable:
        return _terminal(
            mission_id,
            goal,
            snapshot_ref,
            "preview_unavailable",
            plan_request,
            llm_output.rationale,
            impact,
        )

    proposal = MissionProposal(
        schema_version=1,
        mission_id=mission_id,
        goal=goal,
        truth_snapshot_ref=snapshot_ref,
        rationale=llm_output.rationale,
        plan=plan_request,
        plan_response=plan_response,
        impact=impact,
        status="previewed",
    )
    ledger_client.record_proposal(proposal)
    return proposal
