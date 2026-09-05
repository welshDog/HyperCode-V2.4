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


def test_operator_key_comparison_handles_non_ascii(monkeypatch):
    """Fix 3 (final review): _require_operator switched to
    hmac.compare_digest for timing-safety. compare_digest raises TypeError
    when comparing `str` values that aren't pure ASCII -- realistically
    reachable if the operator-key secret file ever picks up a UTF-8 BOM or
    any non-ASCII byte (e.g. from a Windows editor). Must still be a clean
    401/accept, never an unhandled TypeError.

    Exercised at the function level, not over HTTP: httpx's header encoder
    itself rejects non-ASCII str header values before the request even
    reaches the app, which would test httpx's encoder, not this fix.
    """
    import main

    monkeypatch.setenv("OPERATOR_KEY", "s3cret-café")

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        main._require_operator("nope")
    assert exc.value.status_code == 401

    main._require_operator("s3cret-café")  # must not raise TypeError


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
async def test_approvals_post_requires_operator_key(client):
    """Finding 2 (final review): POST /v1/approvals had zero auth — anything
    on agents-net could record fake approvals and satisfy the two-person
    rule for any mission."""
    resp = await client.post("/v1/approvals", json={
        "mission_id": "m10", "plan_hash": "sha256:p", "approver_id": "mallory",
        "decision": "approved", "reason": "no key given",
    })
    assert resp.status_code == 401
    # Confirm the rejected call did not actually record anything: an
    # authenticated GET (also newly gated) shows an empty list.
    h = {"X-Operator-Key": "s3cret-op"}
    lst = (await client.get("/v1/approvals/m10", headers=h)).json()["approvals"]
    assert lst == []


@pytest.mark.asyncio
async def test_approvals_get_requires_operator_key(client):
    """Finding 2 (final review): GET /v1/approvals/{mission_id} had zero auth."""
    resp = await client.get("/v1/approvals/m9")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_record_and_list_approvals(client):
    h = {"X-Operator-Key": "s3cret-op"}
    r = await client.post("/v1/approvals", json={
        "mission_id": "m9", "plan_hash": "sha256:p", "approver_id": "alice",
        "decision": "approved", "reason": "lgtm",
    }, headers=h)
    assert r.json()["approval_id"].startswith("appr_")
    lst = (await client.get("/v1/approvals/m9", headers=h)).json()["approvals"]
    assert lst[0]["approver_id"] == "alice"
