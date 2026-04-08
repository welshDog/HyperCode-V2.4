from unittest.mock import patch

import pytest

from app.core.config import settings


class _FakeRedis:
    def __init__(self):
        self._kv: dict[str, str] = {}
        self._counters: dict[str, int] = {}

    async def get(self, key: str):
        return self._kv.get(key)

    async def set(self, key: str, value: str, ex=None, nx: bool = False):
        if nx and key in self._kv:
            return False
        self._kv[key] = value
        return True

    async def delete(self, key: str):
        self._kv.pop(key, None)
        return 1

    async def incr(self, key: str):
        self._counters[key] = self._counters.get(key, 0) + 1
        return self._counters[key]

    async def expire(self, key: str, seconds: int):
        return True

    async def aclose(self):
        return None


@pytest.fixture
def hypersync_key():
    return "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _handoff_payload():
    return {
        "client_id": "client-abc-123",
        "messages": [{"role": "user", "content": "hello", "timestamp": 1}],
        "context_variables": {"x": 1},
        "file_references": [{"path": "README.md", "line_start": 1, "line_end": 2}],
        "user_preferences": {"sensory_profile": "CALM"},
        "session_meta": {"source": "test"},
    }


def test_hypersync_handoff_and_redeem_round_trip(client, hypersync_key, monkeypatch):
    fake_redis = _FakeRedis()
    monkeypatch.setattr(settings, "HYPERSYNC_MASTER_KEY", hypersync_key)

    with patch("app.api.v1.endpoints.hypersync.aioredis.from_url", return_value=fake_redis):
        resp = client.post(
            "/api/v1/hypersync/handoff",
            json=_handoff_payload(),
            headers={"Idempotency-Key": "550e8400-e29b-41d4-a716-446655440000"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "resume_token" in data
        assert "handoff_id" in data

        redeem = client.post(
            "/api/v1/hypersync/redeem",
            json={"resume_token": data["resume_token"], "client_id": "client-abc-123"},
        )
        assert redeem.status_code == 200
        redeemed = redeem.json()
        assert redeemed["handoff_id"] == data["handoff_id"]
        assert redeemed["state"]["client_id"] == "client-abc-123"
        assert redeemed["state"]["messages"][0]["content"] == "hello"

        redeem_again = client.post(
            "/api/v1/hypersync/redeem",
            json={"resume_token": data["resume_token"], "client_id": "client-abc-123"},
        )
        assert redeem_again.status_code == 200


def test_hypersync_redeem_rejects_wrong_client(client, hypersync_key, monkeypatch):
    fake_redis = _FakeRedis()
    monkeypatch.setattr(settings, "HYPERSYNC_MASTER_KEY", hypersync_key)

    with patch("app.api.v1.endpoints.hypersync.aioredis.from_url", return_value=fake_redis):
        resp = client.post("/api/v1/hypersync/handoff", json=_handoff_payload())
        token = resp.json()["resume_token"]

        bad = client.post("/api/v1/hypersync/redeem", json={"resume_token": token, "client_id": "client-wrong"})
        assert bad.status_code == 403


def test_hypersync_requires_key(client, monkeypatch):
    monkeypatch.setattr(settings, "HYPERSYNC_MASTER_KEY", None)
    resp = client.post("/api/v1/hypersync/handoff", json={"client_id": "client-abc-123", "messages": []})
    assert resp.status_code == 503


def test_hypersync_rate_limit_429(client, hypersync_key, monkeypatch):
    fake_redis = _FakeRedis()
    monkeypatch.setattr(settings, "HYPERSYNC_MASTER_KEY", hypersync_key)

    with patch("app.api.v1.endpoints.hypersync.aioredis.from_url", return_value=fake_redis):
        last = None
        for _ in range(11):
            last = client.post("/api/v1/hypersync/handoff", json={"client_id": "client-abc-123", "messages": []})
        assert last is not None
        assert last.status_code == 429

