from __future__ import annotations

import json
from pathlib import Path

from tools.smoke_framework.reporting import (
    CheckResult,
    SmokeSuiteReport,
    write_junit_report,
    write_json_report,
    write_markdown_report,
)


def test_reports_write_files(tmp_path: Path) -> None:
    report = SmokeSuiteReport(
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:00:01Z",
        duration_ms=1000.0,
        environment="dev",
        results=[
            CheckResult(name="a", passed=True, latency_ms=1.23, status_code=200),
            CheckResult(
                name="b", passed=False, latency_ms=4.56, status_code=500, detail="boom"
            ),
        ],
    )

    json_path = tmp_path / "r.json"
    md_path = tmp_path / "r.md"
    junit_path = tmp_path / "r.xml"

    write_json_report(report, json_path)
    write_markdown_report(report, md_path)
    write_junit_report(report, junit_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["environment"] == "dev"
    assert payload["passed"] == 1
    assert payload["failed"] == 1

    md = md_path.read_text(encoding="utf-8")
    assert "| a | PASS |" in md
    assert "| b | FAIL |" in md

    xml = junit_path.read_bytes()
    assert b"testsuite" in xml
