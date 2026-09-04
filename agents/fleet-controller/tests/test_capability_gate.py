import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pytest
from pydantic import BaseModel

sys.path.append(str(Path(__file__).resolve().parents[1]))

import capability_verify  # noqa: E402


@pytest.fixture()
def _ephemeral_gov_key(tmp_path, monkeypatch):
    """Self-contained ephemeral Ed25519 keypair for this test file only.

    Ruling P2: the brief's literal test reads
    secrets/governor_ed25519_private_key.txt via a relative path, which is
    gitignored and won't exist in CI or on a fresh clone. This fixture mints
    its own keypair (same pattern as agents/governor/keys.py's own test
    fixture / agents/governor/tests/conftest.py's autouse fixture), points
    capability_verify at the ephemeral public half via
    GOVERNOR_PUBLIC_KEY_FILE, and hands back the matching private pyseto key
    for minting test tokens directly with pyseto — no dependency on any file
    outside the test itself.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    priv = Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pub_pem = (
        priv.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    pub_file = tmp_path / "governor_public_key.pem"
    pub_file.write_text(pub_pem)
    monkeypatch.setenv("GOVERNOR_PUBLIC_KEY_FILE", str(pub_file))

    import pyseto

    priv_key = pyseto.Key.new(version=4, purpose="public", key=priv_pem)
    return priv_key


def _gov_token(priv_key, **over):
    """Mint a token with the ephemeral private key handed back by
    _ephemeral_gov_key — never reads secrets/governor_ed25519_private_key.txt."""
    import pyseto

    now = datetime.now(timezone.utc)
    claims = {
        "iss": "governor", "sub": "fleet-controller", "mission_id": "m",
        "plan_hash": "sha256:demo", "action": "compose_profile.preview", "target": "agents",
        "mode": "DRY_RUN", "max_attempts": 1,
        "not_before": now.isoformat(), "expires_at": (now + timedelta(seconds=300)).isoformat(),
        "jti": "cap_test", "verdict_id": "v", "policy_version": "p", "approval_id": None,
    }
    claims.update(over)
    return pyseto.encode(priv_key, payload=claims, serializer=json).decode()


def test_no_token():
    ok, reason = capability_verify.verify_or_none(
        None, plan_hash="sha256:demo", action="compose_profile.preview", target="agents", mode="DRY_RUN"
    )
    assert ok is False
    assert "no capability" in reason.lower()


def test_valid_token(_ephemeral_gov_key):
    ok, reason = capability_verify.verify_or_none(
        _gov_token(_ephemeral_gov_key),
        plan_hash="sha256:demo", action="compose_profile.preview", target="agents", mode="DRY_RUN"
    )
    assert ok is True


def test_plan_hash_mismatch(_ephemeral_gov_key):
    ok, reason = capability_verify.verify_or_none(
        _gov_token(_ephemeral_gov_key),
        plan_hash="sha256:OTHER", action="compose_profile.preview", target="agents", mode="DRY_RUN"
    )
    assert ok is False
    assert "plan_hash" in reason


def test_canonical_hash_stable_regardless_of_capability():
    """The property the whole verify pipeline depends on: a capability token
    is minted against a plan_hash computed BEFORE the token exists to attach
    to the plan, so canonical_hash must be identical whether or not a
    capability is riding alongside the plan. Fix 1 (controller-ruled):
    canonical_hash excludes the `capability` field."""
    from models import Constraints, PlanRequest, RequestedAction, canonical_hash

    plan = PlanRequest(
        schema_version=1,
        mission_id="m",
        requested_actions=[RequestedAction(action_id="a1", kind="compose_profile.preview", profile="agents")],
        constraints=Constraints(allow_profiles=["agents"]),
    )
    plan_with_cap = plan.model_copy(update={"capability": "some-token"})

    assert canonical_hash(plan) == canonical_hash(plan_with_cap)


@pytest.mark.asyncio
async def test_preview_reports_capability_and_never_executes(client, monkeypatch):
    import safety_client

    async def fake_check(plan, plan_hash):
        return safety_client.SafetyResult(decision="ALLOW", reason="ok")
    monkeypatch.setattr(safety_client, "check_infrastructure_mutation", fake_check)

    plan = {
        "schema_version": 1, "mission_id": "m",
        "requested_actions": [{"action_id": "a1", "kind": "compose_profile.preview", "profile": "agents"}],
        "constraints": {"allow_profiles": ["agents"], "deny_profiles": ["prod", "gpu"]},
        "capability": None,
    }
    body = (await client.post("/v1/plans/preview", json=plan)).json()
    assert body["execution"]["performed"] is False
    assert body["capability_check"]["presented"] is False
    assert body["capability_check"]["valid"] is False
    # Fix 2 (controller-ruled): `capability` stays the original Optional[str]
    # type — null when nothing valid was presented — so mission-director's
    # mirrored PlanResponse model keeps parsing this response.
    assert body["capability"] is None


@pytest.mark.asyncio
async def test_preview_echoes_token_only_when_capability_valid(client, monkeypatch, _ephemeral_gov_key):
    """Fix 2: `capability` echoes the submitted token back only when it
    verified valid; `capability_check` always carries the full breakdown."""
    import safety_client

    async def fake_check(plan, plan_hash):
        return safety_client.SafetyResult(decision="ALLOW", reason="ok")
    monkeypatch.setattr(safety_client, "check_infrastructure_mutation", fake_check)

    plan = {
        "schema_version": 1, "mission_id": "m",
        "requested_actions": [{"action_id": "a1", "kind": "compose_profile.preview", "profile": "agents"}],
        "constraints": {"allow_profiles": ["agents"], "deny_profiles": ["prod", "gpu"]},
    }
    # First call (no capability) to learn the real plan_hash the server computes.
    first = (await client.post("/v1/plans/preview", json=plan)).json()
    plan_hash = first["plan_hash"]

    token = _gov_token(
        _ephemeral_gov_key,
        plan_hash=plan_hash, action="compose_profile.preview", target="agents",
    )
    plan["capability"] = token
    body = (await client.post("/v1/plans/preview", json=plan)).json()

    assert body["plan_hash"] == plan_hash  # capability excluded from the hash (Fix 1)
    assert body["capability_check"]["presented"] is True
    assert body["capability_check"]["valid"] is True
    assert body["capability"] == token  # echoed back — proves valid-path echo works

    # And an invalid token (mismatched target) must NOT be echoed.
    bad_token = _gov_token(
        _ephemeral_gov_key,
        plan_hash=plan_hash, action="compose_profile.preview", target="WRONG",
    )
    plan["capability"] = bad_token
    body2 = (await client.post("/v1/plans/preview", json=plan)).json()
    assert body2["capability_check"]["valid"] is False
    assert body2["capability"] is None


class _MissionDirectorStylePlanResponseMirror(BaseModel):
    """Throwaway stand-in for agents/mission-director/models.py's
    PlanResponse — same shape, deliberately NOT importing mission-director's
    actual module (no cross-agent import). This is the exact regression that
    slipped through before the controller's Fix 2: fleet-controller's
    capability field changing type would break every real caller with this
    shape. Only the fields relevant to the regression are mirrored."""

    plan_id: str
    plan_hash: str
    capability: Optional[str] = None


@pytest.mark.asyncio
async def test_response_parses_against_plain_str_capability_mirror_model(client, monkeypatch):
    """Regression test for the wire-compat break the controller ruled on:
    proves PlanResponse(**resp.json()) still succeeds against a model where
    `capability` is plainly Optional[str], the way mission-director's own
    mirrored model declares it."""
    import safety_client

    async def fake_check(plan, plan_hash):
        return safety_client.SafetyResult(decision="ALLOW", reason="ok")
    monkeypatch.setattr(safety_client, "check_infrastructure_mutation", fake_check)

    plan = {
        "schema_version": 1, "mission_id": "m",
        "requested_actions": [{"action_id": "a1", "kind": "compose_profile.preview", "profile": "agents"}],
        "constraints": {"allow_profiles": ["agents"], "deny_profiles": ["prod", "gpu"]},
    }
    resp = await client.post("/v1/plans/preview", json=plan)
    # Would raise pydantic.ValidationError if `capability` were still a dict-typed field.
    mirrored = _MissionDirectorStylePlanResponseMirror(**resp.json())
    assert mirrored.capability is None
