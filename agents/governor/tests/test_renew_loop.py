import fakeredis.aioredis
import pytest

import lease
import redis_state
import shepherd_client


@pytest.fixture
def fake(monkeypatch, tmp_path):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))


@pytest.mark.asyncio
async def test_healthy_probe_true(monkeypatch, fake):
    import httpx
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    monkeypatch.setattr(shepherd_client, "_get_client", lambda: client)
    assert await shepherd_client.healthy() is True
    await client.aclose()


@pytest.mark.asyncio
async def test_healthy_probe_failclosed(monkeypatch, fake):
    import httpx
    def boom(r):
        raise httpx.ConnectError("no")
    client = httpx.AsyncClient(transport=httpx.MockTransport(boom))
    monkeypatch.setattr(shepherd_client, "_get_client", lambda: client)
    assert await shepherd_client.healthy() is False
    await client.aclose()


@pytest.mark.asyncio
async def test_one_renew_tick_via_loop_body(monkeypatch, fake):
    monkeypatch.setattr(shepherd_client, "healthy", lambda: _true())
    async def _true():
        return True
    ok = await lease.renew_tick(shepherd_healthy=await shepherd_client.healthy())
    assert ok is True
    assert await lease.is_valid() is True
