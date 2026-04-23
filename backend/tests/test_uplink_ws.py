"""
Phase 10J — CognitiveUplink WebSocket tests
Uses starlette.testclient.TestClient.websocket_connect (sync WS testing).
Tests: ping/pong, execute dispatch, empty command, unknown type, timeout, error.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── helpers ───────────────────────────────────────────────────────────────────

def _crew_ok() -> dict:
    return {"status": "completed", "message": "Workflow finished", "results": {}, "task_id": "t-001"}


def _crew_with_results() -> dict:
    return {
        "status": "completed",
        "message": "Workflow finished",
        "task_id": "t-002",
        "results": {
            "backend-specialist": {"output": "Auth module scaffolded ✅"}
        },
    }


def _make_mock_client(return_value: dict):
    """Build an AsyncMock httpx client that returns the given JSON dict."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = return_value
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


# ── tests ─────────────────────────────────────────────────────────────────────

def test_ping_pong():
    with client.websocket_connect("/ws/uplink") as ws:
        ws.send_text(json.dumps({"type": "ping"}))
        msg = json.loads(ws.receive_text())
    assert msg["type"] == "pong"


def test_execute_dispatches_to_crew():
    mock_client = _make_mock_client(_crew_ok())
    with patch("app.ws.uplink.httpx.AsyncClient", return_value=mock_client):
        with client.websocket_connect("/ws/uplink") as ws:
            ws.send_text(json.dumps({
                "type":    "execute",
                "id":      "test-001",
                "payload": {"command": "build login page"},
            }))
            msg = json.loads(ws.receive_text())

    assert msg["type"] == "response"
    assert len(msg["payload"]) > 0


def test_execute_with_agent_results():
    mock_client = _make_mock_client(_crew_with_results())
    with patch("app.ws.uplink.httpx.AsyncClient", return_value=mock_client):
        with client.websocket_connect("/ws/uplink") as ws:
            ws.send_text(json.dumps({
                "type":    "execute",
                "payload": {"command": "@backend-specialist build auth"},
            }))
            msg = json.loads(ws.receive_text())

    assert msg["type"] == "response"
    assert "backend-specialist" in msg["payload"]
    assert "Auth module" in msg["payload"]


def test_empty_command_returns_error():
    with client.websocket_connect("/ws/uplink") as ws:
        ws.send_text(json.dumps({"type": "execute", "payload": {"command": "   "}}))
        msg = json.loads(ws.receive_text())
    assert msg["type"] == "error"
    assert "empty" in msg["data"].lower()


def test_crew_timeout_returns_error():
    import httpx

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

    with patch("app.ws.uplink.httpx.AsyncClient", return_value=mock_client):
        with client.websocket_connect("/ws/uplink") as ws:
            ws.send_text(json.dumps({"type": "execute", "payload": {"command": "slow task"}}))
            msg = json.loads(ws.receive_text())

    assert msg["type"] == "error"
    assert "time" in msg["data"].lower()  # "timed out" or "timeout"


def test_unknown_message_type_ignored():
    """Unknown types are silently dropped — send ping after to confirm alive."""
    with client.websocket_connect("/ws/uplink") as ws:
        ws.send_text(json.dumps({"type": "subscribe", "channel": "something"}))
        ws.send_text(json.dumps({"type": "ping"}))
        msg = json.loads(ws.receive_text())
    assert msg["type"] == "pong"


def test_invalid_json_returns_error():
    with client.websocket_connect("/ws/uplink") as ws:
        ws.send_text("not valid json {{{")
        msg = json.loads(ws.receive_text())
    assert msg["type"] == "error"
    assert "json" in msg["data"].lower()
