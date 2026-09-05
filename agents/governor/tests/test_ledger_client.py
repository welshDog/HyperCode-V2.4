import asyncio

import pytest

import ledger_client


@pytest.mark.asyncio
async def test_record_posts_when_key_from_file(monkeypatch, tmp_path):
    """End-to-end proof the finding is actually fixed: not just that
    init() resolves a key from CORE_AGENT_KEY_FILE, but that record()'s
    fire-and-forget task then actually POSTs a ledger row through the
    client init() built -- the concrete behavior the finding said was
    permanently no-op'd in the deployed configuration."""
    key_file = tmp_path / "k.txt"
    key_file.write_text("hc_k\n")
    monkeypatch.setenv("CORE_AGENT_KEY_FILE", str(key_file))
    monkeypatch.delenv("CORE_AGENT_KEY", raising=False)

    ledger_client._client = None
    ledger_client.init()
    assert ledger_client._client is not None

    seen = []

    class _Resp:
        status_code = 200

    async def fake_post(path, json=None):
        seen.append((path, json))
        return _Resp()

    monkeypatch.setattr(ledger_client._client, "post", fake_post)
    try:
        ledger_client.record("capability.minted", "ALLOW", {"jti": "cap_1"})
        # Let the fire-and-forget task actually run.
        for _ in range(5):
            if seen:
                break
            await asyncio.sleep(0)
        assert seen, "record() did not post -- ledger write still silently no-op'd"
        assert seen[0][0] == ledger_client.LEDGER_PATH
        assert seen[0][1]["action"] == "capability.minted"
        assert seen[0][1]["payload"] == {"jti": "cap_1"}
    finally:
        ledger_client._client = None


def test_init_reads_core_agent_key_file(monkeypatch, tmp_path):
    """Finding (final review, same fix wave): init() only ever read the
    plain CORE_AGENT_KEY env var, but docker-compose.secrets.yml sets
    CORE_AGENT_KEY_FILE for governor -- nothing ever populated the plain
    var in the deployed configuration, so init() always returned early and
    record() permanently no-op'd. CORE_AGENT_KEY_FILE must now win."""
    key_file = tmp_path / "agent_api_key_governor.txt"
    key_file.write_text("hc_test_governor_key\n")
    monkeypatch.setenv("CORE_AGENT_KEY_FILE", str(key_file))
    monkeypatch.delenv("CORE_AGENT_KEY", raising=False)

    ledger_client._client = None
    ledger_client.init()
    try:
        assert ledger_client._client is not None
        assert ledger_client._client.headers["X-Agent-Key"] == "hc_test_governor_key"
    finally:
        ledger_client._client = None


def test_init_falls_back_to_plain_env_var_when_no_file_set(monkeypatch):
    """The plain CORE_AGENT_KEY path (e.g. local/dev, no Docker secret)
    must keep working as a fallback."""
    monkeypatch.delenv("CORE_AGENT_KEY_FILE", raising=False)
    monkeypatch.setenv("CORE_AGENT_KEY", "hc_plain_env_key")

    ledger_client._client = None
    ledger_client.init()
    try:
        assert ledger_client._client is not None
        assert ledger_client._client.headers["X-Agent-Key"] == "hc_plain_env_key"
    finally:
        ledger_client._client = None


def test_init_noop_when_key_file_referenced_but_missing(monkeypatch, tmp_path):
    """A referenced-but-nonexistent CORE_AGENT_KEY_FILE must fail closed
    (no ledger client), not raise -- mirrors safety_shepherd.py's
    _read_secret_file OSError handling."""
    monkeypatch.setenv("CORE_AGENT_KEY_FILE", str(tmp_path / "does-not-exist.txt"))
    monkeypatch.delenv("CORE_AGENT_KEY", raising=False)

    ledger_client._client = None
    ledger_client.init()
    try:
        assert ledger_client._client is None
    finally:
        ledger_client._client = None


def test_build_body_shape():
    body = ledger_client.build_body("capability.minted", "ALLOW", {"jti": "cap_1"})
    assert body == {
        "agent": "governor",
        "action": "capability.minted",
        "decision": "ALLOW",
        "user_id": "system",
        "payload": {"jti": "cap_1"},
    }


def test_record_is_noop_without_client():
    ledger_client._client = None
    ledger_client.record("x", "ALLOW", {})  # must not raise
