import fakeredis.aioredis
import pytest

import redis_state


@pytest.fixture
def fake(monkeypatch):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    return r


@pytest.mark.asyncio
async def test_first_use_then_replay(fake):
    assert await redis_state.register_use("cap_1", 300) is True
    assert await redis_state.register_use("cap_1", 300) is False


@pytest.mark.asyncio
async def test_revoke_jti(fake):
    assert await redis_state.is_revoked("cap_2") is False
    await redis_state.revoke("cap_2")
    assert await redis_state.is_revoked("cap_2") is True


@pytest.mark.asyncio
async def test_revoke_mission(fake):
    await redis_state.revoke_mission("mission_x")
    assert await redis_state.is_mission_revoked("mission_x") is True
