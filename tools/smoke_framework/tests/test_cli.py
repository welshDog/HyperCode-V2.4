from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from tools.smoke_framework.reporting import CheckResult, SmokeSuiteReport


@pytest.mark.asyncio
async def test_cli_writes_reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tools.smoke_framework import cli as cli_mod

    class DummyRunner:
        def __init__(self, config):
            self.config = config

        async def run(self, progress_queue=None):
            if progress_queue is not None:
                await progress_queue.put(cli_mod.SmokeProgressEvent(check="core_health", status="running"))
            return SmokeSuiteReport(
                started_at="2026-01-01T00:00:00Z",
                finished_at="2026-01-01T00:00:01Z",
                duration_ms=1000.0,
                environment="dev",
                results=[CheckResult(name="core_health", passed=True, latency_ms=1.0, status_code=200)],
            )

    monkeypatch.setattr(cli_mod, "SmokeSuiteRunner", DummyRunner)
    monkeypatch.setattr(cli_mod, "_consume_progress", lambda q, json_progress: asyncio.sleep(0))

    monkeypatch.setattr(
        cli_mod.argparse.ArgumentParser,
        "parse_args",
        lambda self: type(
            "Args",
            (),
            {
                "env": "dev",
                "orchestrator_url": "http://127.0.0.1:8081",
                "core_url": "http://127.0.0.1:8000",
                "dashboard_url": "",
                "healer_url": "",
                "smoke_api_key": "x",
                "timeout": 1.0,
                "retries": 0,
                "concurrency": 1,
                "redis_url": "",
                "verify_no_redis_writes": False,
                "skip_task_history_check": True,
                "out_dir": str(tmp_path),
                "json_progress": True,
                "json_logs": True,
            },
        )(),
    )

    exit_code = await cli_mod.main_async()
    assert exit_code == 0
    assert (tmp_path / "smoke_dev.json").exists()
    assert (tmp_path / "smoke_dev.md").exists()
    assert (tmp_path / "smoke_dev.junit.xml").exists()
