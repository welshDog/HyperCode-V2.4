# HyperFlow Goal Matcher — Design

## Context & Constraints

- HyperFlow (P0-1) flows are hand-authored YAML files under
  `backend/app/agents/hyperflow/flows/`, loaded fresh from disk on every
  request via `available_flows()`. No runtime flow-generation exists today.
- Only 3 flows exist: `hyperflow-smoke`, `implement-new-agent`,
  `safety-demo`. All were human-reviewed via PR before they could run.
- Safety Shepherd integration is already correct: any node can carry a
  `safety:` hint, and `HyperFlowRunner` consults Safety Shepherd
  (ALLOW/BLOCK/ESCALATE) before dispatching that node. This spec does not
  touch that path.
- Evolution Plan Phase 1.3 originally proposed an LLM-driven graph
  compiler (`POST /goals` inventing new node/edge topology at runtime).
  Rejected for v1 as disproportionate risk for the current flow count —
  every hand-authored flow today got human review before first run; a
  generated graph would get none. This spec implements the deterministic
  alternative instead: match a free-text goal to an *existing,
  already-reviewed* flow.

## Goal

Let callers `POST /api/v1/flows/runs` with `{"description": "..."}` instead
of only `{"flow": "name"}`, and get either a confident match to an existing
flow (which then runs exactly as if named explicitly) or a clear `422`
listing candidates — never a silent guess.

## Design

### 1. `FlowDefinition.intent` (new optional field)

`schema.py` gains `intent: str = ""` — a short human-written sentence
describing what the flow is for. Added by hand to the 3 existing YAMLs.
Documentation, not new runtime logic; empty string for any future flow
that doesn't set it (matches on name alone in that case).

### 2. `hyperflow/goal_matcher.py` (new module, pure function)

```python
def match_goal(description: str, flows: dict[str, FlowDefinition]) -> MatchResult
```

- Tokenizes `description` and each flow's `name + " " + intent`
  (lowercase, split on non-alphanumeric, stdlib only — no fuzzy-matching
  dependency).
- Scores by token overlap (Jaccard similarity of token sets).
- `MatchResult`: `flow_name: str | None`, `score: float`,
  `candidates: list[CandidateMatch]` (every flow, always populated, sorted
  by score desc then flow name asc — for consistent presentation whether
  or not a confident match was found).
- Minimum-confidence threshold, env-tunable:
  `HYPERFLOW_MATCH_THRESHOLD` (default `0.4`). Below threshold →
  `flow_name = None`.
- **Tie rule:** if the top two candidates are exactly tied at or above
  threshold, treat as ambiguous → `flow_name = None` even though both
  clear the threshold. Candidate list sorting is a presentation concern
  only; it never silently decides which of two equally-scored flows
  actually runs.

### 3. `POST /flows/runs` extension (existing endpoint, backward-compatible)

- `{"flow": "name"}` — unchanged behavior, exactly as today.
- `{"description": "..."}` — runs `match_goal`; on confident match,
  proceeds via the same `start_flow_run(fd, ...)` call an explicit `flow`
  would use. Response adds `matched_flow` + `match_score` only — the full
  `candidates` list is a 422-only diagnostic, not included on success (a
  successful match doesn't need to explain itself).
- No confident match → `422`:
  ```json
  {
    "error": "no_confident_flow_match",
    "candidates": [
      {"flow": "implement-new-agent", "score": 0.62, "intent": "..."},
      {"flow": "safety-demo", "score": 0.31, "intent": "..."}
    ]
  }
  ```
- Both `flow` and `description` given → explicit `flow` wins;
  `description` is ignored (documented, not silently overridden).

## API Behaviour Summary

| Input | Result |
|---|---|
| `{"flow": "x"}` | Unchanged — runs `x` or 404 if unknown |
| `{"description": "..."}`, confident match | Runs matched flow; response includes `matched_flow`, `match_score` |
| `{"description": "..."}`, no confident match | `422`, candidates listed (sorted, with intent) |
| `{"description": "..."}`, top-2 tied | Treated as no confident match → `422` |
| Both `flow` and `description` | `flow` wins |

## Error Handling

Ambiguous or unrecognized goals fail loud (`422` + candidates). No
silent guessing, no partial/best-effort execution of an uncertain match.

## Testing Plan

**Unit — `goal_matcher.py`** (mirrors `test_hyperflow.py` conventions,
pure function, no DB/Redis):
- Exact keyword match → highest score, wins.
- Partial overlap, above threshold → matches, lower score.
- No overlap → below threshold, `flow_name = None`.
- Exact top-2 tie → `flow_name = None` despite both clearing threshold.
- Candidate list always sorted score desc, then name asc (deterministic
  regardless of dict iteration order).

**Endpoint — `POST /flows/runs`:**
- `{"description": "add a new agent"}` → `200`, `matched_flow =
  "implement-new-agent"`, same internal `start_flow_run` call a matching
  explicit `flow` would trigger.
- `{"description": "do something vague"}` → `422`,
  `error = "no_confident_flow_match"`, candidates present.
- Both `flow` and `description` present → explicit `flow` wins.

## Out of Scope (future, not this spec)

- LLM-assisted matching or generated graph topology — deferred until
  there are enough flows in the wild that keyword matching genuinely
  falls short.
- `intent_keywords: list[str]` as a separate canonical-term field —
  skipped for v1 since tokenizing `intent` already covers it with only 3
  flows to match against; revisit if real usage shows sentence-tokenizing
  misses cases a keyword list would catch.

## Rollout Order

1. Add `intent` to the 3 existing YAML flows.
2. Implement `goal_matcher.py` + unit tests.
3. Extend `POST /flows/runs` to accept `description`.
4. Add endpoint tests.
5. Smoke-test with curl (one matching description, one vague one).
