from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.etree.ElementTree import Element, SubElement, tostring


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    latency_ms: Optional[float] = None
    status_code: Optional[int] = None
    detail: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class SmokeSuiteReport:
    started_at: str
    finished_at: str
    duration_ms: float
    environment: str
    results: List[CheckResult]

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def ok(self) -> bool:
        return self.failed == 0


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json_report(report: SmokeSuiteReport, path: Path) -> None:
    payload = {
        "started_at": report.started_at,
        "finished_at": report.finished_at,
        "duration_ms": report.duration_ms,
        "environment": report.environment,
        "passed": report.passed,
        "failed": report.failed,
        "ok": report.ok,
        "results": [
            {
                "name": r.name,
                "passed": r.passed,
                "latency_ms": r.latency_ms,
                "status_code": r.status_code,
                "detail": r.detail,
                "meta": r.meta or {},
            }
            for r in report.results
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_markdown_report(report: SmokeSuiteReport, path: Path) -> None:
    lines = []
    lines.append("# Smoke Suite Report")
    lines.append("")
    lines.append(f"- Environment: {report.environment}")
    lines.append(f"- Started: {report.started_at}")
    lines.append(f"- Finished: {report.finished_at}")
    lines.append(f"- Duration (ms): {report.duration_ms:.2f}")
    lines.append(f"- Passed: {report.passed}")
    lines.append(f"- Failed: {report.failed}")
    lines.append("")
    lines.append("| Check | Result | Latency (ms) | HTTP | Detail |")
    lines.append("|---|---:|---:|---:|---|")
    for r in report.results:
        result = "PASS" if r.passed else "FAIL"
        latency = f"{r.latency_ms:.2f}" if r.latency_ms is not None else ""
        http = str(r.status_code) if r.status_code is not None else ""
        detail = (r.detail or "").replace("\n", " ")
        lines.append(f"| {r.name} | {result} | {latency} | {http} | {detail} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_junit_report(report: SmokeSuiteReport, path: Path) -> None:
    testsuite = Element("testsuite")
    testsuite.set("name", f"smoke:{report.environment}")
    testsuite.set("tests", str(len(report.results)))
    testsuite.set("failures", str(report.failed))
    testsuite.set("time", f"{report.duration_ms / 1000.0:.3f}")

    for r in report.results:
        testcase = SubElement(testsuite, "testcase")
        testcase.set("name", r.name)
        testcase.set("time", f"{(r.latency_ms or 0.0) / 1000.0:.6f}")
        if not r.passed:
            failure = SubElement(testcase, "failure")
            failure.set("message", r.detail or "failed")
            failure.text = r.detail or "failed"

    xml_bytes = tostring(testsuite, encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(xml_bytes)
