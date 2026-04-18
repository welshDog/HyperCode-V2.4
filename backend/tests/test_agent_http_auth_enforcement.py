from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.e2e
def test_base_agent_enforces_api_key(monkeypatch):
    monkeypatch.setenv("HYPERCODE_API_KEY", "hc_test_key")
    agent_mod = _load_module(
        "hc_base_agent_mod",
        Path(__file__).resolve().parents[2] / "agents" / "base-agent" / "agent.py",
    )

    class _FakeRedis:
        async def ping(self):
            return True

        async def close(self):
            return None

    async def _from_url(*args, **kwargs):  # noqa: ARG001
        return _FakeRedis()

    monkeypatch.setattr(agent_mod.redis, "from_url", _from_url)

    cfg = agent_mod.AgentConfig()
    agent = agent_mod.BaseAgent(cfg)
    with TestClient(agent.app) as client:
        assert client.get("/health").status_code == 200
        assert client.post("/execute", json={"task": "hello"}).status_code == 401
        ok = client.post("/execute", headers={"X-API-Key": "hc_test_key"}, json={"task": "hello"})
        assert ok.status_code == 200
        missing = client.post("/execute", headers={"X-API-Key": "hc_test_key"}, json={})
        assert missing.status_code == 422


@pytest.mark.e2e
def test_coder_agent_enforces_api_key(monkeypatch):
    monkeypatch.setenv("HYPERCODE_API_KEY", "hc_test_key")
    coder_mod = _load_module(
        "hc_coder_agent_mod",
        Path(__file__).resolve().parents[2] / "agents" / "coder" / "main.py",
    )

    cfg = coder_mod.AgentConfig(name="coder-agent", port=8002)
    agent = coder_mod.CoderAgent(cfg)
    with TestClient(agent.app) as client:
        assert client.get("/health").status_code == 200
        assert client.post("/execute", json={"id": "t1", "task": "hello"}).status_code == 401
        ok = client.post(
            "/execute",
            headers={"X-Agent-Key": "hc_test_key"},
            json={"id": "t1", "task": "hello"},
        )
        assert ok.status_code == 200
