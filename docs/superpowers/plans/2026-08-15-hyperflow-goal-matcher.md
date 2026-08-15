# HyperFlow Goal Matcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `POST /api/v1/flows/runs` accept `{"description": "..."}` as an alternative to `{"flow": "name"}`, deterministically matching the goal to an existing, already-reviewed flow — or failing loud with a 422 and candidates, never guessing.

**Architecture:** A pure token-overlap (Jaccard) matcher scores a free-text description against each flow's `name + intent`. On a confident, unique match, the request proceeds through the exact same `start_flow_run` path an explicit `{"flow": "name"}` call would use — zero changes to `HyperFlowRunner` or the Safety Shepherd integration. No match, or an exact tie at the top, fails as `422`.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, pytest (stdlib `re` for tokenizing — no new dependencies).

**Spec:** `docs/superpowers/specs/2026-08-15-hyperflow-goal-matcher-design.md`

## Global Constraints

- Backward-compatible: `{"flow": "name"}` behavior is byte-for-byte unchanged.
- Zero changes to `hyperflow_runner.py` or Safety Shepherd integration.
- Matching is deterministic keyword overlap only — no LLM call, no new flow-graph topology invented at runtime.
- Threshold is env-tunable: `HYPERFLOW_MATCH_THRESHOLD` (default `0.4`).
- An exact tie between the top two candidates is ambiguous → treated as no match, even if both clear the threshold.
- Candidate lists (when returned) are always sorted score descending, then flow name ascending.
- A successful match response includes only `matched_flow` + `match_score` — the full `candidates` list is 422-only.
- No new dependencies (stdlib `re` for tokenizing; no fuzzy-matching library).

---

### Task 1: `intent` field on `FlowDefinition` + populate the 3 existing flows

**Files:**
- Modify: `backend/app/agents/hyperflow/schema.py:91-96` (`FlowDefinition` class)
- Modify: `backend/app/agents/hyperflow/flows/hyperflow_smoke.yml`
- Modify: `backend/app/agents/hyperflow/flows/implement_new_agent.yml`
- Modify: `backend/app/agents/hyperflow/flows/safety_demo.yml`
- Test: `backend/tests/test_hyperflow.py`

**Interfaces:**
- Produces: `FlowDefinition.intent: str` (default `""`) — consumed by Task 2's matcher.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_hyperflow.py` (near the existing `# ── schema ──` tests):

```python
def test_all_registered_flows_declare_intent():
    for name, fd in available_flows_for_test().items():
        assert fd.intent, f"flow '{name}' has no intent — needed for goal matching"
```

This needs `available_flows` imported — add to the existing import line at the top of the file:

```python
from app.agents.hyperflow.registry import FLOWS_DIR, available_flows, get_flow
```

