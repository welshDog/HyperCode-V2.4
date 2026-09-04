import fakeredis.aioredis
import pytest

import capability
import redis_state

_EXPECT = dict(
    expected_sub="fleet-controller", expected_plan_hash="sha256:v",
    expected_action="compose_profile.preview", expected_target="agents",
    expected_mode="DRY_RUN",
)


@pytest.fixture(autouse=True)
def _wire(monkeypatch, tmp_path):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))


def _token():
    tok, _ = capability.mint(
        sub="fleet-controller", mission_id="m", plan_hash="sha256:v",
        action="compose_profile.preview", target="agents", mode="DRY_RUN",
        verdict_id="v", policy_version="p",
    )
    return tok


@pytest.mark.asyncio
async def test_verify_valid(client):
    body = (await client.post("/v1/capabilities/verify", json={"token": _token(), **_EXPECT})).json()
    assert body["valid"] is True
    assert body["code"] is None


@pytest.mark.asyncio
async def test_verify_rejects_revoked_mission(client):
    await client.post("/v1/capabilities/revoke", json={"mission_id": "m", "reason": "test"})
    body = (await client.post("/v1/capabilities/verify", json={"token": _token(), **_EXPECT})).json()
    assert body["valid"] is False
    assert body["code"] == "revoked"


@pytest.mark.asyncio
async def test_verify_burn_then_replay(client):
    tok = _token()
    first = (await client.post("/v1/capabilities/verify", json={"token": tok, "burn": True, **_EXPECT})).json()
    assert first["valid"] is True
    second = (await client.post("/v1/capabilities/verify", json={"token": tok, "burn": True, **_EXPECT})).json()
    assert second["valid"] is False
    assert second["code"] == "replayed"


@pytest.mark.asyncio
async def test_lease_endpoint(client):
    body = (await client.get("/v1/lease")).json()
    assert body["valid"] is False
    assert body["lease"] is None
