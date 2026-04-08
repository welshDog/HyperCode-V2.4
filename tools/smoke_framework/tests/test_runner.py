from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import pytest

from tools.smoke_framework.config import SmokeRunConfig
from tools.smoke_framework.runner import SmokeProgressEvent, SmokeSuiteRunner


class FakeRunner(SmokeSuiteRunner):
    def __init__(
        self, config: SmokeRunConfig, responses: Dict[str, tuple[int, str, float]]
    ):
        super().__init__(config)
        self._responses = responses

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> tuple[int, str, float]:
        key = f"{method} {url}"
        if method == "POST" and json_body:
            key = f"{key} {json_body.get('mode', '')}"
        if key not in self._responses:
            raise RuntimeError("missing fake response")
        return self._responses[key]


@pytest.mark.asyncio
async def test_runner_emits_progress_and_report_ok() -> None:
    cfg = SmokeRunConfig(smoke_api_key="x", output_dir="artifacts/smoke-test")
    responses = {
        "GET http://127.0.0.1:8000/health": (200, "ok", 1.0),
        "GET http://127.0.0.1:8081/health": (200, "ok", 1.0),
        "GET http://127.0.0.1:8010/health": (200, "ok", 1.0),
        "GET http://127.0.0.1:8088": (200, "ok", 1.0),
        "GET http://127.0.0.1:8081/tasks": (200, "[]", 1.0),
        "POST http://127.0.0.1:8081/execute/smoke noop": (200, "ok", 1.0),
    }
    runner = FakeRunner(cfg, responses)
    q: asyncio.Queue[SmokeProgressEvent] = asyncio.Queue()
    report = await runner.run(progress_queue=q)
    assert report.ok is True
    assert report.failed == 0


@pytest.mark.asyncio
async def test_runner_failure_propagates_to_report() -> None:
    cfg = SmokeRunConfig(smoke_api_key="x", output_dir="artifacts/smoke-test")
    responses = {
        "GET http://127.0.0.1:8000/health": (500, "bad", 1.0),
        "GET http://127.0.0.1:8081/health": (200, "ok", 1.0),
        "GET http://127.0.0.1:8010/health": (200, "ok", 1.0),
        "GET http://127.0.0.1:8088": (200, "ok", 1.0),
        "GET http://127.0.0.1:8081/tasks": (200, "[]", 1.0),
        "POST http://127.0.0.1:8081/execute/smoke noop": (200, "ok", 1.0),
    }
    runner = FakeRunner(cfg, responses)
    report = await runner.run()
    assert report.ok is False
    assert report.failed == 1


@pytest.mark.asyncio
async def test_request_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    from tools.smoke_framework import runner as runner_mod

    attempts = {"count": 0}

    class Resp:
        def __init__(self, status_code: int, text: str):
            self.status_code = status_code
            self.text = text

    class FakeAsyncClient:
        def __init__(self, timeout: float):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method: str, url: str, headers=None, json=None):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("flaky")
            return Resp(200, "ok")

    monkeypatch.setattr(runner_mod.httpx, "AsyncClient", FakeAsyncClient)

    cfg = SmokeRunConfig(retries=1, retry_backoff_seconds=0.0, concurrency=1)
    runner = SmokeSuiteRunner(cfg)
    status, body, latency = await runner._request("GET", "http://example/health")
    assert status == 200
    assert body == "ok"
    assert attempts["count"] == 2
