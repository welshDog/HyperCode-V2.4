from __future__ import annotations

from fastapi import HTTPException
import pytest

from app.main import app
from app.middleware.agent_auth import require_agent_key


class _FakePipeline:
    def __init__(self) -> None:
        self.ops: list[tuple[str, tuple]] = []

    async def __aenter__(self) -> "_FakePipeline":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    def rpush(self, *args):
        self.ops.append(("rpush", args))

    def ltrim(self, *args):
        self.ops.append(("ltrim", args))

    def publish(self, *args):
        self.ops.append(("publish", args))

    async def execute(self):
        return []


class _FakeRedis:
    def __init__(self) -> None:
        self.pipeline_obj = _FakePipeline()

    def pipeline(self, transaction: bool = False) -> _FakePipeline:  # noqa: ARG002
        return self.pipeline_obj

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_require_agent_key_missing_header_returns_401():
    with pytest.raises(HTTPException) as exc:
        await require_agent_key(agent=None)
    assert exc.value.status_code == 401


def test_publish_event_rejects_when_agent_auth_fails(client, monkeypatch):
    from app.ws import events_broadcaster

    async def _deny():
        raise HTTPException(status_code=401, detail="Missing key")

    app.dependency_overrides[events_broadcaster.require_agent_key] = _deny
    try:
        resp = client.post("/api/v1/events", json={"channel": "system", "status": "info", "payload": {"k": "v"}})
    finally:
        app.dependency_overrides.pop(events_broadcaster.require_agent_key, None)

    assert resp.status_code == 401


def test_publish_event_accepts_with_valid_agent_key(client, monkeypatch):
    from app.ws import events_broadcaster

    fake_redis = _FakeRedis()

    async def _from_url(*args, **kwargs):  # noqa: ARG001
        return fake_redis

    async def _allow():
        return {"agent_name": "healer-agent", "rate_limit_rpm": 200}

    monkeypatch.setattr(events_broadcaster.aioredis, "from_url", _from_url)
    app.dependency_overrides[events_broadcaster.require_agent_key] = _allow
    try:
        resp = client.post(
            "/api/v1/events",
            json={"channel": "health", "agentId": "healer-agent", "status": "ok", "payload": {"action": "tick"}},
        )
    finally:
        app.dependency_overrides.pop(events_broadcaster.require_agent_key, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["channel"] == "health"
    assert body["agentId"] == "healer-agent"
    op_names = [name for name, _ in fake_redis.pipeline_obj.ops]
    assert op_names == ["rpush", "ltrim", "publish"]

