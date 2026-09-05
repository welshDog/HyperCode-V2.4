from datetime import datetime, timedelta, timezone

import pytest

import capability

_NOW = datetime(2026, 9, 4, 13, 0, 0, tzinfo=timezone.utc)
_BASE = dict(
    sub="fleet-controller", mission_id="m", plan_hash="sha256:aaa",
    action="compose_profile.preview", target="agents", mode="DRY_RUN",
    verdict_id="v", policy_version="p",
)
_EXPECT = dict(
    expected_sub="fleet-controller", expected_plan_hash="sha256:aaa",
    expected_action="compose_profile.preview", expected_target="agents",
    expected_mode="DRY_RUN",
)


def _mint(**over):
    """Helper: mint."""
    kw = {**_BASE, **over}
    token, _ = capability.mint(now=_NOW, **kw)
    return token


def test_valid_token_verifies():
    """Test valid token verifies."""
    claims = capability.verify(_mint(), now=_NOW, **_EXPECT)
    assert claims.mission_id == "m"


@pytest.mark.parametrize("bad,code", [
    (dict(expected_plan_hash="sha256:bbb"), "plan_hash_mismatch"),
    (dict(expected_sub="crew-orchestrator"), "wrong_subject"),
    (dict(expected_action="compose_profile.start"), "out_of_scope"),
    (dict(expected_mode="LIVE"), "wrong_mode"),
])
def test_claim_gates(bad, code):
    """Test claim gates."""
    with pytest.raises(capability.VerifyError) as exc:
        capability.verify(_mint(), now=_NOW, **{**_EXPECT, **bad})
    assert exc.value.code == code


def test_expired():
    """Test expired."""
    with pytest.raises(capability.VerifyError) as exc:
        capability.verify(_mint(), now=_NOW + timedelta(seconds=301), **_EXPECT)
    assert exc.value.code == "expired"


def test_not_yet_valid():
    """Test not yet valid."""
    with pytest.raises(capability.VerifyError) as exc:
        capability.verify(_mint(), now=_NOW - timedelta(seconds=5), **_EXPECT)
    assert exc.value.code == "not_yet_valid"


def test_forged_signature():
    """Test forged signature."""
    good = _mint()
    forged = good[:-4] + ("AAAA" if good[-4:] != "AAAA" else "BBBB")
    with pytest.raises(capability.VerifyError) as exc:
        capability.verify(forged, now=_NOW, **_EXPECT)
    assert exc.value.code in ("bad_signature", "malformed")
