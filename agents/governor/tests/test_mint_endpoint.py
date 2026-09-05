import fakeredis.aioredis
import pytest

import killswitch
import redis_state
import shepherd_client
from models import PlanRequest, canonical_hash


@pytest.fixture(autouse=True)
def _wire(monkeypatch, tmp_path):
    """Helper: wire."""
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))
    yield


def _plan():
    """Helper: plan."""
    return {
        "schema_version": 1,
        "mission_id": "mission_demo_1",
        "requested_actions": [
            {"action_id": "a1", "kind": "compose_profile.preview", "profile": "agents"}
        ],
        "constraints": {"max_services": 25, "allow_profiles": ["agents"], "deny_profiles": ["prod", "gpu"]},
    }


def _req(**over):
    """Helper: req."""
    plan = _plan()
    base = {
        "plan": plan,
        # Real canonical hash of `plan` — NOT a hardcoded literal. Fix 1
        # (final review) made the mint endpoint actually check plan_hash
        # against canonical_hash(plan); a fake literal like the old
        # "sha256:demo" would now 422 every test in this file.
        "plan_hash": canonical_hash(PlanRequest(**plan)),
        "mode": "DRY_RUN",
        "action": "compose_profile.preview", "target": "agents", "proposer_id": "mission-director",
    }
    base.update(over)
    return base


def _verdict(monkeypatch, decision, risk="INFRASTRUCTURE_MUTATION"):
    """Helper: verdict."""
    async def fake_eval(**kw):
        """Helper: fake eval."""
        return shepherd_client.Verdict(
            decision=decision, reason="test", risk_class=risk,
            policy_version="safety-2026-09-04.1", event_id="evt_1",
        )
    monkeypatch.setattr(shepherd_client, "evaluate_plan", fake_eval)


@pytest.mark.asyncio
async def test_allow_dry_run_mints(client, monkeypatch):
    """Test allow dry run mints."""
    _verdict(monkeypatch, "ALLOW")
    resp = await client.post("/v1/capabilities/mint", json=_req())
    body = resp.json()
    assert resp.status_code == 200
    assert body["minted"] is True
    assert body["capability"] and body["jti"].startswith("cap_")


@pytest.mark.asyncio
async def test_block_no_capability(client, monkeypatch):
    """Test block no capability."""
    _verdict(monkeypatch, "BLOCK")
    body = (await client.post("/v1/capabilities/mint", json=_req())).json()
    assert body["minted"] is False
    assert body["capability"] is None


@pytest.mark.asyncio
async def test_escalate_needs_approval(client, monkeypatch):
    """Test escalate needs approval."""
    _verdict(monkeypatch, "ESCALATE")
    body = (await client.post("/v1/capabilities/mint", json=_req())).json()
    assert body["minted"] is False
    assert "approval" in body["reason"].lower()


@pytest.mark.asyncio
async def test_kill_switch_refuses(client, monkeypatch):
    """Test kill switch refuses."""
    _verdict(monkeypatch, "ALLOW")
    await killswitch.engage("halt")
    body = (await client.post("/v1/capabilities/mint", json=_req())).json()
    assert body["minted"] is False
    assert "kill-switch" in body["reason"].lower()


@pytest.mark.asyncio
async def test_shepherd_down_fail_closed(client, monkeypatch):
    """Test shepherd down fail closed."""
    async def boom(**kw):
        """Helper: boom."""
        return shepherd_client._FAIL_CLOSED
    monkeypatch.setattr(shepherd_client, "evaluate_plan", boom)
    body = (await client.post("/v1/capabilities/mint", json=_req())).json()
    assert body["minted"] is False
    assert body["verdict"]["shepherd_available"] is False


