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


@pytest.mark.asyncio
async def test_is_valid_false_on_missing_expires_at(fake):
    """CodeRabbit follow-up: a record missing expires_at previously raised
    KeyError straight through is_valid() -- main.py calls this unguarded on
    the LIVE mint path, which would 500 instead of cleanly refusing."""
    import json
    await fake.set("gov:lease", json.dumps({"lease_id": "lease_x"}))
    assert await lease.is_valid(now=_NOW) is False


@pytest.mark.asyncio
async def test_is_valid_false_on_unparsable_expires_at(fake):
    import json
    await fake.set("gov:lease", json.dumps({"lease_id": "lease_x", "expires_at": "not-a-date"}))
    assert await lease.is_valid(now=_NOW) is False


@pytest.mark.asyncio
async def test_is_valid_false_on_naive_expires_at(fake):
    """A naive (tzinfo-less) timestamp can't be safely compared to an
    aware `now` -- must be treated as invalid, not raise or silently
    compare wrong."""
    import json
    await fake.set("gov:lease", json.dumps({
        "lease_id": "lease_x",
        "expires_at": (_NOW + timedelta(seconds=300)).replace(tzinfo=None).isoformat(),
    }))
    assert await lease.is_valid(now=_NOW) is False
