import fakeredis.aioredis
import pytest

import redis_state


@pytest.fixture
def fake(monkeypatch):
    """Helper: fake."""
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    return r


@pytest.mark.asyncio
async def test_first_use_then_replay(fake):
    """Test first use then replay."""
    assert await redis_state.register_use("cap_1", 300) is True
    assert await redis_state.register_use("cap_1", 300) is False


@pytest.mark.asyncio
async def test_revoke_jti(fake):
    """Test revoke jti."""
    assert await redis_state.is_revoked("cap_2") is False
    await redis_state.revoke("cap_2")
    assert await redis_state.is_revoked("cap_2") is True


@pytest.mark.asyncio
async def test_revoke_mission(fake):
    """Test revoke mission."""
    await redis_state.revoke_mission("mission_x")
    assert await redis_state.is_mission_revoked("mission_x") is True


@pytest.mark.asyncio
async def test_revoke_jti_sets_ttl(fake):
    """CodeRabbit follow-up: revocation keys previously had no expiry and
    accumulated in Redis DB 3 for the deployment's lifetime."""
    await redis_state.revoke("cap_3")
    ttl = await fake.ttl("gov:revoked:jti:cap_3")
    assert 0 < ttl <= redis_state._REVOCATION_TTL_SECONDS


@pytest.mark.asyncio
async def test_revoke_mission_sets_ttl(fake):
    """Test revoke mission sets ttl."""
    await redis_state.revoke_mission("mission_y")
    ttl = await fake.ttl("gov:revoked:mission:mission_y")
    assert 0 < ttl <= redis_state._REVOCATION_TTL_SECONDS
