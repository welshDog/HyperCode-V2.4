"""API surface: health/status are open; research endpoints honour X-Agent-Key
and call the sweep layer (which is stubbed here so no network happens)."""

import importlib

import pytest
from fastapi.testclient import TestClient

from models import BriefResult


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AGENT_API_KEY", "secret")
    monkeypatch.setenv("RESEARCH_RUN_ON_STARTUP", "false")
    import config
    import scheduler
    import sweep
    importlib.reload(config)
    importlib.reload(sweep)

    async def _fake_topic(topic, max_sources, categories):
        return BriefResult(kind="topic", topic=topic, markdown="# stub", new_count=0)

    async def _fake_sweep():
        return BriefResult(kind="sweep", markdown="# stub", new_count=0)

    monkeypatch.setattr(sweep, "run_topic", _fake_topic)
    monkeypatch.setattr(sweep, "run_sweep", _fake_sweep)
    monkeypatch.setattr(scheduler, "start", lambda: None)
    monkeypatch.setattr(scheduler, "shutdown", lambda: None)

    import main
    importlib.reload(main)
    with TestClient(main.app) as c:
        yield c


def test_health_open(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_status_reports_safety(client):
    body = client.get("/status").json()
    assert body["safety"]["observe_only"] is True
    assert body["safety"]["self_evolve_enabled"] is False


def test_brief_requires_key(client):
    assert client.post("/research/brief", json={"topic": "rag"}).status_code == 401
    ok = client.post("/research/brief", json={"topic": "rag"}, headers={"X-Agent-Key": "secret"})
    assert ok.status_code == 200
    assert ok.json()["kind"] == "topic"


def test_run_now_requires_key(client):
    assert client.post("/research/run-now").status_code == 401
    ok = client.post("/research/run-now", headers={"X-Agent-Key": "secret"})
    assert ok.status_code == 200
    assert ok.json()["kind"] == "sweep"
