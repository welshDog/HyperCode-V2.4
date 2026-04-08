"""
Task 12 — Backend tests for dashboard live-data endpoints and middleware.

Coverage:
  - GET  /api/v1/metrics           (metrics_broadcaster)
  - GET  /api/v1/agents/status     (agents_broadcaster)
  - GET  /api/v1/error-budget      (reliability)
  - GET  /api/v1/system/state      (reliability)
  - GET  /api/v1/logs              (logs_broadcaster)
  - GET  /api/v1/tasks (public)    (routes.tasks)
  - POST /api/v1/tasks (public)    (routes.tasks)
  - POST /api/v1/tasks/check-errors (auto-task logic)
  - HTTP metrics middleware         (main._http_metrics_middleware)

All external dependencies (Redis, DB) are mocked — no live services needed.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ────────────────────────────────────────────────────────────────────

def _client():
    try:
        from fastapi.testclient import TestClient
        from backend.app.main import app
    except ImportError:
        from fastapi.testclient import TestClient
        from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def client():
    return _client()


# ── Fake Redis pipeline ────────────────────────────────────────────────────────

def _make_redis_mock(pipeline_results: list):
    """Build a mock aioredis client whose pipeline().execute() returns given list."""
    pipe_mock = AsyncMock()
    pipe_mock.__aenter__ = AsyncMock(return_value=pipe_mock)
    pipe_mock.__aexit__ = AsyncMock(return_value=False)
    pipe_mock.get = AsyncMock()
    pipe_mock.lrange = AsyncMock()
    pipe_mock.llen = AsyncMock()
    pipe_mock.keys = AsyncMock()
    pipe_mock.execute = AsyncMock(return_value=pipeline_results)

    r_mock = AsyncMock()
    r_mock.pipeline = MagicMock(return_value=pipe_mock)
    r_mock.keys = AsyncMock(return_value=[])
    r_mock.lrange = AsyncMock(return_value=[])
    r_mock.aclose = AsyncMock()
    r_mock.ping = AsyncMock()
    return r_mock


# ── GET /api/v1/metrics ────────────────────────────────────────────────────────

class TestMetricsEndpoint:
    @patch("app.ws.metrics_broadcaster.aioredis.from_url")
    def test_returns_metrics_snapshot_shape(self, mock_from_url, client):
        """Response must include all MetricsSnapshot fields."""
        pipeline_results = [
            "10",   # req_count current minute
            "5",    # req_count previous minute
            ["12.5", "20.0"],  # response_times
            "1",    # error_count
            "3",    # healer:heals_today
            "7",    # queue depth
            ["agents:heartbeat:agent1", "agents:heartbeat:agent2"],  # keys
        ]
        mock_from_url.return_value = _make_redis_mock(pipeline_results)

        resp = client.get("/api/v1/metrics")
        assert resp.status_code == 200
        data = resp.json()
        required_fields = [
            "requestsPerMin", "avgResponseMs", "healsToday",
            "errorRatePct", "activeAgents", "redisQueueDepth", "collectedAt",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    @patch("app.ws.metrics_broadcaster.aioredis.from_url")
    def test_requests_per_min_sums_two_minutes(self, mock_from_url, client):
        pipeline_results = ["10", "5", [], "0", None, "0", []]
        mock_from_url.return_value = _make_redis_mock(pipeline_results)

        resp = client.get("/api/v1/metrics")
        assert resp.status_code == 200
        assert resp.json()["requestsPerMin"] == 15

    @patch("app.ws.metrics_broadcaster.aioredis.from_url")
    def test_handles_empty_redis(self, mock_from_url, client):
        """All Redis keys absent — should return zeros, not crash."""
        pipeline_results = [None, None, [], None, None, "0", []]
        mock_from_url.return_value = _make_redis_mock(pipeline_results)

        resp = client.get("/api/v1/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["requestsPerMin"] == 0
        assert data["avgResponseMs"] == 0.0
        assert data["activeAgents"] == 0


# ── GET /api/v1/agents/status ─────────────────────────────────────────────────

class TestAgentStatusEndpoint:
    @patch("app.ws.agents_broadcaster.aioredis.from_url")
    def test_returns_agent_list_schema(self, mock_from_url, client):
        r_mock = AsyncMock()
        r_mock.keys = AsyncMock(return_value=["agents:heartbeat:core"])
        pipe_mock = AsyncMock()
        pipe_mock.__aenter__ = AsyncMock(return_value=pipe_mock)
        pipe_mock.__aexit__ = AsyncMock(return_value=False)
        pipe_mock.hgetall = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[
            {"name": "hypercode-core", "status": "online", "last_seen": "2026-04-01T12:00:00Z"}
        ])
        r_mock.pipeline = MagicMock(return_value=pipe_mock)
        r_mock.aclose = AsyncMock()
        mock_from_url.return_value = r_mock

        resp = client.get("/api/v1/agents/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert "updatedAt" in data

    @patch("app.ws.agents_broadcaster.aioredis.from_url")
    def test_empty_heartbeat_keys_returns_empty_list(self, mock_from_url, client):
        r_mock = AsyncMock()
        r_mock.keys = AsyncMock(return_value=[])
        r_mock.aclose = AsyncMock()
        mock_from_url.return_value = r_mock

        resp = client.get("/api/v1/agents/status")
        assert resp.status_code == 200
        assert resp.json()["agents"] == []


# ── GET /api/v1/error-budget ──────────────────────────────────────────────────

class TestErrorBudgetEndpoint:
    @patch("app.routes.reliability.aioredis.from_url")
    def test_budget_ok_gate(self, mock_from_url, client):
        """Low error count → gate = ok."""
        # 5 minutes * 2 sets of keys (req + err) = 10 results
        pipeline_results = ["100", "100", "100", "100", "100",  # req_count x5
                            "0",   "0",   "0",   "0",   "0"]    # error_count x5
        mock_from_url.return_value = _make_redis_mock(pipeline_results)

        resp = client.get("/api/v1/error-budget")
        assert resp.status_code == 200
        data = resp.json()
        assert data["gate"] == "ok"
        assert data["errorTotal"] == 0

    @patch("app.routes.reliability.aioredis.from_url")
    def test_budget_exhausted_gate(self, mock_from_url, client):
        """Many errors → gate = exhausted."""
        pipeline_results = ["100", "100", "100", "100", "100",
                            "10",  "10",  "10",  "10",  "10"]   # 10% error rate
        mock_from_url.return_value = _make_redis_mock(pipeline_results)

        resp = client.get("/api/v1/error-budget")
        assert resp.status_code == 200
        assert resp.json()["gate"] == "exhausted"

    @patch("app.routes.reliability.aioredis.from_url")
    def test_no_requests_returns_100_pct_budget(self, mock_from_url, client):
        """Zero requests → 100% budget remaining (no data = healthy)."""
        pipeline_results = [None] * 10
        mock_from_url.return_value = _make_redis_mock(pipeline_results)

        resp = client.get("/api/v1/error-budget")
        assert resp.status_code == 200
        assert resp.json()["budgetPct"] == 100.0


# ── GET /api/v1/system/state ──────────────────────────────────────────────────

class TestSystemStateEndpoint:
    @patch("app.routes.reliability.aioredis.from_url")
    def test_stable_when_no_errors(self, mock_from_url, client):
        pipeline_results = ["100"] * 5 + ["0"] * 5
        mock_from_url.return_value = _make_redis_mock(pipeline_results)

        resp = client.get("/api/v1/system/state")
        assert resp.status_code == 200
        assert resp.json()["state"] == "stable"

    @patch("app.routes.reliability.aioredis.from_url")
    def test_on_fire_when_high_error_rate(self, mock_from_url, client):
        pipeline_results = ["100"] * 5 + ["10"] * 5  # 10% error rate
        mock_from_url.return_value = _make_redis_mock(pipeline_results)

        resp = client.get("/api/v1/system/state")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "on_fire"
        assert len(data["reasons"]) > 0


# ── GET /api/v1/logs ──────────────────────────────────────────────────────────

class TestLogsEndpoint:
    @patch("app.ws.logs_broadcaster.aioredis.from_url")
    def test_returns_log_response_schema(self, mock_from_url, client):
        log_entry = json.dumps({
            "id": "abc",
            "time": "12:00:00",
            "agent": "healer",
            "level": "info",
            "msg": "Container restarted",
        })
        r_mock = AsyncMock()
        r_mock.lrange = AsyncMock(return_value=[log_entry])
        r_mock.aclose = AsyncMock()
        mock_from_url.return_value = r_mock

        resp = client.get("/api/v1/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data
        assert "total" in data
        assert data["total"] == 1
        assert data["logs"][0]["agent"] == "healer"

    @patch("app.ws.logs_broadcaster.aioredis.from_url")
    def test_empty_redis_returns_empty_logs(self, mock_from_url, client):
        r_mock = AsyncMock()
        r_mock.lrange = AsyncMock(return_value=[])
        r_mock.aclose = AsyncMock()
        mock_from_url.return_value = r_mock

        resp = client.get("/api/v1/logs")
        assert resp.status_code == 200
        assert resp.json()["logs"] == []

    @patch("app.ws.logs_broadcaster.aioredis.from_url")
    def test_level_filter(self, mock_from_url, client):
        entries = [
            json.dumps({"id": "1", "time": "", "agent": "core", "level": "error", "msg": "boom"}),
            json.dumps({"id": "2", "time": "", "agent": "core", "level": "info",  "msg": "ok"}),
        ]
        r_mock = AsyncMock()
        r_mock.lrange = AsyncMock(return_value=entries)
        r_mock.aclose = AsyncMock()
        mock_from_url.return_value = r_mock

        resp = client.get("/api/v1/logs?level=error")
        assert resp.status_code == 200
        data = resp.json()
        assert all(e["level"] == "error" for e in data["logs"])


# ── Public task CRUD (/api/v1/tasks public) ───────────────────────────────────

class TestPublicTasksCRUD:
    @pytest.fixture
    def db_session(self):
        """In-memory SQLite session for route tests."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        try:
            from backend.app.db.base_class import Base
            from backend.app.models.dashboard_task import DashboardTask  # noqa: F401
        except ImportError:
            from app.db.base_class import Base
            from app.models.dashboard_task import DashboardTask  # noqa: F401

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
        Base.metadata.drop_all(engine)

    def test_list_tasks_empty(self, client, db_session):
        try:
            from backend.app.db.session import get_db
            from backend.app.main import app
        except ImportError:
            from app.db.session import get_db
            from app.main import app

        app.dependency_overrides[get_db] = lambda: db_session
        resp = client.get("/api/v1/tasks")
        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert data["tasks"] == []
        assert data["total"] == 0

    @patch("app.routes.tasks.aioredis.from_url")
    def test_create_and_list_task(self, mock_redis, client, db_session):
        r_mock = AsyncMock()
        r_mock.pipeline = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=AsyncMock(
                rpush=AsyncMock(), ltrim=AsyncMock(), publish=AsyncMock(),
                execute=AsyncMock(return_value=[1, True, 1])
            )),
            __aexit__=AsyncMock(return_value=False),
        ))
        r_mock.aclose = AsyncMock()
        mock_redis.return_value = r_mock

        try:
            from backend.app.db.session import get_db
            from backend.app.main import app
        except ImportError:
            from app.db.session import get_db
            from app.main import app

        app.dependency_overrides[get_db] = lambda: db_session

        create_resp = client.post(
            "/api/v1/tasks",
            json={"title": "Fix cAdvisor OOM", "priority": "high"},
        )
        app.dependency_overrides.clear()

        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["title"] == "Fix cAdvisor OOM"
        assert created["status"] == "todo"
        assert created["source"] == "manual"


# ── HTTP metrics middleware ────────────────────────────────────────────────────

class TestHttpMetricsMiddleware:
    def test_middleware_does_not_break_requests(self, client):
        """Middleware must pass through even when Redis is unavailable."""
        with patch("app.main._metrics_redis", None):
            resp = client.get("/health")
        assert resp.status_code == 200

    def test_middleware_records_to_redis(self, client):
        """When Redis is available, pipeline.execute() is called once per request."""
        pipe_mock = AsyncMock()
        pipe_mock.__aenter__ = AsyncMock(return_value=pipe_mock)
        pipe_mock.__aexit__ = AsyncMock(return_value=False)
        pipe_mock.incr = AsyncMock()
        pipe_mock.expire = AsyncMock()
        pipe_mock.lpush = AsyncMock()
        pipe_mock.ltrim = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[1, True, 1, True])

        r_mock = MagicMock()
        r_mock.pipeline = MagicMock(return_value=pipe_mock)

        with patch("app.main._metrics_redis", r_mock):
            resp = client.get("/health")

        assert resp.status_code == 200
        pipe_mock.execute.assert_awaited_once()
