import fakeredis.aioredis
import pytest

import killswitch
import redis_state


@pytest.fixture(autouse=True)
def _wire(monkeypatch, tmp_path):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))
    monkeypatch.setenv("OPERATOR_KEY", "s3cret-op")


@pytest.mark.asyncio
async def test_kill_requires_operator_key(client):
    assert (await client.post("/v1/kill", json={"reason": "x"})).status_code == 401


@pytest.mark.asyncio
async def test_kill_then_unkill(client):
    h = {"X-Operator-Key": "s3cret-op"}
    assert (await client.post("/v1/kill", json={"reason": "halt"}, headers=h)).status_code == 200
    assert await killswitch.is_killed() is True
    assert (await client.post("/v1/unkill", json={"reason": "clear"}, headers=h)).status_code == 200
    assert await killswitch.is_killed() is False


@pytest.mark.asyncio
async def test_unkill_requires_reason(client):
    h = {"X-Operator-Key": "s3cret-op"}
    assert (await client.post("/v1/unkill", json={"reason": ""}, headers=h)).status_code == 422


@pytest.mark.asyncio
async def test_record_and_list_approvals(client):
    r = await client.post("/v1/approvals", json={
        "mission_id": "m9", "plan_hash": "sha256:p", "approver_id": "alice",
        "decision": "approved", "reason": "lgtm",
    })
    assert r.json()["approval_id"].startswith("appr_")
    lst = (await client.get("/v1/approvals/m9")).json()["approvals"]
    assert lst[0]["approver_id"] == "alice"
