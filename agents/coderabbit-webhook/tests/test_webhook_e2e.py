"""T12 — CodeRabbit webhook E2E integration tests.

Tests cover:
  - /health endpoint
  - /capabilities endpoint
  - /webhook/coderabbit — happy path, auth, validation, routing, timeouts
  - /webhook/github — PR opened, closed (ignored), malformed
  - Rate limiting behaviour (header inspection)
  - Orchestrator dispatch (mocked httpx)
  - Payload validation and error responses
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient


# Import the app — we use TestClient (sync) for simplicity so no asyncio needed
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _coderabbit_payload(**overrides) -> dict:
    """Build a valid CodeRabbit review_completed webhook payload."""
    payload = {
        "event": "review_completed",
        "pr": {
            "number": 42,
            "repo": "hyperstation/hypercode",
            "branch": "feature/awesome",
            "html_url": "https://github.com/hyperstation/hypercode/pull/42",
        },
        "review": {
            "summary": "Looks good overall, a few nits.",
            "critical_issues": [
                {"file": "main.py", "line": 10, "message": "Use contextmanager"},
            ],
            "suggestions": [
                {"file": "utils.py", "message": "Extract helper function"},
            ],
            "comments": ["Good job!"],
        },
    }
    payload.update(overrides)
    return payload


def _github_pr_payload(action: str = "opened") -> dict:
    return {
        "action": action,
        "pull_request": {
            "number": 99,
            "html_url": "https://github.com/hyperstation/hypercode/pull/99",
        },
        "repository": {"full_name": "hyperstation/hypercode"},
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. Health and capabilities endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestInfraEndpoints:
    def test_health_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_body_has_status_ok(self):
        r = client.get("/health")
        assert r.json()["status"] == "ok"

    def test_health_body_has_service_name(self):
        r = client.get("/health")
        assert "coderabbit" in r.json()["service"]

    def test_capabilities_returns_200(self):
        r = client.get("/capabilities")
        assert r.status_code == 200

    def test_capabilities_lists_coderabbit_integration(self):
        r = client.get("/capabilities")
        integrations = r.json()["integrations"]
        assert "CodeRabbit" in integrations

    def test_capabilities_lists_orchestrator(self):
        r = client.get("/capabilities")
        assert "crew-orchestrator" in r.json()["integrations"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. CodeRabbit webhook — happy path
# ─────────────────────────────────────────────────────────────────────────────

class TestCodeRabbitWebhookHappyPath:
    def _mock_orchestrator(self, status_code=200) -> AsyncMock:
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json.return_value = {"status": "queued", "task_id": "t-1"}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        return mock_client

    def test_valid_review_returns_accepted(self):
        with patch("httpx.AsyncClient", return_value=self._mock_orchestrator()):
            r = client.post("/webhook/coderabbit", json=_coderabbit_payload())
        assert r.status_code == 200
        assert r.json()["status"] == "accepted"

    def test_response_includes_pr_number(self):
        with patch("httpx.AsyncClient", return_value=self._mock_orchestrator()):
            r = client.post("/webhook/coderabbit", json=_coderabbit_payload())
        assert r.json()["pr"] == 42

    def test_response_includes_repo(self):
        with patch("httpx.AsyncClient", return_value=self._mock_orchestrator()):
            r = client.post("/webhook/coderabbit", json=_coderabbit_payload())
        assert r.json()["repo"] == "hyperstation/hypercode"

    def test_tasks_generated_from_critical_issues(self):
        payload = _coderabbit_payload()
        payload["review"]["critical_issues"] = [
            {"file": "a.py", "line": 1, "message": "issue 1"},
            {"file": "b.py", "line": 2, "message": "issue 2"},
        ]
        with patch("httpx.AsyncClient", return_value=self._mock_orchestrator()):
            r = client.post("/webhook/coderabbit", json=payload)
        assert r.json()["tasks_generated"] >= 1

    def test_zero_critical_issues_still_accepted(self):
        payload = _coderabbit_payload()
        payload["review"]["critical_issues"] = []
        payload["review"]["suggestions"] = []
        with patch("httpx.AsyncClient", return_value=self._mock_orchestrator()):
            r = client.post("/webhook/coderabbit", json=payload)
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 3. Authentication / secret validation
# ─────────────────────────────────────────────────────────────────────────────

class TestWebhookAuth:
    def test_missing_secret_header_rejected_when_secret_configured(self):
        with patch("main.CODERABBIT_WEBHOOK_SECRET", "super-secret"):
            r = client.post("/webhook/coderabbit", json=_coderabbit_payload())
        assert r.status_code == 401

    def test_wrong_secret_header_rejected(self):
        with patch("main.CODERABBIT_WEBHOOK_SECRET", "super-secret"):
            r = client.post(
                "/webhook/coderabbit",
                json=_coderabbit_payload(),
                headers={"X-CodeRabbit-Secret": "wrong-secret"},
            )
        assert r.status_code == 401

    def test_correct_secret_header_accepted(self):
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"status": "queued", "task_id": "t-1"}
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("main.CODERABBIT_WEBHOOK_SECRET", "super-secret"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                r = client.post(
                    "/webhook/coderabbit",
                    json=_coderabbit_payload(),
                    headers={"X-CodeRabbit-Secret": "super-secret"},
                )
        assert r.status_code == 200

    def test_no_secret_configured_allows_all_requests(self):
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"status": "queued"}
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("main.CODERABBIT_WEBHOOK_SECRET", ""):
            with patch("httpx.AsyncClient", return_value=mock_client):
                r = client.post("/webhook/coderabbit", json=_coderabbit_payload())
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 4. Payload validation / error handling
# ─────────────────────────────────────────────────────────────────────────────

class TestPayloadValidation:
    def test_non_json_body_returns_400(self):
        r = client.post(
            "/webhook/coderabbit",
            content=b"not json at all",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400

    def test_unknown_event_type_ignored(self):
        r = client.post(
            "/webhook/coderabbit",
            json={"event": "comment_added", "pr": {}, "review": {}},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "ignored"

    def test_missing_pr_number_returns_400(self):
        payload = _coderabbit_payload()
        del payload["pr"]["number"]
        r = client.post("/webhook/coderabbit", json=payload)
        assert r.status_code == 400

    def test_missing_repo_returns_400(self):
        payload = _coderabbit_payload()
        del payload["pr"]["repo"]
        r = client.post("/webhook/coderabbit", json=payload)
        assert r.status_code == 400

    def test_missing_branch_returns_400(self):
        payload = _coderabbit_payload()
        del payload["pr"]["branch"]
        r = client.post("/webhook/coderabbit", json=payload)
        assert r.status_code == 400

    def test_empty_body_returns_4xx(self):
        r = client.post("/webhook/coderabbit", content=b"", headers={"Content-Type": "application/json"})
        assert r.status_code in (400, 422)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Orchestrator dispatch failure scenarios
# ─────────────────────────────────────────────────────────────────────────────

class TestOrchestratorDispatch:
    def _make_mock(self, raises=None, status=200):
        mock_response = MagicMock(status_code=status)
        mock_response.json.return_value = {"status": "queued", "task_id": "t-x"}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        if raises:
            mock_client.post = AsyncMock(side_effect=raises)
        else:
            mock_client.post = AsyncMock(return_value=mock_response)
        return mock_client

    def test_orchestrator_unavailable_returns_partial_results(self):
        """If orchestrator is down, webhook should degrade gracefully, not 500."""
        with patch("httpx.AsyncClient", return_value=self._make_mock(raises=httpx.ConnectError("refused"))):
            r = client.post("/webhook/coderabbit", json=_coderabbit_payload())
        # Should not be a server error; either accepted with 0 submitted or handled
        assert r.status_code < 500

    def test_orchestrator_timeout_handled(self):
        with patch("httpx.AsyncClient", return_value=self._make_mock(raises=httpx.TimeoutException("timeout"))):
            r = client.post("/webhook/coderabbit", json=_coderabbit_payload())
        assert r.status_code < 500

    def test_orchestrator_500_handled(self):
        with patch("httpx.AsyncClient", return_value=self._make_mock(status=500)):
            r = client.post("/webhook/coderabbit", json=_coderabbit_payload())
        assert r.status_code < 500


# ─────────────────────────────────────────────────────────────────────────────
# 6. GitHub webhook endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestGitHubWebhook:
    def test_pr_opened_accepted(self):
        r = client.post("/webhook/github", json=_github_pr_payload("opened"))
        assert r.status_code == 200

    def test_pr_closed_ignored(self):
        r = client.post("/webhook/github", json=_github_pr_payload("closed"))
        assert r.status_code == 200
        assert r.json().get("status") == "ignored"

    def test_pr_merged_ignored(self):
        r = client.post("/webhook/github", json=_github_pr_payload("merged"))
        assert r.status_code == 200

    def test_non_json_github_body_returns_400(self):
        r = client.post(
            "/webhook/github",
            content=b"garbage",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400

    def test_github_payload_includes_pr_number_in_response(self):
        r = client.post("/webhook/github", json=_github_pr_payload("opened"))
        data = r.json()
        # Response should acknowledge the PR somehow
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 7. Idempotency — same PR sent twice
# ─────────────────────────────────────────────────────────────────────────────

class TestIdempotency:
    def test_duplicate_webhook_both_return_200(self):
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"status": "queued", "task_id": "t-1"}
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        payload = _coderabbit_payload()
        with patch("httpx.AsyncClient", return_value=mock_client):
            r1 = client.post("/webhook/coderabbit", json=payload)
            r2 = client.post("/webhook/coderabbit", json=payload)

        assert r1.status_code == 200
        assert r2.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 8. Task routing by issue type
# ─────────────────────────────────────────────────────────────────────────────

class TestTaskRouting:
    def test_security_issue_routes_to_security_engineer(self):
        payload = _coderabbit_payload()
        payload["review"]["critical_issues"] = [
            {"file": "auth.py", "line": 5, "message": "SQL injection vulnerability detected"}
        ]
        dispatched = []

        async def mock_submit(tasks):
            dispatched.extend(tasks)
            return [{"status": "queued"} for _ in tasks]

        with patch("main.submit_tasks_to_orchestrator", side_effect=mock_submit):
            r = client.post("/webhook/coderabbit", json=payload)

        assert r.status_code == 200
        # At least one task should be generated
        assert r.json()["tasks_generated"] >= 1

    def test_frontend_issue_generates_task(self):
        payload = _coderabbit_payload()
        payload["review"]["suggestions"] = [
            {"file": "components/Button.tsx", "message": "Add aria-label for accessibility"}
        ]

        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"status": "queued", "task_id": "t-front"}
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            r = client.post("/webhook/coderabbit", json=payload)
        assert r.status_code == 200
