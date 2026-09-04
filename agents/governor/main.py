"""
governor — Phase 2. The governance-plane nucleus.

Mints signed, scope-bound capability tokens. Holds the kill-switch, the
Ed25519 signing key, the jti replay store, the system lease, and approval
records. Structurally inert: no Docker socket, no DOCKER_HOST, no
crew-orchestrator credential, no LLM/MCP client. See
docs/superpowers/specs/2026-09-04-autonomous-control-plane-north-star-design.md
"""
from __future__ import annotations

import asyncio
import json as _json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import FastAPI, Header, HTTPException

import capability
import ledger_client
import lease as lease_mod
import redis_state
import shepherd_client
import transitions
from approvals import record as approvals_record
from approvals import satisfied as approvals_satisfied
from killswitch import engage as kill_engage
from killswitch import is_killed
from killswitch import release as kill_release
from models import ApprovalRequest, KillRequest, MintRequest, MintResponse, RevokeRequest, VerifyRequest
from plan_validator import PlanValidationError, validate_plan


async def _renew_loop() -> None:
    try:
        interval = max(int(os.getenv("GOVERNOR_LEASE_RENEW_SECONDS") or 120), 1)
    except ValueError:
        interval = 120
    while True:
        try:
            await lease_mod.renew_tick(shepherd_healthy=await shepherd_client.healthy())
        except Exception:
            pass
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    ledger_client.init()
    task = asyncio.create_task(_renew_loop())
    try:
        yield
    finally:
        task.cancel()
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


@app.post("/v1/capabilities/verify")
async def verify_capability(req: VerifyRequest) -> dict:
    try:
        claims = capability.verify(
            req.token, expected_sub=req.expected_sub, expected_plan_hash=req.expected_plan_hash,
            expected_action=req.expected_action, expected_target=req.expected_target,
            expected_mode=req.expected_mode,
        )
    except capability.VerifyError as exc:
        return {"valid": False, "code": exc.code, "claims": None}

    if await redis_state.is_revoked(claims.jti) or await redis_state.is_mission_revoked(claims.mission_id):
        return {"valid": False, "code": "revoked", "claims": None}
    if await is_killed():
        return {"valid": False, "code": "kill_switch", "claims": None}
    if req.burn:
        remaining = (datetime.fromisoformat(claims.expires_at) - datetime.now(timezone.utc)).total_seconds()
        ttl = max(int(remaining), 1)
        first = await redis_state.register_use(claims.jti, ttl)
        if not first:
            return {"valid": False, "code": "replayed", "claims": None}
    return {"valid": True, "code": None, "claims": claims.model_dump()}


@app.post("/v1/capabilities/revoke")
async def revoke_capability(req: RevokeRequest) -> dict:
    if req.jti:
        await redis_state.revoke(req.jti)
    if req.mission_id:
        await redis_state.revoke_mission(req.mission_id)
    ledger_client.record("capability.revoked", "REVOKED", {
        "jti": req.jti, "mission_id": req.mission_id, "reason": req.reason,
    })
    return {"revoked": True}


@app.get("/v1/lease")
async def get_lease() -> dict:
    return {"lease": await lease_mod.current(), "valid": await lease_mod.is_valid()}


def _operator_key() -> str:
    path = os.getenv("OPERATOR_KEY_FILE", "/run/secrets/api_key")
    if path and os.path.isfile(path):
        return open(path).read().strip()
    return (os.getenv("OPERATOR_KEY") or "").strip()


def _require_operator(x_operator_key: str | None) -> None:
    expected = _operator_key()
    if not expected or x_operator_key != expected:
        raise HTTPException(status_code=401, detail="invalid operator key")


@app.post("/v1/approvals")
async def post_approval(req: ApprovalRequest) -> dict:
    approval_id = await approvals_record(
        mission_id=req.mission_id, plan_hash=req.plan_hash, approver_id=req.approver_id,
        decision=req.decision, reason=req.reason,
    )
    ledger_client.record("approval.recorded", req.decision.upper(), {
        "mission_id": req.mission_id, "plan_hash": req.plan_hash,
        "approver_id": req.approver_id, "approval_id": approval_id,
    })
    return {"approval_id": approval_id}


@app.get("/v1/approvals/{mission_id}")
async def list_approvals(mission_id: str) -> dict:
    raw = await redis_state.get_redis().lrange(f"gov:appr:{mission_id}", 0, -1)
    return {"approvals": [_json.loads(x) for x in raw]}


@app.post("/v1/kill")
async def post_kill(req: KillRequest, x_operator_key: str | None = Header(default=None)) -> dict:
    _require_operator(x_operator_key)
    await kill_engage(req.reason)
    ledger_client.record("kill.engaged", "KILL", {"reason": req.reason})
    return {"killed": True}


@app.post("/v1/unkill")
async def post_unkill(req: KillRequest, x_operator_key: str | None = Header(default=None)) -> dict:
    _require_operator(x_operator_key)
    await kill_release(req.reason)
    ledger_client.record("kill.released", "UNKILL", {"reason": req.reason})
    return {"released": True, "note": "sentinel file, if present, still forces killed"}
