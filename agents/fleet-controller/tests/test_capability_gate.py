import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

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
    assert body["capability"]["presented"] is False
    assert body["capability"]["valid"] is False
