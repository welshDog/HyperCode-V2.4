"""P2-1 — Evo Harness unit tests (pure logic). Standalone — no backend conftest,
so it runs fast in the dedicated evo-harness CI job."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import evo_harness  # noqa: E402


def test_classify_status():
    assert evo_harness.classify_status("✅ ALL DONE") == "complete"
    assert evo_harness.classify_status("✅ LIVE — May 7") == "complete"
    assert evo_harness.classify_status("✅ BUILT — May 16 (smoke pending)") == "complete_pending"
    assert evo_harness.classify_status("rated 9.5/10 — backbone complete") == "unknown"
    assert evo_harness.classify_status("TODO") == "unknown"


_ROADMAP = """# Roadmap
| Phase | Name | Status |
|---|---|---|
| 0-9 | Identity + tokens | ✅ ALL DONE |
| 10A | FastAPI | ✅ DONE — April 1 |
| 11 | Mystery track | rated 9.5/10 |
"""


def _write_roadmap():
    fd, path = tempfile.mkstemp(suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(_ROADMAP)
    return path


def test_parse_roadmap_skips_header_and_separator():
    ms = evo_harness.parse_roadmap(_write_roadmap())
    assert len(ms) == 3
    assert ms[0]["phase"] == "0-9"
    assert ms[0]["classification"] == "complete"
    assert ms[2]["classification"] == "unknown"


def test_build_dag_is_linear():
    dag = evo_harness.build_dag(evo_harness.parse_roadmap(_write_roadmap()))
    assert len(dag["nodes"]) == 3
    assert len(dag["edges"]) == 2
    assert dag["nodes"][0]["preconditions"] == []
    assert dag["nodes"][1]["preconditions"] == ["m0"]


def test_scoring_blocks_downstream_of_failure():
    dag = {
        "nodes": [
            {"id": "m0", "phase": "0", "name": "a", "classification": "complete", "preconditions": []},
            {"id": "m1", "phase": "1", "name": "b", "classification": "unknown", "preconditions": ["m0"]},
            {"id": "m2", "phase": "2", "name": "c", "classification": "complete", "preconditions": ["m1"]},
        ],
        "edges": [],
    }
    r = evo_harness.score_milestones(dag)["results"]
    assert r["m0"]["passed"] is True
    assert r["m1"]["passed"] is False
    assert r["m2"]["passed"] is False
    assert r["m2"]["reason"] == "blocked by failed precondition"


def test_scoring_all_green():
    dag = evo_harness.build_dag([
        {"phase": "0", "name": "a", "status": "DONE", "classification": "complete"},
        {"phase": "1", "name": "b", "status": "LIVE", "classification": "complete"},
    ])
    s = evo_harness.score_milestones(dag)["summary"]
    assert s["green"] is True and s["pass_rate"] == 1.0


def test_allow_pending_toggle():
    dag = evo_harness.build_dag([
        {"phase": "0", "name": "a", "status": "BUILT pending", "classification": "complete_pending"},
    ])
    assert evo_harness.score_milestones(dag, allow_pending=True)["summary"]["green"] is True
    assert evo_harness.score_milestones(dag, allow_pending=False)["summary"]["green"] is False


def test_report_has_required_shape():
    report = evo_harness.build_report("check", live=False)
    for key in ("generated_at", "mode", "milestone_count", "dag", "summary", "milestones"):
        assert key in report
