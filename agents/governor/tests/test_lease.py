from datetime import datetime, timedelta, timezone

import fakeredis.aioredis
import pytest

import killswitch
import lease
import redis_state

_NOW = datetime(2026, 9, 4, 13, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def fake(monkeypatch, tmp_path):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))
    return r


@pytest.mark.asyncio
async def test_renew_then_valid(fake):
    assert await lease.renew_tick(shepherd_healthy=True, ttl_seconds=300, now=_NOW) is True
    assert await lease.is_valid(now=_NOW + timedelta(seconds=120)) is True
    assert await lease.is_valid(now=_NOW + timedelta(seconds=400)) is False


@pytest.mark.asyncio
async def test_renew_skipped_when_killed(fake):
    await killswitch.engage("halt")
    assert await lease.renew_tick(shepherd_healthy=True, now=_NOW) is False
    assert await lease.is_valid(now=_NOW) is False


@pytest.mark.asyncio
async def test_renew_skipped_when_shepherd_down(fake):
    assert await lease.renew_tick(shepherd_healthy=False, now=_NOW) is False


@pytest.mark.asyncio
async def test_current_returns_none_when_redis_get_raises(fake, monkeypatch):
    async def raising_get(*args, **kwargs):
        raise ConnectionError("redis unreachable")

    monkeypatch.setattr(fake, "get", raising_get)
    assert await lease.current() is None


@pytest.mark.asyncio
async def test_current_returns_none_when_stored_value_malformed(fake):
    await fake.set("gov:lease", "not-valid-json")
    assert await lease.current() is None


@pytest.mark.asyncio
async def test_renew_tick_returns_false_when_redis_set_raises(fake, monkeypatch):
    async def raising_set(*args, **kwargs):
        raise ConnectionError("redis unreachable")

    monkeypatch.setattr(fake, "set", raising_set)
    assert await lease.renew_tick(shepherd_healthy=True, now=_NOW) is False
