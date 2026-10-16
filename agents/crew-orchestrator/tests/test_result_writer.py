"""result_writer: the Duration line of latest-report.md.

Regression: the conditional was written outside the f-string braces, so a run with a duration printed the
literal text `33.21s if duration_seconds else "N/A"`, and a run WITHOUT one raised TypeError
(`{None:.2f}`). Run: pytest agents/crew-orchestrator/tests/test_result_writer.py
"""
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import result_writer  # noqa: E402


def _write(tmp_path, monkeypatch, **kw):
    monkeypatch.setattr(result_writer, "RESULTS_DIR", tmp_path)
    asyncio.run(result_writer.write_execution_results({"status": "completed"}, task_id="t-1", agents=["qa-engineer"], **kw))
    return (tmp_path / "latest-report.md").read_text(encoding="utf-8")


def test_duration_is_formatted_not_left_as_template_text(tmp_path, monkeypatch):
    report = _write(tmp_path, monkeypatch, duration_seconds=33.2149)
    assert "- **Duration:** 33.21s" in report
    assert "if duration_seconds" not in report


def test_missing_duration_renders_na_instead_of_crashing(tmp_path, monkeypatch):
    report = _write(tmp_path, monkeypatch, duration_seconds=None)
    assert "- **Duration:** N/A" in report
    assert "if duration_seconds" not in report
