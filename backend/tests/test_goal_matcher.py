from __future__ import annotations

from app.agents.hyperflow.goal_matcher import match_goal
from app.agents.hyperflow.schema import FlowDefinition


def _flow(name: str, intent: str) -> FlowDefinition:
    return FlowDefinition.model_validate(
        {
            "name": name,
            "entry": "a",
            "intent": intent,
            "nodes": [{"id": "a", "type": "tool", "tool": "t"}],
        }
    )


def test_exact_keyword_match_wins(monkeypatch):
    monkeypatch.delenv("HYPERFLOW_MATCH_THRESHOLD", raising=False)
    flows = {
        "implement-new-agent": _flow(
            "implement-new-agent", "design and scaffold a new agent from a spec"
        ),
        "safety-demo": _flow(
            "safety-demo", "demonstrate safety shepherd escalation for a docker action"
        ),
    }
    result = match_goal("design and scaffold a new agent", flows)
    assert result.flow_name == "implement-new-agent"
    assert result.score > 0.5


def test_partial_overlap_above_threshold_matches(monkeypatch):
    monkeypatch.setenv("HYPERFLOW_MATCH_THRESHOLD", "0.2")
    flows = {
        "implement-new-agent": _flow(
            "implement-new-agent", "design and scaffold a new agent from a spec"
        ),
        "safety-demo": _flow(
            "safety-demo", "demonstrate safety shepherd escalation for a docker action"
        ),
    }
    result = match_goal("add a new agent please", flows)
    assert result.flow_name == "implement-new-agent"
    assert 0.0 < result.score < 1.0


def test_no_overlap_returns_none(monkeypatch):
    monkeypatch.delenv("HYPERFLOW_MATCH_THRESHOLD", raising=False)
    flows = {
        "implement-new-agent": _flow(
            "implement-new-agent", "design and scaffold a new agent from a spec"
        ),
    }
    result = match_goal("completely unrelated request about weather", flows)
    assert result.flow_name is None
    assert result.score == 0.0


def test_exact_tie_is_ambiguous(monkeypatch):
    monkeypatch.setenv("HYPERFLOW_MATCH_THRESHOLD", "0.1")
    flows = {
        "flow-a": _flow("flow-a", "process the widget"),
        "flow-b": _flow("flow-b", "process the widget"),
    }
    result = match_goal("process the widget", flows)
    assert result.flow_name is None
    assert {c.flow for c in result.candidates if c.score >= 0.1} == {"flow-a", "flow-b"}


def test_candidates_always_sorted_score_desc_then_name_asc(monkeypatch):
    monkeypatch.delenv("HYPERFLOW_MATCH_THRESHOLD", raising=False)
    flows = {
        "zebra-flow": _flow("zebra-flow", "totally unrelated"),
        "apple-flow": _flow(
            "apple-flow", "design and scaffold a new agent from a spec"
        ),
        "mango-flow": _flow(
            "mango-flow", "design and scaffold a new agent from a spec"
        ),
    }
    result = match_goal("design and scaffold a new agent", flows)
    scores = [c.score for c in result.candidates]
    assert scores == sorted(scores, reverse=True)
    top_two = result.candidates[:2]
    assert [c.flow for c in top_two] == ["apple-flow", "mango-flow"]
