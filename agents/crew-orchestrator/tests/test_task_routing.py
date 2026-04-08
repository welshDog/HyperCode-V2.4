import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


client = TestClient(app)


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.api_key = None
    settings.agents = {
        "coder": "http://coder:8000",
        "agent_x": "http://agent-x:8000",
    }
    settings.enabled_agent_keys.return_value = list(settings.agents.keys())
    settings.parsed_cors_allow_origins.return_value = ["http://localhost:3000"]
    return settings


def test_task_routes_code_generation_to_coder(mock_settings):
    with patch("main.settings", mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"status": "completed", "result": {"code": "print('ok')"}}
            mock_post.return_value = mock_resp

            resp = client.post(
                "/task",
                json={"id": "t1", "task": "Write a python function", "type": "code_generation"},
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["agent"] == "coder"
            assert mock_post.call_args[0][0] == "http://coder:8000/execute"


def test_task_routes_spawn_agent_to_agent_x(mock_settings):
    with patch("main.settings", mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"status": "submitted"}
            mock_post.return_value = mock_resp

            resp = client.post(
                "/task",
                json={
                    "id": "t2",
                    "type": "spawn_agent",
                    "context": {"description": "Create a tiny agent that greets", "auto_deploy": False},
                },
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["agent"] == "agent-x"
            assert mock_post.call_args[0][0] == "http://agent-x:8000/execute"


def test_task_unknown_type_returns_422(mock_settings):
    with patch("main.settings", mock_settings):
        resp = client.post(
            "/task",
            json={"id": "t3", "task": "do something", "type": "unknown_type"},
        )
    assert resp.status_code == 422

