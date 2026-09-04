import asyncio

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


@pytest.mark.asyncio
async def test_renew_loop_survives_raising_healthy(monkeypatch, fake):
    """Finding 1: a raising healthy() must not kill main._renew_loop() —
    the loop must catch it and continue to a second iteration."""
    import main

    calls = {"n": 0}

    async def _boom():
        calls["n"] += 1
        raise RuntimeError("boom")

    monkeypatch.setattr(shepherd_client, "healthy", _boom)

    sleep_calls = {"n": 0}

    async def _fast_sleep(_seconds):
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 2:
            raise asyncio.CancelledError()

    monkeypatch.setattr(main.asyncio, "sleep", _fast_sleep)

    with pytest.raises(asyncio.CancelledError):
        await main._renew_loop()

    # healthy() raised on tick 1, but the loop kept going and called it
    # again on tick 2 — proof the try/except kept it alive.
    assert calls["n"] >= 2


@pytest.mark.asyncio
async def test_renew_loop_survives_malformed_interval_env(monkeypatch, fake):
    """Finding 3: a malformed GOVERNOR_LEASE_RENEW_SECONDS must not raise
    before the try/except even exists — proves the parse itself can't kill
    the loop on startup."""
    import main

    monkeypatch.setenv("GOVERNOR_LEASE_RENEW_SECONDS", "not-a-number")

    async def _healthy():
        return True

    monkeypatch.setattr(shepherd_client, "healthy", _healthy)

    sleep_calls = {"n": 0}

    async def _fast_sleep(_seconds):
        sleep_calls["n"] += 1
        raise asyncio.CancelledError()

    monkeypatch.setattr(main.asyncio, "sleep", _fast_sleep)

    # If the malformed env var raised before the try/except, this would
    # raise ValueError instead of ever reaching the (mocked) sleep call.
    with pytest.raises(asyncio.CancelledError):
        await main._renew_loop()

    assert sleep_calls["n"] == 1


@pytest.mark.asyncio
async def test_lifespan_starts_and_cancels_renew_loop(monkeypatch, fake):
    """Finding 2: lifespan must actually start _renew_loop as a task on
    entry and actually cancel it on exit — driven end-to-end, not just
    read from the source."""
    import main

    async def _healthy():
        return True

    monkeypatch.setattr(shepherd_client, "healthy", _healthy)

    before = asyncio.all_tasks()
    task = None
    async with main.app.router.lifespan_context(main.app):
        new_tasks = asyncio.all_tasks() - before
        assert len(new_tasks) == 1
        task = new_tasks.pop()
        assert not task.done()

    assert task is not None
    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled()