@pytest.mark.asyncio
async def test_plan_hash_mismatch_422(client, monkeypatch):
    """Finding 1 (final review): plan_hash must actually be checked against
    the submitted plan, not bound verbatim from the request body."""
    _verdict(monkeypatch, "ALLOW")
    bad = _req(plan_hash="sha256:" + "0" * 64)
    resp = await client.post("/v1/capabilities/mint", json=bad)
    assert resp.status_code == 422
    assert "plan_hash" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_action_target_not_in_plan_422(client, monkeypatch):
    """Finding 1 (final review): action/target must actually appear in the
    plan's requested_actions, not be trusted verbatim from the request
    body — otherwise a benign validated plan could mint a capability bound
    to an arbitrary action/target (e.g. target="prod")."""
    _verdict(monkeypatch, "ALLOW")
    bad = _req(target="prod")
    resp = await client.post("/v1/capabilities/mint", json=bad)
    assert resp.status_code == 422
    assert "action/target" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_denied_profile_422(client, monkeypatch):
    """Test denied profile 422."""
    _verdict(monkeypatch, "ALLOW")
    bad = _req()
    bad["plan"]["requested_actions"][0]["profile"] = "gpu"
    resp = await client.post("/v1/capabilities/mint", json=bad)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_live_allow_mints_live_capability(client, monkeypatch):
    """Test live allow mints live capability."""
    _verdict(monkeypatch, "ALLOW")
    # Deviation from the brief's verbatim test (see task-12-report.md): the
    # brief's test never seeds a system lease, but the spec (north-star
    # design doc, table row for POST /v1/capabilities/mint) and this
    # endpoint's own LIVE-mode gate both require lease validity before
    # minting a LIVE capability. ASGITransport doesn't run lifespan/renew
    # loops for these tests, so the lease has to be seeded here directly,
    # via lease.py's own tested API (Task 9) rather than hand-writing the
    # Redis key.
    import lease
    await lease.renew_tick(shepherd_healthy=True)
    body = (await client.post("/v1/capabilities/mint", json=_req(mode="LIVE"))).json()
    assert body["minted"] is True
    import capability, keys, pyseto, json as _j
    payload = pyseto.decode(keys.load_public_key(), body["capability"], deserializer=_j).payload
    assert payload["mode"] == "LIVE"


@pytest.mark.asyncio
async def test_escalate_approved_mints_with_approval_id(client, monkeypatch):
    """The two-person rule's actual payoff: ESCALATE + two distinct approvers
    (INFRASTRUCTURE_MUTATION is in DANGEROUS_CLASSES, needs 2) must mint a
    capability, not refuse — with the approval_id embedded in the token."""
    _verdict(monkeypatch, "ESCALATE")
    import approvals

    req = _req()
    mission_id = req["plan"]["mission_id"]
    plan_hash = req["plan_hash"]
    await approvals.record(
        mission_id=mission_id, plan_hash=plan_hash,
        approver_id="approver_a", decision="approved", reason="ok",
    )
    await approvals.record(
        mission_id=mission_id, plan_hash=plan_hash,
        approver_id="approver_b", decision="approved", reason="ok",
    )

    resp = await client.post("/v1/capabilities/mint", json=req)
    body = resp.json()
    assert resp.status_code == 200
    assert body["minted"] is True
    assert body["capability"]
    assert body["jti"].startswith("cap_")

    import keys, pyseto, json as _j
    payload = pyseto.decode(keys.load_public_key(), body["capability"], deserializer=_j).payload
    assert payload["approval_id"] == f"appr-set:{mission_id}"


@pytest.mark.asyncio
async def test_escalate_single_approver_still_refused(client, monkeypatch):
    """Companion negative case: one approver is not enough for a DANGEROUS
    risk_class — must still refuse, not mint."""
    _verdict(monkeypatch, "ESCALATE")
    import approvals

    req = _req()
    mission_id = req["plan"]["mission_id"]
    plan_hash = req["plan_hash"]
    await approvals.record(
        mission_id=mission_id, plan_hash=plan_hash,
        approver_id="approver_a", decision="approved", reason="ok",
    )

    resp = await client.post("/v1/capabilities/mint", json=req)
    body = resp.json()
    assert resp.status_code == 200
    assert body["minted"] is False
    assert body["capability"] is None
