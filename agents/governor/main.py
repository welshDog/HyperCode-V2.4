"""
governor — Phase 2. The governance-plane nucleus.

Mints signed, scope-bound capability tokens. Holds the kill-switch, the
Ed25519 signing key, the jti replay store, the system lease, and approval
records. Structurally inert: no Docker socket, no DOCKER_HOST, no
crew-orchestrator credential, no LLM/MCP client. See
docs/superpowers/specs/2026-09-04-autonomous-control-plane-north-star-design.md
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException

import capability
import ledger_client
import lease as lease_mod
import redis_state
import shepherd_client
import transitions
from approvals import satisfied as approvals_satisfied
from killswitch import is_killed
from models import MintRequest, MintResponse
from plan_validator import PlanValidationError, validate_plan


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    ledger_client.init()
    try:
        yield
    finally:
        await shepherd_client.aclose()
        await ledger_client.aclose()
        await redis_state.aclose()


app = FastAPI(title="governor", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "agent": "governor"}


@app.post("/v1/capabilities/mint", response_model=MintResponse)
async def mint_capability(req: MintRequest) -> MintResponse:
    try:
        validate_plan(req.plan)
    except PlanValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.detail) from exc

    verdict = await shepherd_client.evaluate_plan(
        mission_id=req.plan.mission_id, plan_hash=req.plan_hash, action=req.action, target=req.target
    )
    verdict_dict = {
        "decision": verdict.decision,
        "reason": verdict.reason,
        "risk_class": verdict.risk_class,
        "policy_version": verdict.policy_version,
        "shepherd_available": verdict.shepherd_available,
    }
    ledger_client.record("verdict.issued", verdict.decision, {
        "mission_id": req.plan.mission_id, "plan_hash": req.plan_hash,
        "verdict_id": verdict.event_id, "risk_class": verdict.risk_class,
        "policy_version": verdict.policy_version,
    })

    killed = await is_killed()
    outcome = transitions.resolve(
        mode=req.mode, decision=verdict.decision, kill_switch=killed, risk_class=verdict.risk_class
    )

    approval_id = None
    if outcome.needs_approval:
        approval_id = await approvals_satisfied(
            mission_id=req.plan.mission_id, plan_hash=req.plan_hash,
            proposer_id=req.proposer_id, risk_class=verdict.risk_class,
        )
        if approval_id is None:
            ledger_client.record("mint.refused", verdict.decision, {
                "mission_id": req.plan.mission_id, "plan_hash": req.plan_hash, "reason": "approval required",
            })
            return MintResponse(verdict=verdict_dict, minted=False,
                                reason="policy verdict ESCALATE; human approval required")

    if not outcome.mint and approval_id is None:
        ledger_client.record("mint.refused", verdict.decision, {
            "mission_id": req.plan.mission_id, "plan_hash": req.plan_hash, "reason": outcome.reason,
        })
        return MintResponse(verdict=verdict_dict, minted=False, reason=outcome.reason)

    if req.mode == "LIVE" and not await lease_mod.is_valid():
        ledger_client.record("mint.refused", verdict.decision, {
            "mission_id": req.plan.mission_id, "plan_hash": req.plan_hash, "reason": "system lease invalid",
        })
        return MintResponse(verdict=verdict_dict, minted=False, reason="system lease invalid")

    cap_mode = outcome.capability_mode or req.mode
    token, claims = capability.mint(
        sub="fleet-controller",
        mission_id=req.plan.mission_id,
        plan_hash=req.plan_hash,
        action=req.action,
        target=req.target,
        mode=cap_mode,
        verdict_id=verdict.event_id or "unknown",
        policy_version=verdict.policy_version,
        approval_id=approval_id,
    )
    ledger_client.record("capability.minted", verdict.decision, {
        "mission_id": req.plan.mission_id, "plan_hash": req.plan_hash,
        "jti": claims.jti, "verdict_id": verdict.event_id, "mode": cap_mode,
        "expires_at": claims.expires_at,
    })
    return MintResponse(capability=token, jti=claims.jti, verdict=verdict_dict, minted=True,
                        reason=outcome.reason)
