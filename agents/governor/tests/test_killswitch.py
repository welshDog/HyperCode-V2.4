import fakeredis.aioredis
import pytest

import killswitch
import redis_state


@pytest.fixture
def fake(monkeypatch, tmp_path):
    """Helper: fake."""
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))
    return r


@pytest.mark.asyncio
async def test_default_not_killed(fake):
    """Test default not killed."""
    assert await killswitch.is_killed() is False


@pytest.mark.asyncio
async def test_redis_flag_kills(fake):
    """Test redis flag kills."""
    await killswitch.engage("manual test")
    assert await killswitch.is_killed() is True
    await killswitch.release("done")
    assert await killswitch.is_killed() is False


@pytest.mark.asyncio
async def test_sentinel_file_kills_even_after_release(fake, tmp_path):
    """Test sentinel file kills even after release."""
    (tmp_path / "KILL").write_text("stop")
    assert await killswitch.is_killed() is True
    await killswitch.release("api says clear")
    assert await killswitch.is_killed() is True  # file still present


@pytest.mark.asyncio
async def test_sentinel_check_filesystem_error_fails_closed(fake, monkeypatch):
    """Test sentinel check filesystem error fails closed."""
    def _raise(*a, **k):
        """Helper: raise."""
        raise OSError("filesystem fault")
    monkeypatch.setattr(killswitch.os, "stat", _raise)
    assert await killswitch.is_killed() is True


@pytest.mark.asyncio
async def test_sentinel_parent_directory_missing_fails_closed(fake, monkeypatch, tmp_path):
    """Follow-up fix: the sentinel's own directory being gone (e.g. an
    unmounted governance-control volume) must fail closed, not read as 'no
    sentinel placed'. Path.exists() swallowed this distinction entirely --
    a stat on a path whose parent doesn't exist raises the same
    FileNotFoundError as a path whose parent is fine and file is merely
    absent, so the parent must be checked on its own."""
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "vanished-mount" / "KILL"))
    assert await killswitch.is_killed() is True


@pytest.mark.asyncio
async def test_redis_unreachable_fails_closed(monkeypatch, tmp_path):
    """Test redis unreachable fails closed."""
    class Boom:
        async def get(self, *a, **k):
            """Helper: get."""
            raise ConnectionError("no redis")
    monkeypatch.setattr(redis_state, "get_redis", lambda: Boom())
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))
    assert await killswitch.is_killed() is True
