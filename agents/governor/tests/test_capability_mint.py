from datetime import datetime, timedelta, timezone

import pyseto
import pytest

import capability
import keys


def _decode(token: str) -> dict:
    """Helper: decode."""
    return pyseto.decode(keys.load_public_key(), token, deserializer=__import__("json")).payload


def test_mint_claims_present_and_bound():
    """Test mint claims present and bound."""
    now = datetime(2026, 9, 4, 13, 0, 0, tzinfo=timezone.utc)
    token, claims = capability.mint(
        sub="fleet-controller",
        mission_id="mission_abc",
        plan_hash="sha256:deadbeef",
        action="compose_profile.preview",
        target="agents",
        mode="DRY_RUN",
        verdict_id="verdict_1",
        policy_version="safety-2026-09-04.1",
        ttl_seconds=300,
        now=now,
    )
    payload = _decode(token)
    assert payload["iss"] == "governor"
    assert payload["sub"] == "fleet-controller"
    assert payload["plan_hash"] == "sha256:deadbeef"
    assert payload["action"] == "compose_profile.preview"
    assert payload["mode"] == "DRY_RUN"
    assert payload["max_attempts"] == 1
    assert payload["jti"].startswith("cap_")
    assert payload["not_before"] == "2026-09-04T13:00:00+00:00"
    assert payload["expires_at"] == "2026-09-04T13:05:00+00:00"
    assert claims.jti == payload["jti"]


def test_mint_jti_unique():
    """Test mint jti unique."""
    kw = dict(
        sub="fleet-controller", mission_id="m", plan_hash="sha256:x",
        action="compose_profile.preview", target=None, mode="DRY_RUN",
        verdict_id="v", policy_version="p",
    )
    _, c1 = capability.mint(**kw)
    _, c2 = capability.mint(**kw)
    assert c1.jti != c2.jti
