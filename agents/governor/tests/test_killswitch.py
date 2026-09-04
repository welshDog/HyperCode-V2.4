import fakeredis.aioredis
import pytest

import killswitch
import redis_state


@pytest.fixture
def fake(monkeypatch, tmp_path):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))
    return r


@pytest.mark.asyncio
async def test_default_not_killed(fake):
    assert await killswitch.is_killed() is False


@pytest.mark.asyncio
async def test_redis_flag_kills(fake):
    await killswitch.engage("manual test")
    assert await killswitch.is_killed() is True
    await killswitch.release("done")
    assert await killswitch.is_killed() is False


@pytest.mark.asyncio
async def test_sentinel_file_kills_even_after_release(fake, tmp_path):
    (tmp_path / "KILL").write_text("stop")
    assert await killswitch.is_killed() is True
    await killswitch.release("api says clear")
    assert await killswitch.is_killed() is True  # file still present


@pytest.mark.asyncio
async def test_redis_unreachable_fails_closed(monkeypatch, tmp_path):
    class Boom:
        async def get(self, *a, **k):
            raise ConnectionError("no redis")
    monkeypatch.setattr(redis_state, "get_redis", lambda: Boom())
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))
    assert await killswitch.is_killed() is True
