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
from typing import AsyncIterator, Any

import time

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import fleet_client
import impact_snapshot
import ledger_client
import plan_generator
from local_validator import LocalValidationError, validate
from models import Constraints, ImpactView, MissionProposal, PlanRequest
from truth_snapshot import get_snapshot_ref
import redis.asyncio as redis
import os
import json

from app.api import deps
from app.db.session import get_db
from app.models import models
from app.models.governance import GovernanceLedger
from app.services import mission_store


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
        {a.profile for a in llm_output.requested_actions if a.profile is not None}
    )
    impact = impact_snapshot.get_impact(profiles)

    try:
        validate(plan_request, snapshot_ref)
    except LocalValidationError:
        return _terminal(
            mission_id, goal, snapshot_ref, "rejected_malformed",
            plan_request, llm_output.rationale, impact,
        )

    try:
        plan_response = await fleet_client.preview(plan_request)
    except fleet_client.FleetControllerUnavailable:
        return _terminal(
            mission_id, goal, snapshot_ref, "preview_unavailable",
            plan_request, llm_output.rationale, impact,
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


@app.post("/v1/missions/{mission_id}/execute")
async def execute_mission(
    mission_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Execute an approved mission by publishing to the execution queue.
    Only missions with status 'approved' can be executed.
    """
    # Get the mission from the store
    row = mission_store.get_by_id(db, mission_id)
    if row is None:
        raise HTTPException(status_code=404, detail="mission not found")
    if row.status != "approved":
        raise HTTPException(
            status_code=409,
            detail=f"mission status is {row.status!r}, must be 'approved' to execute",
        )

    # Publish execution request to Redis
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    execution_channel = os.getenv("MISSION_EXECUTION_CHANNEL", "mission_executions")

    execution_payload = {
        "mission_id": mission_id,
        "goal": row.goal,
        "plan": row.plan,
        "requested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time())),
        "requested_by": str(current_user.id)
    }

    try:
        redis_client = redis.from_url(redis_url)
        await redis_client.publish(execution_channel, json.dumps(execution_payload))
        await redis_client.close()
    except Exception:
        # Fail softly - execution will be picked up by the executor service if Redis is available
        pass

    # Update mission status to executing
    updated = mission_store.update_status(db, mission_id, "executing")

    # Record execution attempt in ledger
    ledger_row = GovernanceLedger(
        user_id=str(current_user.id),
        action="mission.execute",
        payload={"mission_id": mission_id},
        decision="executing",
        agent_name="mission-director",
        approved_by=str(current_user.id),
    )
    db.add(ledger_row)
    db.commit()

    return _serialize(updated)