Then define the small local wrapper right above the new test (keeps the test file's existing flat style, no fixture needed):

```python
def available_flows_for_test():
    return available_flows()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd HyperCode-V2.4 && python -m pytest backend/tests/test_hyperflow.py::test_all_registered_flows_declare_intent -v`
Expected: FAIL — `AttributeError: 'FlowDefinition' object has no attribute 'intent'` (field doesn't exist yet).

- [ ] **Step 3: Add the `intent` field to the schema**

In `backend/app/agents/hyperflow/schema.py`, in the `FlowDefinition` class:

```python
class FlowDefinition(BaseModel):
    name: str
    version: int = 1
    entry: str
    intent: str = ""
    nodes: list[FlowNode]
    edges: list[FlowEdge] = Field(default_factory=list)
```

(Only the new `intent: str = ""` line is added, right after `entry: str`.)

- [ ] **Step 4: Populate `intent` on the 3 existing flow YAMLs**

`backend/app/agents/hyperflow/flows/hyperflow_smoke.yml` — add after `entry: ready`:

```yaml
intent: "Deterministic smoke test of the flow control plane using approval gates only, no external dependencies"
```

`backend/app/agents/hyperflow/flows/implement_new_agent.yml` — add after `entry: design_spec`:

```yaml
intent: "Design and scaffold a new agent from a spec, verify health"
```

`backend/app/agents/hyperflow/flows/safety_demo.yml` — add after `entry: risky_action`:

```yaml
intent: "Demonstrate Safety Shepherd escalation and approval for a privileged docker action"
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd HyperCode-V2.4 && python -m pytest backend/tests/test_hyperflow.py -v`
Expected: PASS — all existing tests plus the new one green (existing tests must stay green; this is a purely additive field with a default, so nothing else should break).

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/hyperflow/schema.py backend/app/agents/hyperflow/flows/*.yml backend/tests/test_hyperflow.py
git commit -m "feat: add intent field to FlowDefinition, populate existing flows"
```

---

### Task 2: `goal_matcher.py` — pure token-overlap matcher

**Files:**
- Create: `backend/app/agents/hyperflow/goal_matcher.py`
- Test: `backend/tests/test_goal_matcher.py`

**Interfaces:**
- Consumes: `FlowDefinition` (`.name`, `.intent`) from Task 1.
- Produces:
  - `match_goal(description: str, flows: dict[str, FlowDefinition]) -> MatchResult`
  - `MatchResult(flow_name: str | None, score: float, candidates: list[CandidateMatch])`
  - `CandidateMatch(flow: str, score: float, intent: str)`
  - Consumed by Task 3's endpoint.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_goal_matcher.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd HyperCode-V2.4 && python -m pytest backend/tests/test_goal_matcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.agents.hyperflow.goal_matcher'`.

- [ ] **Step 3: Implement the matcher**

Create `backend/app/agents/hyperflow/goal_matcher.py`:

```python
"""Deterministic free-text goal → existing-flow matcher.

Token-overlap (Jaccard) scoring only — never invents new flow topology.
A goal either confidently matches one existing, already-reviewed flow, or
it doesn't match at all. See docs/superpowers/specs/2026-08-15-hyperflow-goal-matcher-design.md.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from app.agents.hyperflow.schema import FlowDefinition

_TOKEN_RE = re.compile(r"[a-z0-9]+")
DEFAULT_THRESHOLD = 0.4


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def _match_threshold() -> float:
    raw = os.getenv("HYPERFLOW_MATCH_THRESHOLD", str(DEFAULT_THRESHOLD))
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_THRESHOLD


@dataclass
class CandidateMatch:
    flow: str
    score: float
    intent: str


@dataclass
class MatchResult:
    flow_name: str | None
    score: float
    candidates: list[CandidateMatch] = field(default_factory=list)


def match_goal(description: str, flows: dict[str, FlowDefinition]) -> MatchResult:
    """Match a free-text goal to the best existing flow.

    Returns flow_name=None when nothing clears HYPERFLOW_MATCH_THRESHOLD
    (default 0.4), or when the top two candidates are exactly tied —
    a tie is ambiguous and must never be silently broken by execution.
    Candidates are always sorted score desc, then flow name asc.
    """
    goal_tokens = _tokenize(description)

    candidates = [
        CandidateMatch(
            flow=name,
            score=_jaccard(goal_tokens, _tokenize(f"{fd.name} {fd.intent}")),
            intent=fd.intent,
        )
        for name, fd in flows.items()
    ]
    candidates.sort(key=lambda c: (-c.score, c.flow))

    if not candidates:
        return MatchResult(flow_name=None, score=0.0, candidates=candidates)

    threshold = _match_threshold()
    if candidates[0].score < threshold:
        return MatchResult(flow_name=None, score=0.0, candidates=candidates)

    if len(candidates) > 1 and candidates[0].score == candidates[1].score:
        return MatchResult(flow_name=None, score=candidates[0].score, candidates=candidates)

    top = candidates[0]
    return MatchResult(flow_name=top.flow, score=top.score, candidates=candidates)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd HyperCode-V2.4 && python -m pytest backend/tests/test_goal_matcher.py -v`
Expected: PASS — all 5 tests green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/hyperflow/goal_matcher.py backend/tests/test_goal_matcher.py
git commit -m "feat: add deterministic goal-to-flow matcher"
```

---

### Task 3: Extend `POST /flows/runs` to accept `description`

**Files:**
- Modify: `backend/app/api/v1/endpoints/flows.py:52-66` (`create_run`)
- Test: `backend/tests/test_flows_endpoint.py` (new file — the existing `test_hyperflow.py` covers schema/runner directly, not this endpoint over HTTP)

**Interfaces:**
- Consumes: `match_goal(description, flows) -> MatchResult` from Task 2; `available_flows()`, `get_flow(name)` from `app.agents.hyperflow.registry` (already imported in `flows.py`); `start_flow_run(fd, run_id, *, user_id=None)` from `app.agents.hyperflow_runner` (already imported).
- Produces: `POST /api/v1/flows/runs` now accepts `{"description": "..."}` in addition to `{"flow": "name"}`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_flows_endpoint.py`:

```python
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.api import deps
from app.main import app


def _authed():
    def _fake_user():
        return SimpleNamespace(id=1, is_superuser=False)

    app.dependency_overrides[deps.get_current_active_user] = _fake_user


def test_description_matches_and_runs_flow(client):
    _authed()
    try:
        with patch(
            "app.api.v1.endpoints.flows.start_flow_run",
            new=AsyncMock(return_value=None),
        ) as mock_start:
            resp = client.post(
                "/api/v1/flows/runs",
                json={"description": "design and scaffold a new agent"},
            )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["flow"] == "implement-new-agent"
    assert body["matched_flow"] == "implement-new-agent"
    assert 0.0 < body["match_score"] <= 1.0
    mock_start.assert_awaited_once()
    called_flow = mock_start.await_args.args[0]
    assert called_flow.name == "implement-new-agent"


def test_vague_description_returns_422_with_candidates(client):
    _authed()
    try:
        resp = client.post(
            "/api/v1/flows/runs",
            json={"description": "completely unrelated weather forecast request"},
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error"] == "no_confident_flow_match"
    assert len(detail["candidates"]) >= 1
    assert all({"flow", "score", "intent"} <= set(c.keys()) for c in detail["candidates"])


def test_explicit_flow_wins_over_description(client):
    _authed()
    try:
        with patch(
            "app.api.v1.endpoints.flows.start_flow_run",
            new=AsyncMock(return_value=None),
        ) as mock_start:
            resp = client.post(
                "/api/v1/flows/runs",
                json={
                    "flow": "hyperflow-smoke",
                    "description": "design and scaffold a new agent",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["flow"] == "hyperflow-smoke"
    assert "matched_flow" not in body
    called_flow = mock_start.await_args.args[0]
    assert called_flow.name == "hyperflow-smoke"


def test_neither_flow_nor_description_returns_422(client):
    _authed()
    try:
        resp = client.post("/api/v1/flows/runs", json={})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd HyperCode-V2.4 && python -m pytest backend/tests/test_flows_endpoint.py -v`
Expected: FAIL — `test_description_matches_and_runs_flow` and `test_vague_description_returns_422_with_candidates` fail with `422 'flow' is required` (current code only accepts `flow`); `test_explicit_flow_wins_over_description` may pass already (harmless, `description` is just an unused extra key today — that's fine, it'll still pass after the change); `test_neither_flow_nor_description_returns_422` should already pass today too.

- [ ] **Step 3: Extend the endpoint**

In `backend/app/api/v1/endpoints/flows.py`:

Add the import (alongside the existing `hyperflow_runner` import block):

```python
from app.agents.hyperflow.goal_matcher import match_goal
```

Replace the `create_run` function body:

```python
@router.post("/runs")
async def create_run(
    payload: dict,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    name = payload.get("flow")
    description = payload.get("description")

    if not name and not description:
        raise HTTPException(status_code=422, detail="'flow' or 'description' is required")

    match_score: float | None = None
    if not name:
        result = match_goal(description, available_flows())
        if result.flow_name is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "no_confident_flow_match",
                    "candidates": [
                        {"flow": c.flow, "score": c.score, "intent": c.intent}
                        for c in result.candidates
                    ],
                },
            )
        name = result.flow_name
        match_score = result.score

    fd = get_flow(name)
    if fd is None:
        raise HTTPException(status_code=404, detail=f"Unknown flow '{name}'")

    run_id = str(uuid.uuid4())
    await start_flow_run(fd, run_id, user_id=getattr(current_user, "id", None))
    response: dict[str, Any] = {"run_id": run_id, "flow": fd.name, "status": "running"}
    if match_score is not None:
        response["matched_flow"] = fd.name
        response["match_score"] = match_score
    return response
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd HyperCode-V2.4 && python -m pytest backend/tests/test_flows_endpoint.py backend/tests/test_hyperflow.py backend/tests/test_goal_matcher.py -v`
Expected: PASS — all tests across all three files green (confirms Task 3 didn't regress Tasks 1-2).

- [ ] **Step 5: Manual smoke test**

With the backend running locally (`uvicorn app.main:app --reload` or via the usual dev stack), confirm real end-to-end behavior:

```bash
curl -X POST http://localhost:8000/api/v1/flows/runs \
  -H "Authorization: Bearer <a real test token>" \
  -H "Content-Type: application/json" \
  -d '{"description": "design and scaffold a new agent"}'
# Expect: 200, {"run_id": "...", "flow": "implement-new-agent", "matched_flow": "implement-new-agent", "match_score": ...}

curl -X POST http://localhost:8000/api/v1/flows/runs \
  -H "Authorization: Bearer <a real test token>" \
  -H "Content-Type: application/json" \
  -d '{"description": "book a flight to mars"}'
# Expect: 422, {"detail": {"error": "no_confident_flow_match", "candidates": [...]}}
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/endpoints/flows.py backend/tests/test_flows_endpoint.py
git commit -m "feat: accept free-text description on POST /flows/runs"
```

---

## Self-Review Notes

- **Spec coverage:** `intent` field (Task 1), matcher module + threshold + tie rule (Task 2), endpoint extension + backward-compat + 422 shape (Task 3), full testing plan from the spec (unit matcher tests in Task 2, endpoint tests in Task 3), manual curl smoke test (Task 3 Step 5). No spec section without a task.
- **Placeholder scan:** no TBD/TODO; every step has real code, not descriptions of code.
- **Type consistency:** `MatchResult`/`CandidateMatch` field names (`flow_name`, `score`, `candidates`, `flow`, `intent`) are identical between Task 2's implementation and Task 3's consumption. `start_flow_run(fd, run_id, *, user_id=...)` signature matches the existing one in `hyperflow_runner.py` — unchanged, just called from a new branch.
