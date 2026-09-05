import fakeredis.aioredis
import pytest

import killswitch
import redis_state


@pytest.fixture(autouse=True)
def _wire(monkeypatch, tmp_path):
    """Helper: wire."""
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))
    monkeypatch.setenv("OPERATOR_KEY", "s3cret-op")


@pytest.mark.asyncio
async def test_kill_requires_operator_key(client):
    """Test kill requires operator key."""
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


def test_operator_key_reads_utf8_file_exactly(monkeypatch, tmp_path):
    """Finding (final review, same fix wave, closing the gap the last
    report flagged): _operator_key() previously read its secret file with
    open(path).read().strip() -- no explicit encoding, no try/except.
    On a box whose locale default isn't UTF-8 (cp1252 here), a UTF-8
    secret file with non-ASCII content would silently decode to mojibake
    and never match the real key an operator sends -- a functional
    lockout, the same bug class already fixed in ledger_client.py's
    _read_secret_file() this same wave. Proves the file is read back
    byte-for-byte correct, not just "some string"."""
    import main

    key_file = tmp_path / "operator_key.txt"
    original = "s3cret-café-🔑"
    key_file.write_text(original, encoding="utf-8")
    monkeypatch.setenv("OPERATOR_KEY_FILE", str(key_file))

    assert main._operator_key() == original


def test_operator_key_file_referenced_but_missing_falls_back(monkeypatch, tmp_path):
    """A referenced-but-nonexistent OPERATOR_KEY_FILE must fail closed to
    the plain OPERATOR_KEY fallback, not raise -- mirrors the OSError
    handling in _read_secret_file()."""
    import main

    monkeypatch.setenv("OPERATOR_KEY_FILE", str(tmp_path / "does-not-exist.txt"))
    monkeypatch.setenv("OPERATOR_KEY", "fallback-key")

    assert main._operator_key() == "fallback-key"


def test_operator_key_file_strips_bom(monkeypatch, tmp_path):
    """Follow-up fix (parked R2): the comment above _read_secret_file
    previously claimed BOM-handling that encoding="utf-8" does not
    actually provide. utf-8-sig does -- prove the BOM never reaches the
    returned key."""
    import main

    key_file = tmp_path / "operator_key.txt"
    key_file.write_bytes(b"\xef\xbb\xbfs3cret-op")
    monkeypatch.setenv("OPERATOR_KEY_FILE", str(key_file))

    assert main._operator_key() == "s3cret-op"


def test_operator_key_file_non_utf8_fails_closed_to_env(monkeypatch, tmp_path):
    """Follow-up fix (parked R1): a non-UTF-8 secret file must fail closed
    to the plain OPERATOR_KEY fallback, not raise UnicodeDecodeError
    (which would crash /v1/kill and /v1/unkill into an unhandled 500
    instead of a clean 401)."""
    import main

    key_file = tmp_path / "operator_key.txt"
    key_file.write_bytes(b"\xff\xfe\x00bad")
    monkeypatch.setenv("OPERATOR_KEY_FILE", str(key_file))
    monkeypatch.setenv("OPERATOR_KEY", "fallback-key")

    assert main._operator_key() == "fallback-key"


def test_operator_key_no_hardcoded_secret_default(monkeypatch):
    """Follow-up fix (parked R3): _operator_key() must not default
    OPERATOR_KEY_FILE to the shared /run/secrets/api_key path -- if the env
    var is genuinely unset, it must fall straight through to plain
    OPERATOR_KEY without ever attempting a file read, rather than silently
    reading whatever secret happens to be mounted at that shared default."""
    import main

    monkeypatch.delenv("OPERATOR_KEY_FILE", raising=False)
    monkeypatch.setenv("OPERATOR_KEY", "the-real-operator-key")

    calls = []
    monkeypatch.setattr(main, "_read_secret_file", lambda p: calls.append(p) or "")

    assert main._operator_key() == "the-real-operator-key"
    assert calls == [], f"_read_secret_file was called with no OPERATOR_KEY_FILE set: {calls}"


def test_operator_key_empty_file_falls_back_to_env(monkeypatch, tmp_path):
    """Deliberate precedence change from this fix, pinned by test: the old
    `if path and os.path.isfile(path): return open(path).read().strip()`
    returned "" for an existing-but-empty file and never fell through to
    OPERATOR_KEY. The new `if from_file:` guard treats "" as absent and
    falls through -- matching safety_shepherd.py's _core_agent_key()
    exactly (what this fix was told to mirror). Safe either way:
    _require_operator's `not expected` guard still 401s when both are
    empty."""
    import main

    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("OPERATOR_KEY_FILE", str(empty_file))
    monkeypatch.setenv("OPERATOR_KEY", "env-key")

    assert main._operator_key() == "env-key"


@pytest.mark.asyncio
async def test_kill_then_unkill(client):
    """Test kill then unkill."""
    h = {"X-Operator-Key": "s3cret-op"}
    assert (await client.post("/v1/kill", json={"reason": "halt"}, headers=h)).status_code == 200
    assert await killswitch.is_killed() is True
    assert (await client.post("/v1/unkill", json={"reason": "clear"}, headers=h)).status_code == 200
    assert await killswitch.is_killed() is False


@pytest.mark.asyncio
async def test_unkill_requires_reason(client):
    """Test unkill requires reason."""
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
async def test_approval_decision_bad_casing_422s_instead_of_silently_not_counting(client):
    """CodeRabbit follow-up: decision was a plain str -- a case typo like
    "Approved" previously got a 200 + approval_id, but satisfied()'s exact
    "approved" match meant it silently never counted toward the two-person
    rule. Literal on ApprovalRequest.decision turns that into an immediate
    422 instead of a silent no-count the caller has no way to detect."""
    h = {"X-Operator-Key": "s3cret-op"}
    resp = await client.post("/v1/approvals", json={
        "mission_id": "m11", "plan_hash": "sha256:p", "approver_id": "alice",
        "decision": "Approved", "reason": "case typo",
    }, headers=h)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_record_and_list_approvals(client):
    """Test record and list approvals."""
    h = {"X-Operator-Key": "s3cret-op"}
    r = await client.post("/v1/approvals", json={
        "mission_id": "m9", "plan_hash": "sha256:p", "approver_id": "alice",
        "decision": "approved", "reason": "lgtm",
    }, headers=h)
    assert r.json()["approval_id"].startswith("appr_")
    lst = (await client.get("/v1/approvals/m9", headers=h)).json()["approvals"]
    assert lst[0]["approver_id"] == "alice"
