# BROski `hypercode.recover` Phase 2a Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Plan-mode note:** this file was written while plan mode was active. After approval, copy it verbatim to `docs/superpowers/plans/2026-09-27-broski-recover-2a.md` on branch `feature/broski-recover-2a` and commit it (`docs: BROski recover 2a implementation plan`) before dispatching Task 1.

**Goal:** Add `hypercode.recover` — a zero-mutation operator tool that diagnoses broken containers with deterministic rules, proposes exactly one allow-listed restart, shows a superuser the exact plan with a `plan_hash`, and seals the approved plan (with the recorded approver and a Governance Ledger row) for the future governed executor (2b).

**Architecture:** New flow `operator-recover` = `inspect → propose → approve(gate) → seal`, run by the existing HyperFlow runner as in-core "local tools". Candidate selection is pure code over read-only Docker socket-proxy GETs (no LLM, no Docker write). Generic runner/API extensions: local tools receive a context (`run_id`, `history`), a gate can show a prior node's data and bind approval to a `plan_hash`, and the approver identity is recorded on the completed gate entry.

**Tech Stack:** Python 3.13 / FastAPI / SQLAlchemy (Postgres prod, SQLite tests) / httpx / pytest (`asyncio.run` style) / FastMCP.

**Spec:** `docs/superpowers/specs/2026-09-27-broski-recover-design.md` (committed `0eb5a206` on `feature/broski-recover-2a`). Refinement decided while planning (record in Task 7): `/input` requires `plan_hash` for **approvals** only; a **reject** needs no hash (safe direction).

## Global Constraints

- Work on branch `feature/broski-recover-2a` in `H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4`. Commit prefixes `feat:`/`fix:`/`docs:`/`test:`. Every commit message ends with `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`. `git add <exact files>` only. **No push and no PR without Bro's say-so.** Never merge.
- Python: 4-space indent; imports `from app.X import Y`, never `from backend.app.X`. `backend/app/agents/hyperflow_runner.py` is **CRLF** — keep its line endings, small diffs only (whole-file churn is a defect).
- **No mutation in 2a:** no Docker write call anywhere; only `GET` through `settings.DOCKER_SOCKET_PROXY_URL` (the read-only proxy). No LLM in the plan path. No Shepherd/Governor changes.
- Default-deny eligibility; the never-list beats the allow-list and the label. Never-list: `hypercode-core, postgres, redis, docker-socket-proxy, docker-socket-proxy-build, docker-socket-proxy-healer, safety-shepherd, governor, fleet-controller, crew-orchestrator, hypercode-mcp-server, hypercode-ollama, agent-registry, healer-agent`. Allow-list: `agent-focus-tracker, agent-hyper-brain-core, agent-mcp-bridge, agent-morning-briefing, broski-bot, chroma, coder-studio, evolve-relay, github-sync, github-sync-brain, hyper-brain, hyperhealth-worker, memstream, obsidian-watcher, skillweaver`. `celery-worker` and `hypercode-dashboard` are undecided = **not eligible** (Bro confirms in review). Opt-in label: `hypercode.recover=restartable` (exact value).
- Approvals stay superuser-human-only; agent keys can start/read/cancel but never approve; decisions are gate-scoped. Arguments must be `{}`.
- `plan_hash` format `"sha256:" + hexdigest` over `json.dumps(plan, sort_keys=True, separators=(",", ":"))` (same rule as `agents/fleet-controller/models.py:canonical_hash`).
- Evidence text is scrubbed (`scrub_text`) and capped; no env vars or raw inspect blobs are stored. `result.data` and `result.context` are operator-API only: they must be stripped from the unauthenticated legacy `/flows` GETs and Redis payloads.
- Tests: from `backend/`: `python -m pytest <files> -q -p no:cacheprovider --no-cov`; only the files named in the task, never the whole suite (RAM). New runner tests use the autouse fixture `SAFETY_SHEPHERD_MODE=off` and no network.
- Live phase (Task 7) follows the Phase 1 RAM rules: `available` (never `free`) >= 1.2 GB always, >= 1.5 GB before build/recreate; build only the services that changed; `up -d --no-deps`; never `--force-recreate`; never `docker compose config`; stop if core stays unhealthy past the healthcheck retry window, restarts unexpectedly, `/health` fails after the ~2 min startup allowance, or available RAM < 1.2 GB. Record `StartedAt`, first good `/health`, final health, restart count, min available RAM. Lean Operations Mode stays on: observability stopped, no other mutation.

## Review Focus

1. **A stale/wrong `plan_hash` can never approve**, and `seal` re-verifies the hash and the recorded approver (Tasks 3, 4, 5).
2. **A container stopped on purpose is never proposed** (exit 0/143), while an OOM-killed one (exit 137 + `OOMKilled`) is (Task 2).
3. **Never-list beats allow-list and label** (Task 1).
4. **`context`/`data` never leak** through unauthenticated legacy GETs or Redis (Task 3).
5. **Docker unreachable / malformed Docker JSON** yields a structured "nothing proposed" report, never an exception (Tasks 2, 5).
6. **Container ids are validated** before being placed in a URL path (Task 5).
7. **A ledger failure never blocks the seal**, but a hash/approver failure always fails the run (Task 5).

## File Structure

| File | Responsibility |
|---|---|
| `backend/app/broski_operator/recover_policy.py` (create) | never/allow lists, label rule, `classify` |
| `backend/app/broski_operator/recover.py` (create) | pure logic: candidate rules, evidence, ranking, dependents, plan + `plan_hash`, report, `scrub_text` |
| `backend/app/broski_operator/recover_tools.py` (create) | local tools `recover_propose` / `recover_seal` (Docker GETs, cooldown read, ledger write) |
| `backend/app/broski_operator/tools.py` (modify) | tool signature `(params, ctx)`; use `scrub_text`; register the two recover tools |
| `backend/app/agents/hyperflow_runner.py` (modify) | tool ctx, `success_key` surfacing, gate `show_from`/`plan_hash`, approver evidence, strip `context` |
| `backend/app/api/v1/endpoints/operator_tasks.py` (modify) | expose gate context + `plan_hash`; require matching `plan_hash` on approve |
| `backend/app/broski_operator/runs.py` (modify) | `store_decision(..., plan_hash=None)` |
| `backend/app/api/v1/endpoints/flows.py` (modify) | legacy `_public_history` also strips `context` |
| `backend/app/broski_operator/catalog.py` (modify) | `hypercode.recover` → `operator-recover` |
| `backend/app/agents/hyperflow/flows/operator_recover.yml` (create) | the flow |
| `services/hypercode-mcp-server/server.py` (modify) | `hypercode_recover` MCP tool |
| `scripts/prove-recover.py` (create) | live proof (runs inside core) |
| `backend/tests/test_recover_*.py`, `test_operator_gate_context.py` (create); a few existing operator tests (modify: tool signature) | tests |

---

### Task 1: Restart policy (`recover_policy.py`)

**Files:**
- Create: `backend/app/broski_operator/recover_policy.py`
- Test: `backend/tests/test_recover_policy.py`

**Interfaces:**
- Produces: `NEVER_LIST: frozenset[str]`, `ALLOW_LIST: frozenset[str]`, `RESTARTABLE_LABEL = "hypercode.recover"`, `RESTARTABLE_LABEL_VALUE = "restartable"`.
- Produces: `@dataclass(frozen=True) Eligibility(allowed: bool, basis: Optional[str] = None, blocked_by: Optional[str] = None)` with `as_dict() -> {"allowed","basis","blocked_by"}`.
- Produces: `classify(name: str, labels: Optional[Mapping[str, str]] = None) -> Eligibility`.

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_recover_policy.py`

```python
"""BROski recover — restart eligibility policy (default-deny)."""

import pytest

from app.broski_operator.recover_policy import (
    ALLOW_LIST,
    NEVER_LIST,
    RESTARTABLE_LABEL,
    Eligibility,
    classify,
)

LABEL = {RESTARTABLE_LABEL: "restartable"}


@pytest.mark.parametrize("name", sorted(NEVER_LIST))
def test_never_list_always_blocked_even_with_label(name):
    assert classify(name).blocked_by == "never_list"
    elig = classify(name, LABEL)  # Review focus 3: label cannot override the never-list
    assert elig.allowed is False and elig.blocked_by == "never_list"


@pytest.mark.parametrize("name", sorted(ALLOW_LIST))
def test_allow_list_eligible(name):
    assert classify(name) == Eligibility(True, "allow_list", None)


def test_label_opt_in():
    assert classify("zz-recover-proof", LABEL) == Eligibility(True, "label", None)


def test_wrong_label_value_is_not_eligible():
    elig = classify("zz-x", {RESTARTABLE_LABEL: "true"})
    assert elig == Eligibility(False, None, "not_allowlisted")


def test_unknown_and_undecided_are_default_deny():
    for name in ("celery-worker", "hypercode-dashboard", "something-new"):
        assert classify(name) == Eligibility(False, None, "not_allowlisted")


def test_lists_are_disjoint():
    assert NEVER_LIST.isdisjoint(ALLOW_LIST)


def test_as_dict_shape():
    assert classify("skillweaver").as_dict() == {
        "allowed": True, "basis": "allow_list", "blocked_by": None,
    }
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_recover_policy.py -q -p no:cacheprovider --no-cov`
Expected: FAIL (`ModuleNotFoundError: app.broski_operator.recover_policy`).

- [ ] **Step 3: Implement** — `backend/app/broski_operator/recover_policy.py`

```python
"""Which containers `hypercode.recover` may propose restarting (default-deny).

Pure policy — no Docker, no IO. The never-list always wins over the allow-list and the
opt-in label. Undecided containers (e.g. celery-worker, hypercode-dashboard) are NOT eligible
until Bro decides.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

RESTARTABLE_LABEL = "hypercode.recover"
RESTARTABLE_LABEL_VALUE = "restartable"

# Recovery infrastructure, data stores, safety/governance and the operator's own entry points.
NEVER_LIST = frozenset(
    {
        "hypercode-core",
        "postgres",
        "redis",
        "docker-socket-proxy",
        "docker-socket-proxy-build",
        "docker-socket-proxy-healer",
        "safety-shepherd",
        "governor",
        "fleet-controller",
        "crew-orchestrator",
        "hypercode-mcp-server",
        "hypercode-ollama",
        "agent-registry",
        "healer-agent",
    }
)

ALLOW_LIST = frozenset(
    {
        "agent-focus-tracker",
        "agent-hyper-brain-core",
        "agent-mcp-bridge",
        "agent-morning-briefing",
        "broski-bot",
        "chroma",
        "coder-studio",
        "evolve-relay",
        "github-sync",
        "github-sync-brain",
        "hyper-brain",
        "hyperhealth-worker",
        "memstream",
        "obsidian-watcher",
        "skillweaver",
    }
)


@dataclass(frozen=True)
class Eligibility:
    allowed: bool
    basis: Optional[str] = None       # "allow_list" | "label"
    blocked_by: Optional[str] = None  # "never_list" | "not_allowlisted"

    def as_dict(self) -> dict:
        return {"allowed": self.allowed, "basis": self.basis, "blocked_by": self.blocked_by}


def classify(name: str, labels: Optional[Mapping[str, str]] = None) -> Eligibility:
    if name in NEVER_LIST:
        return Eligibility(False, None, "never_list")
    if name in ALLOW_LIST:
        return Eligibility(True, "allow_list", None)
    if (labels or {}).get(RESTARTABLE_LABEL) == RESTARTABLE_LABEL_VALUE:
        return Eligibility(True, "label", None)
    return Eligibility(False, None, "not_allowlisted")
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && python -m pytest tests/test_recover_policy.py -q -p no:cacheprovider --no-cov`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/broski_operator/recover_policy.py backend/tests/test_recover_policy.py
git commit -m "feat: hypercode.recover restart eligibility policy (default-deny)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Candidate logic, evidence, plan hash (`recover.py`)

**Files:**
- Create: `backend/app/broski_operator/recover.py`
- Modify: `backend/app/broski_operator/tools.py` (`_safe_error` uses the new `scrub_text`)
- Test: `backend/tests/test_recover_core.py`

**Interfaces:**
- Consumes (Task 1): `classify`, `Eligibility.as_dict()`.
- Produces (all pure unless marked async):
  - `MAX_DETAIL = 10`, `PLAN_VERSION = 1`
  - `scrub_text(msg: str) -> str` (URL userinfo → `://***@`, `password=`/`passwd=` values → `***`)
  - `reason_from_summary(summary: dict) -> Optional[str]` → `"unhealthy" | "restarting" | "crashed" | "needs_detail" | None`
  - `build_evidence(summary: dict, detail: Optional[dict]) -> dict`
  - `dependents_of(summary: dict, summaries: list[dict]) -> Optional[list[str]]`
  - `async gather_candidates(summaries: list[dict], get_detail: Callable[[str], Awaitable[Optional[dict]]]) -> list[dict]` — candidate dict keys: `container, state, reason, evidence, eligibility, dependents`
  - `canonical_json(obj) -> str`, `evidence_digest(evidence) -> str`, `build_plan(candidate, run_id) -> dict`, `plan_hash(plan) -> str`
  - `build_report(candidates: list[dict], run_id: str, notes: list[str]) -> dict` with keys `ok, has_proposal, proposal, candidates, not_eligible, notes` (`proposal = {"plan", "plan_hash", "summary"}` or `None`)

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_recover_core.py`

```python
"""BROski recover — pure candidate/evidence/plan logic."""

import asyncio

from app.broski_operator import recover


def S(name, state, status, labels=None, cid=None):
    return {"Id": cid or (name.replace("-", "")[:12].ljust(12, "0")), "Names": ["/" + name],
            "State": state, "Status": status, "Labels": labels or {}}


def D(oom=False, exit_code=0, probes=("boom",), restarts=2):
    return {
        "RestartCount": restarts,
        "State": {"OOMKilled": oom, "ExitCode": exit_code, "StartedAt": "s", "FinishedAt": "f",
                  "Health": {"Status": "unhealthy", "Log": [{"Output": p} for p in probes]}},
    }


def test_reason_from_summary_table():
    r = recover.reason_from_summary
    assert r(S("a", "running", "Up 2 hours (unhealthy)")) == "unhealthy"
    assert r(S("a", "running", "Up 2 hours (healthy)")) is None
    assert r(S("a", "restarting", "Restarting (1) 5 seconds ago")) == "restarting"
    assert r(S("a", "exited", "Exited (1) 3 hours ago")) == "crashed"
    assert r(S("a", "exited", "Exited (139) 3 hours ago")) == "crashed"
    # Review focus 2: stopped on purpose is never a candidate
    assert r(S("a", "exited", "Exited (0) 3 hours ago")) is None
    assert r(S("a", "exited", "Exited (143) 3 hours ago")) is None
    # 137 is SIGKILL: could be OOM or a `docker stop` escalation -> needs the detail
    assert r(S("a", "exited", "Exited (137) 3 hours ago")) == "needs_detail"
    assert r(S("a", "exited", "weird status")) is None
    assert r({}) is None


def _gather(summaries, details):
    async def get_detail(cid):
        return details.get(cid)
    return asyncio.run(recover.gather_candidates(summaries, get_detail))


def test_gather_137_only_when_oom_killed():
    oom = S("agent-mcp-bridge", "exited", "Exited (137) 1 hour ago", cid="aaaaaaaaaaaa")
    stopped = S("memstream", "exited", "Exited (137) 1 hour ago", cid="bbbbbbbbbbbb")
    out = _gather([oom, stopped], {"aaaaaaaaaaaa": D(oom=True, exit_code=137),
                                   "bbbbbbbbbbbb": D(oom=False, exit_code=137)})
    assert [c["container"] for c in out] == ["agent-mcp-bridge"]
    assert out[0]["reason"] == "crashed" and out[0]["evidence"]["oom_killed"] is True


def test_gather_137_with_no_detail_is_excluded():
    s = S("agent-mcp-bridge", "exited", "Exited (137) 1 hour ago", cid="aaaaaaaaaaaa")
    assert _gather([s], {}) == []


def test_gather_ranks_unhealthy_then_restarting_then_crashed():
    sums = [
        S("zz-crashed", "exited", "Exited (1) 1 hour ago", cid="c1c1c1c1c1c1"),
        S("zz-restarting", "restarting", "Restarting (1) 2s ago", cid="c2c2c2c2c2c2"),
        S("zz-unhealthy", "running", "Up 1 hour (unhealthy)", cid="c3c3c3c3c3c3"),
    ]
    out = _gather(sums, {})
    assert [c["reason"] for c in out] == ["unhealthy", "restarting", "crashed"]


def test_gather_caps_detail_lookups():
    sums = [S(f"zz-{i:02d}", "running", "Up (unhealthy)", cid=f"{i:012x}") for i in range(15)]
    calls = []

    async def get_detail(cid):
        calls.append(cid)
        return D()

    out = asyncio.run(recover.gather_candidates(sums, get_detail))
    assert len(calls) == recover.MAX_DETAIL and len(out) == 15


def test_eligibility_is_attached_and_never_list_wins():
    sums = [S("hypercode-core", "running", "Up (unhealthy)", labels={"hypercode.recover": "restartable"},
              cid="d1d1d1d1d1d1"),
            S("skillweaver", "running", "Up (unhealthy)", cid="d2d2d2d2d2d2")]
    out = {c["container"]: c for c in _gather(sums, {})}
    assert out["hypercode-core"]["eligibility"]["blocked_by"] == "never_list"
    assert out["skillweaver"]["eligibility"]["allowed"] is True


def test_evidence_caps_probes_clips_and_scrubs():
    long = "x" * 500
    detail = D(probes=("one", "two", "redis://:hunter2@cache:6379 failed", "password=abc123 " + long))
    ev = recover.build_evidence(S("a", "running", "Up (unhealthy)"), detail)
    assert len(ev["health_probes"]) == 3            # last 3 only
    joined = " ".join(ev["health_probes"])
    assert "hunter2" not in joined and "abc123" not in joined
    assert all(len(p) <= 200 for p in ev["health_probes"])
    assert ev["restart_count"] == 2 and ev["oom_killed"] is False


def test_evidence_without_detail_uses_summary_only():
    ev = recover.build_evidence(S("a", "restarting", "Restarting (1) 2s ago"), None)
    assert ev["state"] == "restarting" and ev["health_probes"] == [] and ev["restart_count"] is None


def test_scrub_text():
    assert "hunter2" not in recover.scrub_text("redis://:hunter2@cache:6379/0")
    assert "abc" not in recover.scrub_text("PASSWORD=abc")


def test_plan_hash_is_canonical_stable_and_run_bound():
    cand = {"container": "skillweaver", "reason": "unhealthy", "evidence": {"a": 1, "b": 2}}
    p1 = recover.build_plan(cand, "run-1")
    p2 = recover.build_plan({**cand, "evidence": {"b": 2, "a": 1}}, "run-1")
    assert recover.plan_hash(p1) == recover.plan_hash(p2)          # key order does not matter
    assert recover.plan_hash(p1).startswith("sha256:") and len(recover.plan_hash(p1)) == 7 + 64
    assert recover.plan_hash(recover.build_plan(cand, "run-2")) != recover.plan_hash(p1)   # run-bound
    assert recover.plan_hash({**p1, "target": "other"}) != recover.plan_hash(p1)           # tamper-evident
    assert p1["version"] == 1 and p1["action"] == "restart" and p1["target"] == "skillweaver"


def test_dependents_from_compose_labels():
    target = S("redis", "running", "Up", labels={"com.docker.compose.service": "redis"})
    others = [
        S("a", "running", "Up", labels={"com.docker.compose.service": "a",
                                         "com.docker.compose.depends_on": "redis:service_healthy:false,db:service_started:false"}),
        S("b", "running", "Up", labels={"com.docker.compose.service": "b",
                                         "com.docker.compose.depends_on": "db:service_started:false"}),
    ]
    assert recover.dependents_of(target, [target] + others) == ["a"]
    assert recover.dependents_of(target, [target]) is None  # no depends_on labels anywhere -> unknown


def test_build_report_picks_first_eligible_and_lists_the_rest():
    cands = [
        {"container": "hypercode-core", "state": "running", "reason": "unhealthy", "evidence": {},
         "eligibility": {"allowed": False, "basis": None, "blocked_by": "never_list"}},
        {"container": "skillweaver", "state": "running", "reason": "unhealthy", "evidence": {"x": 1},
         "eligibility": {"allowed": True, "basis": "allow_list", "blocked_by": None}},
    ]
    rep = recover.build_report(cands, "run-9", ["note"])
    assert rep["ok"] is True and rep["has_proposal"] is True
    assert rep["proposal"]["plan"]["target"] == "skillweaver"
    assert rep["proposal"]["plan_hash"] == recover.plan_hash(rep["proposal"]["plan"])
    assert rep["not_eligible"] == ["hypercode-core: never_list"] and rep["notes"] == ["note"]


def test_build_report_with_nothing_to_recover():
    rep = recover.build_report([], "run-9", [])
    assert rep["has_proposal"] is False and rep["proposal"] is None and rep["candidates"] == []
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_recover_core.py -q -p no:cacheprovider --no-cov`
Expected: FAIL (`ModuleNotFoundError: app.broski_operator.recover`).

- [ ] **Step 3: Implement** — `backend/app/broski_operator/recover.py`

```python
"""Pure logic for `hypercode.recover` (Phase 2a): candidate rules, evidence, plan + plan_hash.

No IO in this module except the injected ``get_detail`` coroutine in ``gather_candidates``.
Nothing here can mutate Docker. Container ids are only ever passed to ``get_detail``.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Awaitable, Callable, Optional

from app.broski_operator.recover_policy import classify

MAX_DETAIL = 10
PLAN_VERSION = 1
_PROBES = 3
_PROBE_CAP = 200
_MAX_DEPENDENTS = 20
_QUIET_EXITS = {0, 143}          # clean stop / SIGTERM: stopped on purpose, never a candidate
_KILLED_EXIT = 137               # SIGKILL: OOM or a `docker stop` escalation -> needs detail
_RANK = {"unhealthy": 0, "restarting": 1, "crashed": 2}
_EXITED = re.compile(r"Exited \((\d+)\)")


def scrub_text(msg: str) -> str:
    """Remove URL userinfo and password= fragments from free text."""
    msg = re.sub(r"://[^/\s@]*@", "://***@", msg or "")
    return re.sub(r"(?i)\b(password|passwd)=\S+", r"\1=***", msg)


def _name(summary: dict[str, Any]) -> str:
    return ((summary.get("Names") or ["?"])[0] or "?").lstrip("/")


def reason_from_summary(summary: dict[str, Any]) -> Optional[str]:
    state = summary.get("State")
    status = summary.get("Status") or ""
    if state == "restarting":
        return "restarting"
    if state == "running" and "(unhealthy)" in status:
        return "unhealthy"
    if state == "exited":
        m = _EXITED.search(status)
        if not m:
            return None
        code = int(m.group(1))
        if code in _QUIET_EXITS:
            return None
        if code == _KILLED_EXIT:
            return "needs_detail"
        return "crashed"
    return None


def build_evidence(summary: dict[str, Any], detail: Optional[dict[str, Any]]) -> dict[str, Any]:
    st = (detail or {}).get("State") or {}
    health = st.get("Health") or {}
    probes = [
        scrub_text(str(p.get("Output") or ""))[:_PROBE_CAP]
        for p in (health.get("Log") or [])[-_PROBES:]
    ]
    return {
        "state": summary.get("State"),
        "status": scrub_text(str(summary.get("Status") or ""))[:80],
        "exit_code": st.get("ExitCode"),
        "oom_killed": bool(st.get("OOMKilled")),
        "restart_count": (detail or {}).get("RestartCount"),
        "started_at": st.get("StartedAt"),
        "finished_at": st.get("FinishedAt"),
        "health_status": health.get("Status"),
        "health_probes": probes,
    }


def dependents_of(summary: dict[str, Any], summaries: list[dict[str, Any]]) -> Optional[list[str]]:
    """Containers whose compose `depends_on` label names this container's service.

    Returns None when no container carries a depends_on label (dependents unknown).
    """
    service = (summary.get("Labels") or {}).get("com.docker.compose.service")
    any_label = False
    out: list[str] = []
    for other in summaries:
        dep = (other.get("Labels") or {}).get("com.docker.compose.depends_on")
        if dep is None:
            continue
        any_label = True
        wanted = {part.split(":", 1)[0] for part in dep.split(",") if part}
        if service and service in wanted and _name(other) != _name(summary):
            out.append(_name(other))
    if not any_label:
        return None
    return sorted(out)[:_MAX_DEPENDENTS]


def rank_key(candidate: dict[str, Any]) -> tuple[int, str]:
    return (_RANK.get(candidate["reason"], 9), candidate["container"])


async def gather_candidates(
    summaries: list[dict[str, Any]],
    get_detail: Callable[[str], Awaitable[Optional[dict[str, Any]]]],
) -> list[dict[str, Any]]:
    pre = []
    for s in summaries:
        reason = reason_from_summary(s)
        if reason is not None:
            pre.append((s, reason))
    pre.sort(key=lambda t: _name(t[0]))
    out: list[dict[str, Any]] = []
    looked_up = 0
    for s, reason in pre:
        detail = None
        if looked_up < MAX_DETAIL:
            detail = await get_detail(s.get("Id", ""))
            looked_up += 1
        if reason == "needs_detail":
            if not ((detail or {}).get("State") or {}).get("OOMKilled"):
                continue  # SIGKILL without an OOM signature = stopped on purpose
            reason = "crashed"
        name = _name(s)
        out.append(
            {
                "container": name,
                "state": s.get("State"),
                "reason": reason,
                "evidence": build_evidence(s, detail),
                "eligibility": classify(name, s.get("Labels") or {}).as_dict(),
                "dependents": dependents_of(s, summaries),
            }
        )
    out.sort(key=rank_key)
    return out


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def evidence_digest(evidence: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(evidence).encode()).hexdigest()


def build_plan(candidate: dict[str, Any], run_id: str) -> dict[str, Any]:
    return {
        "version": PLAN_VERSION,
        "action": "restart",
        "target": candidate["container"],
        "reason": candidate["reason"],
        "evidence_digest": evidence_digest(candidate["evidence"]),
        "run_id": run_id,
    }


def plan_hash(plan: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(plan).encode()).hexdigest()


def build_report(candidates: list[dict[str, Any]], run_id: str, notes: list[str]) -> dict[str, Any]:
    eligible = [c for c in candidates if c["eligibility"]["allowed"]]
    proposal = None
    if eligible:
        plan = build_plan(eligible[0], run_id)
        proposal = {
            "plan": plan,
            "plan_hash": plan_hash(plan),
            "summary": f"restart {plan['target']}: {plan['reason']}",
        }
    return {
        "ok": True,
        "has_proposal": proposal is not None,
        "proposal": proposal,
        "candidates": candidates,
        "not_eligible": [
            f"{c['container']}: {c['eligibility']['blocked_by']}"
            for c in candidates
            if not c["eligibility"]["allowed"]
        ],
        "notes": notes,
    }
```

- [ ] **Step 4: Make `_safe_error` reuse `scrub_text`** — in `backend/app/broski_operator/tools.py`, add the import and replace the two `re.sub` lines in `_safe_error`:

```python
from app.broski_operator.recover import scrub_text
```

```python
    msg = scrub_text(str(exc))
    return f"{type(exc).__name__}: {msg[:120]}" if msg else type(exc).__name__
```

(Leave the `import re` line if other code still uses it; remove only if now unused.)

- [ ] **Step 5: Run to verify pass, plus the existing tools tests**

Run: `cd backend && python -m pytest tests/test_recover_core.py tests/test_operator_tools.py -q -p no:cacheprovider --no-cov`
Expected: all PASS (the scrubber behavior of `_safe_error` is unchanged).

- [ ] **Step 6: Commit**

```bash
git add backend/app/broski_operator/recover.py backend/app/broski_operator/tools.py backend/tests/test_recover_core.py
git commit -m "feat: hypercode.recover pure candidate/evidence/plan-hash logic

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Runner — tool context, gate context/`plan_hash`, approver evidence

**Files:**
- Modify: `backend/app/agents/hyperflow_runner.py` (CRLF!), `backend/app/broski_operator/tools.py` (`inspect_stack` + `LOCAL_TOOLS` type), `backend/app/api/v1/endpoints/flows.py` (`_public_history`)
- Modify (test stubs): `backend/tests/test_operator_tools.py` (any stub `async def X(params)` registered in `tools.LOCAL_TOOLS` becomes `async def X(params, ctx=None)`; `inspect_stack({})` calls become `inspect_stack({}, {})`)
- Test: `backend/tests/test_operator_gate_context.py`

**Interfaces:**
- Consumes (Task 2): nothing new.
- Produces: local tools are called as `await LOCAL_TOOLS[name](node.params, ctx)` with `ctx = {"run_id": str, "history": list[dict]}`; `LOCAL_TOOLS: dict[str, Callable[[dict, dict], Awaitable[dict]]]`.
- Produces: the local-tool wrapper result also carries `result[node.success_key] = data[node.success_key]` when present.
- Produces: a gate with `params.show_from: <node_id>` emits an `awaiting_approval` entry with `result = {"prompt", "context": <that node's last completed data>, "plan_hash"?: context["proposal"]["plan_hash"]}`.
- Produces: the runner keeps `self._last_decision_meta = {"by", "plan_hash"}` (set by `_take_persisted_decision` when it consumes a dict decision); the completed gate entry's `result` gains `approved`, `by`, `plan_hash` (only keys that are not None).
- Produces: `_strip_data` (Redis) and `flows._public_history` (legacy GET) drop **both** `data` and `context` from `result`.

- [ ] **Step 1: Update existing stubs** in `backend/tests/test_operator_tools.py`: every fake local tool becomes `async def _fake(params, ctx=None): ...` (the ones named `_fake`, `_red`, `_raises`, and the second `_fake` near the ordering test); `test_inspect_*` calls `asyncio.run(tools.inspect_stack({}))` become `asyncio.run(tools.inspect_stack({}, {}))`. Run `cd backend && python -m pytest tests/test_operator_tools.py -q -p no:cacheprovider --no-cov` after Step 6 to confirm they still pass.

- [ ] **Step 2: Write the failing tests** — `backend/tests/test_operator_gate_context.py`

```python
"""BROski recover — generic runner support: tool ctx, gate show_from/plan_hash, approver evidence."""

import asyncio

import pytest

from app.agents.hyperflow.schema import FlowDefinition
from app.agents.hyperflow_runner import HyperFlowRunner, _strip_data
from app.broski_operator import tools
from app.models.hyperflow import HyperFlowRunStatus
from tests.test_hyperflow import _runner_with_io


@pytest.fixture(autouse=True)
def _safety_off(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "off")
    monkeypatch.setattr("app.agents.hyperflow_runner.APPROVAL_POLL_SECONDS", 0.01)


def _flow():
    return FlowDefinition.model_validate(
        {
            "name": "ctxflow",
            "entry": "propose",
            "nodes": [
                {"id": "propose", "type": "tool", "tool": "local.fake_propose", "success_key": "has_proposal"},
                {"id": "approve", "type": "human_approval_gate",
                 "params": {"prompt": "ok?", "show_from": "propose"}},
                {"id": "seal", "type": "tool", "tool": "local.fake_seal"},
            ],
            "edges": [
                {"from": "propose", "to": "approve", "condition": True},
                {"from": "approve", "to": "seal"},
            ],
        }
    )


PROPOSAL = {"ok": True, "has_proposal": True,
            "proposal": {"plan": {"target": "skillweaver"}, "plan_hash": "sha256:abc", "summary": "s"}}


def _register(monkeypatch, has_proposal=True, seen=None):
    async def fake_propose(params, ctx):
        if seen is not None:
            seen["ctx"] = ctx
        return dict(PROPOSAL, has_proposal=has_proposal)

    async def fake_seal(params, ctx):
        if seen is not None:
            seen["seal_history"] = ctx["history"]
        return {"ok": True, "sealed": True}

    monkeypatch.setitem(tools.LOCAL_TOOLS, "local.fake_propose", fake_propose)
    monkeypatch.setitem(tools.LOCAL_TOOLS, "local.fake_seal", fake_seal)


def test_tools_receive_run_id_and_history_ctx(monkeypatch):
    seen = {}
    _register(monkeypatch, seen=seen)
    runner, final = _runner_with_io(_flow(), "ctx-run", monkeypatch)
    monkeypatch.setattr(runner, "_take_persisted_decision", lambda *_: True)
    asyncio.run(runner._run())
    assert seen["ctx"]["run_id"] == "ctx-run" and isinstance(seen["ctx"]["history"], list)
    assert final["status"] is HyperFlowRunStatus.COMPLETED
    assert any(e["node"] == "propose" for e in seen["seal_history"])


def test_success_key_is_surfaced_so_conditional_edge_works(monkeypatch):
    _register(monkeypatch, has_proposal=False)
    runner, final = _runner_with_io(_flow(), "sk-run", monkeypatch)
    asyncio.run(runner._run())
    assert final["status"] is HyperFlowRunStatus.COMPLETED
    assert [e["node"] for e in runner._history] == ["propose"]  # no gate: edge condition false


def test_gate_shows_context_and_plan_hash(monkeypatch):
    _register(monkeypatch)
    runner, final = _runner_with_io(_flow(), "gate-run", monkeypatch)

    async def scenario():
        runner._task = asyncio.create_task(runner._run())
        await asyncio.sleep(0.1)
        assert runner.parked_gate == "approve"
        runner.resume(True)
        await runner._task

    monkeypatch.setattr(runner, "_take_persisted_decision", lambda *_: None)
    asyncio.run(scenario())
    awaiting = [e for e in runner._history if e["status"] == "awaiting_approval"][0]
    assert awaiting["result"]["prompt"] == "ok?"
    assert awaiting["result"]["context"]["proposal"]["plan_hash"] == "sha256:abc"
    assert awaiting["result"]["plan_hash"] == "sha256:abc"


def test_completed_gate_records_approver_and_plan_hash(monkeypatch):
    _register(monkeypatch)
    runner, final = _runner_with_io(_flow(), "who-run", monkeypatch)

    def take(node_id=None):
        runner._last_decision_meta = {"by": "bro@example.com", "plan_hash": "sha256:abc"}
        return True

    monkeypatch.setattr(runner, "_take_persisted_decision", take)
    asyncio.run(runner._run())
    gate_done = [e for e in runner._history if e["node"] == "approve" and e["status"] == "completed"][0]
    assert gate_done["result"]["approved"] is True
    assert gate_done["result"]["by"] == "bro@example.com"
    assert gate_done["result"]["plan_hash"] == "sha256:abc"


def test_gate_without_show_from_is_unchanged(monkeypatch):
    from tests.operator_helpers import gate_flow

    runner, final = _runner_with_io(gate_flow(), "plain", monkeypatch)
    monkeypatch.setattr(runner, "_take_persisted_decision", lambda *_: True)
    asyncio.run(runner._run())
    awaiting = [e for e in runner._history if e["status"] == "awaiting_approval"][0]
    assert awaiting["result"] == {"prompt": "ok?"}


def test_strip_data_drops_data_and_context():
    entry = {"node": "n", "result": {"success": True, "data": {"a": 1}, "context": {"b": 2}, "plan_hash": "h"}}
    out = _strip_data(entry)
    assert out["result"] == {"success": True, "plan_hash": "h"}
    assert "data" in entry["result"] and "context" in entry["result"]  # original not mutated


def test_take_persisted_decision_records_meta(hf_db):
    from app.models.hyperflow import HyperFlowRun

    s = hf_db()
    s.add(HyperFlowRun(id="m1", flow_name="g", flow_version=1, status="awaiting_approval",
                       current_node="gate",
                       state={"history": [], "context": {"pending_decision": {
                           "approved": True, "by": "bro", "ts": "t", "node": "gate", "plan_hash": "sha256:z"}}}))
    s.commit()
    s.close()
    from tests.operator_helpers import gate_flow

    runner = HyperFlowRunner(gate_flow(), "m1")
    assert runner._take_persisted_decision("gate") is True
    assert runner._last_decision_meta == {"by": "bro", "plan_hash": "sha256:z"}
```

Also add to `backend/tests/test_flows_endpoint.py` (or the file holding the existing `result.data` legacy test) one test that a seeded run whose history entry has `result.context` returns no `context` from the unauthenticated `GET /api/v1/flows/runs/{id}` (copy the shape of the existing data-stripping test).

- [ ] **Step 3: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_operator_gate_context.py -q -p no:cacheprovider --no-cov`
Expected: FAIL (`TypeError`/missing behavior: tools called with one arg, no `_last_decision_meta`, no gate context).

- [ ] **Step 4: Implement in `backend/app/agents/hyperflow_runner.py`** (keep CRLF)

4a. In `__init__`, after `self.parked_gate: Optional[str] = None ...` add:

```python
        self._last_decision_meta: dict[str, Any] = {}  # {"by", "plan_hash"} of the last consumed decision
```

4b. Replace `_run_local_tool`:

```python
    async def _run_local_tool(self, node: FlowNode) -> dict[str, Any]:
        """Run an in-core tool. No orchestrator hop and no mocked-OK fallback."""
        ctx = {"run_id": self.run_id, "history": list(self._history)}
        data = await LOCAL_TOOLS[node.tool](node.params, ctx)
        ok = bool(data.get("ok"))
        result: dict[str, Any] = {"ok": ok, "green": ok, "data": data}
        if node.success_key in data:
            # Lets a node's `success_key` (e.g. has_proposal) drive conditional edges.
            result[node.success_key] = data[node.success_key]
        return result
```

4c. Add a helper directly above `_take_persisted_decision`:

```python
    def _last_tool_data(self, node_id: str) -> Optional[dict[str, Any]]:
        """`result.data` of the most recent completed entry of ``node_id`` (or None)."""
        for entry in reversed(self._history):
            if entry.get("node") == node_id and entry.get("status") == "completed":
                data = (entry.get("result") or {}).get("data")
                return data if isinstance(data, dict) else None
        return None
```

4d. In `_take_persisted_decision`, right before the final `return bool(decision.get("approved"))` (after `db.commit()`), record the meta:

```python
            self._last_decision_meta = {
                "by": decision.get("by"),
                "plan_hash": decision.get("plan_hash"),
            }
```

4e. Replace the start of `_await_approval` (from `self._approval_event.clear()` through the `_emit(... awaiting ...)` call) with:

```python
        self._approval_event.clear()
        self._approval_result = None
        self._last_decision_meta = {}
        prompt = node.params.get("prompt", f"Approve step '{node.id}'?")
        entry_result: dict[str, Any] = {"prompt": prompt}
        show_from = node.params.get("show_from")
        if show_from:
            shown = self._last_tool_data(str(show_from))
            if shown is not None:
                entry_result["context"] = shown
                plan_hash = (shown.get("proposal") or {}).get("plan_hash")
                if plan_hash:
                    entry_result["plan_hash"] = plan_hash
        await self._emit(node, "awaiting_approval", entry_result,
                         HyperFlowRunStatus.AWAITING_APPROVAL)
```

4f. Replace the final `return {"ok": True, "approved": True}` of `_await_approval` with:

```python
        out: dict[str, Any] = {"ok": True, "approved": True}
        for key in ("by", "plan_hash"):
            if self._last_decision_meta.get(key):
                out[key] = self._last_decision_meta[key]
        return out
```

4g. In `_run`, in the emit block right after the `if node.type is NodeType.TOOL and node.tool in LOCAL_TOOLS and "data" in result:` lines, add:

```python
                if node.type is NodeType.HUMAN_APPROVAL_GATE:
                    for key in ("approved", "by", "plan_hash"):
                        if result.get(key) is not None:
                            emit_result[key] = result[key]
```

4h. Replace `_strip_data`:

```python
def _strip_data(entry: dict[str, Any]) -> dict[str, Any]:
    """Copy of a history entry without ``result.data``/``result.context`` (operator-API only)."""
    result = entry.get("result")
    if isinstance(result, dict) and ("data" in result or "context" in result):
        return {**entry, "result": {k: v for k, v in result.items() if k not in ("data", "context")}}
    return entry
```

- [ ] **Step 5: Implement the other two edits**

`backend/app/broski_operator/tools.py`: change `inspect_stack(params: dict[str, Any])` to `inspect_stack(params: dict[str, Any], ctx: dict[str, Any] | None = None)` (body unchanged) and the registry annotation to `dict[str, Callable[[dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]]]]`.

`backend/app/api/v1/endpoints/flows.py` `_public_history`: strip both keys:

```python
def _public_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """History copy without ``result.data``/``result.context`` (operator API only)."""
    out: list[dict[str, Any]] = []
    for entry in history:
        result = entry.get("result") if isinstance(entry, dict) else None
        if isinstance(result, dict) and ("data" in result or "context" in result):
            entry = {**entry, "result": {k: v for k, v in result.items() if k not in ("data", "context")}}
        out.append(entry)
    return out
```

- [ ] **Step 6: Run to verify pass, plus the existing runner/operator suites**

Run: `cd backend && python -m pytest tests/test_operator_gate_context.py tests/test_operator_tools.py tests/test_operator_runner.py tests/test_operator_durable_approval.py tests/test_operator_api.py tests/test_hyperflow.py tests/test_flows_endpoint.py -q -p no:cacheprovider --no-cov` (background it; ~3 min)
Expected: all PASS. Confirm `git diff --stat` shows a small diff for `hyperflow_runner.py` (no whole-file line-ending churn).

- [ ] **Step 7: Commit**

```bash
git add backend/app/agents/hyperflow_runner.py backend/app/broski_operator/tools.py backend/app/api/v1/endpoints/flows.py backend/tests/test_operator_gate_context.py backend/tests/test_operator_tools.py backend/tests/test_flows_endpoint.py
git commit -m "feat: runner tool context, gate show_from/plan_hash, recorded approver

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Operator API — expose gate context, require matching `plan_hash`

**Files:**
- Modify: `backend/app/api/v1/endpoints/operator_tasks.py`, `backend/app/broski_operator/runs.py`
- Test: `backend/tests/test_operator_plan_hash.py`

**Interfaces:**
- Consumes (Task 3): the awaiting gate entry's `result.context` / `result.plan_hash`.
- Produces: `GET /operator/tasks/{id}` while parked at a gate with a hash returns `inputRequests.approval.context` and `.plan_hash` (plus existing `node`, `question`, `options`).
- Produces: `POST /operator/tasks/{id}/input`: when the parked gate entry has a `plan_hash` and the decision is `approve`: body `plan_hash` missing → 422 `{"error":"plan_hash_required"}`; not a string → 422; mismatch → 409 `{"error":"plan_hash_mismatch"}`. `reject` needs no hash. The stored pending decision includes `plan_hash` when sent.
- Produces: `store_decision(db, run, *, approved, by, node, plan_hash: Optional[str] = None)`.

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_operator_plan_hash.py` (reuse the patterns and helpers from `tests/test_operator_api.py`: `client`/`db` fixtures, the `_as()` principal override, a `_seed` that writes a `HyperFlowRun`; copy those three small helpers into this file). The seeded run uses flow `operator-inspect`?? **No — use `hyperflow-smoke`** (catalog flow) with `current_node="ready"` and this history:

```python
GATE_HASH = "sha256:" + "a" * 64
HIST = [{"node": "ready", "type": "human_approval_gate", "status": "awaiting_approval",
         "result": {"prompt": "Approve?", "plan_hash": GATE_HASH,
                    "context": {"proposal": {"plan_hash": GATE_HASH, "summary": "restart x"}}}}]
```

Tests (each `_as()` = superuser human; run seeded `awaiting_approval`):
1. `test_get_exposes_context_and_plan_hash`: `GET` → `inputRequests.approval.plan_hash == GATE_HASH` and `.context.proposal.summary == "restart x"`.
2. `test_approve_requires_plan_hash`: `POST {"decision":"approve"}` → 422 with `detail.error == "plan_hash_required"`; row has no `pending_decision`.
3. `test_approve_with_wrong_hash_409`: `{"decision":"approve","plan_hash":"sha256:"+"b"*64}` → 409 `plan_hash_mismatch`; nothing stored.
4. `test_approve_with_non_string_hash_422`: `{"plan_hash": 5}` → 422.
5. `test_approve_with_right_hash_stores_it`: right hash → 200; `db.expire_all()`; `run.state["context"]["pending_decision"]["plan_hash"] == GATE_HASH` and `["node"] == "ready"`.
6. `test_reject_needs_no_hash`: `{"decision":"reject"}` → 200 and stored `approved is False`.
7. `test_gate_without_plan_hash_unchanged`: a seeded gate entry with only `{"prompt": "Approve?"}` → approve without hash → 200 (Phase 1 behavior).
8. `test_agent_key_still_403` and `test_non_superuser_still_403` (copy the two existing assertions with the new body).

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_operator_plan_hash.py -q -p no:cacheprovider --no-cov`
Expected: FAIL (context not exposed; approve without hash accepted).

- [ ] **Step 3: Implement**

`runs.py` — extend `store_decision`:

```python
def store_decision(
    db: Session,
    run: HyperFlowRun,
    *,
    approved: bool,
    by: str,
    node: Optional[str],
    plan_hash: Optional[str] = None,
) -> bool:
    """... (keep the existing docstring)"""
    state = dict(run.state or {})
    ctx = dict(state.get("context") or {})
    if "pending_decision" in ctx:
        return False
    decision = {"approved": approved, "by": by, "ts": _now(), "node": node}
    if plan_hash is not None:
        decision["plan_hash"] = plan_hash
    ctx["pending_decision"] = decision
    state["context"] = ctx
    run.state = state
    db.commit()
    return True
```

`operator_tasks.py` — add a helper next to `_parked_gate`:

```python
def _gate_entry(run: HyperFlowRun) -> dict[str, Any]:
    """The awaiting_approval history entry for the gate the run is parked at (or {})."""
    history = (run.state or {}).get("history", [])
    return history[-1] if history and _parked_gate(run) is not None else {}
```

In `_approval_request`, replace the returned dict for the gate case with:

```python
    entry_result = _gate_entry(run).get("result") or {}
    approval: dict[str, Any] = {
        "node": gate,
        "question": prompt,
        "options": ["approve", "reject"],
    }
    if entry_result.get("context") is not None:
        approval["context"] = entry_result["context"]
    if entry_result.get("plan_hash"):
        approval["plan_hash"] = entry_result["plan_hash"]
    return {"kind": "approval", "approval": approval}
```

In `submit_input`, after the `wanted_node` validation add:

```python
    sent_hash = payload.get("plan_hash")
    if sent_hash is not None and not isinstance(sent_hash, str):
        raise HTTPException(status_code=422, detail="'plan_hash' must be a string")
```

then after the `gate_mismatch` check and before `approved = ...`, restructure so `approved` is computed first and add:

```python
    approved = decision == "approve"
    gate_hash = (_gate_entry(run).get("result") or {}).get("plan_hash")
    if approved and gate_hash:
        if sent_hash is None:
            db.rollback()
            raise HTTPException(status_code=422, detail={"error": "plan_hash_required"})
        if sent_hash != gate_hash:
            db.rollback()
            raise HTTPException(status_code=409, detail={"error": "plan_hash_mismatch"})
```

and pass it on: `store_decision(db, run, approved=approved, by=principal["name"], node=gate, plan_hash=sent_hash)`. (Remove the old `approved = decision == "approve"` line that followed the mismatch check.)

- [ ] **Step 4: Run to verify pass, plus the existing API suite**

Run: `cd backend && python -m pytest tests/test_operator_plan_hash.py tests/test_operator_api.py -q -p no:cacheprovider --no-cov`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/operator_tasks.py backend/app/broski_operator/runs.py backend/tests/test_operator_plan_hash.py
git commit -m "feat: operator API exposes gate context and enforces matching plan_hash on approve

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Recover tools, flow, catalog

**Files:**
- Create: `backend/app/broski_operator/recover_tools.py`, `backend/app/agents/hyperflow/flows/operator_recover.yml`
- Modify: `backend/app/broski_operator/tools.py` (register), `backend/app/broski_operator/catalog.py`
- Test: `backend/tests/test_recover_tools.py`

**Interfaces:**
- Consumes (Tasks 2-4): `recover.gather_candidates/build_report/plan_hash`, runner ctx, gate completed entry `{approved, by, plan_hash}`.
- Produces (`recover_tools.py`): `async recover_propose(params, ctx) -> dict`, `async recover_seal(params, ctx) -> dict`, `class RecoverSealError(RuntimeError)`, internals patched by tests: `_fetch_summaries() -> list[dict]`, `_get_detail(cid: str) -> Optional[dict]`, `_cooldown(name: str) -> dict`, `_write_ledger(entry: dict) -> bool`, module-level `SessionLocal`.
- Produces: `LOCAL_TOOLS["local.recover_propose"]`, `LOCAL_TOOLS["local.recover_seal"]`; catalog `hypercode.recover → operator-recover`.
- Seal contract: reads `propose` node data `.proposal` and the completed `approve` gate entry; raises `RecoverSealError` (run fails, message is short and safe) on: no proposal, recomputed `plan_hash(plan) != proposal.plan_hash`, gate not `approved is True`, missing `by`, or gate `plan_hash != proposal.plan_hash`. Returns `{"ok": True, "sealed": True, "performed": False, "plan", "plan_hash", "approved_by", "ledger": bool, "note"}`.

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_recover_tools.py`

```python
"""BROski recover — propose/seal local tools and the operator-recover flow end to end."""

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.hyperflow.registry import get_flow
from app.broski_operator import catalog, recover, recover_tools, tools
from app.broski_operator.recover_tools import RecoverSealError, recover_propose, recover_seal
from app.models.governance import GovernanceLedger
from app.models.hyperflow import HyperFlowRunStatus
from tests.test_hyperflow import _runner_with_io


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "off")
    monkeypatch.setattr("app.agents.hyperflow_runner.APPROVAL_POLL_SECONDS", 0.01)


def S(name, state, status, labels=None, cid="a1b2c3d4e5f6"):
    return {"Id": cid, "Names": ["/" + name], "State": state, "Status": status, "Labels": labels or {}}


def _docker(monkeypatch, summaries, details=None):
    async def fetch():
        return summaries

    async def detail(cid):
        return (details or {}).get(cid)

    async def cooldown(name):
        return {"count": 0, "limit": 3, "window_s": 300}

    monkeypatch.setattr(recover_tools, "_fetch_summaries", fetch)
    monkeypatch.setattr(recover_tools, "_get_detail", detail)
    monkeypatch.setattr(recover_tools, "_cooldown", cooldown)


def test_propose_picks_the_eligible_unhealthy_container(monkeypatch):
    _docker(monkeypatch, [
        S("hypercode-core", "running", "Up (unhealthy)", cid="c0c0c0c0c0c0"),
        S("zz-nolabel", "running", "Up (unhealthy)", cid="c1c1c1c1c1c1"),
        S("skillweaver", "running", "Up (unhealthy)", cid="c2c2c2c2c2c2"),
        S("chroma", "running", "Up (healthy)", cid="c3c3c3c3c3c3"),
    ])
    out = asyncio.run(recover_propose({}, {"run_id": "r1", "history": []}))
    assert out["ok"] is True and out["has_proposal"] is True
    assert out["proposal"]["plan"]["target"] == "skillweaver"
    assert "hypercode-core: never_list" in out["not_eligible"]
    assert "zz-nolabel: not_allowlisted" in out["not_eligible"]
    assert out["proposal"]["plan"]["run_id"] == "r1" and "checked_at" in out


def test_propose_nothing_to_recover(monkeypatch):
    _docker(monkeypatch, [S("chroma", "running", "Up (healthy)")])
    out = asyncio.run(recover_propose({}, {"run_id": "r1", "history": []}))
    assert out["ok"] is True and out["has_proposal"] is False and out["proposal"] is None


def test_propose_docker_unreachable_is_structured_not_an_exception(monkeypatch):
    async def boom():
        raise RuntimeError("redis://:hunter2@host connection refused")

    monkeypatch.setattr(recover_tools, "_fetch_summaries", boom)
    out = asyncio.run(recover_propose({}, {"run_id": "r1", "history": []}))
    assert out["ok"] is False and out["has_proposal"] is False and out["proposal"] is None
    assert "hunter2" not in " ".join(out["notes"])   # Review focus 5


def test_propose_includes_inspect_attention_notes(monkeypatch):
    _docker(monkeypatch, [])
    hist = [{"node": "inspect", "status": "completed",
             "result": {"success": True, "data": {"attention": ["dead-letter queue has 3 tasks"]}}}]
    out = asyncio.run(recover_propose({}, {"run_id": "r1", "history": hist}))
    assert "dead-letter queue has 3 tasks" in out["notes"]


def test_get_detail_rejects_non_hex_ids_before_any_http(monkeypatch):
    called = []

    class Boom:
        def __init__(self, **kw):
            called.append("client")

    monkeypatch.setattr(recover_tools.httpx, "AsyncClient", Boom)
    for bad in ("../../etc", "abc/../x", "", "zz zz", "g" * 12, "a" * 65):   # Review focus 6
        assert asyncio.run(recover_tools._get_detail(bad)) is None
    assert called == []


# ── seal ────────────────────────────────────────────────────────────────────

PLAN = {"version": 1, "action": "restart", "target": "skillweaver", "reason": "unhealthy",
        "evidence_digest": "sha256:e", "run_id": "r1"}
H = recover.plan_hash(PLAN)


def _hist(approved=True, by="bro@example.com", gate_hash=H, proposal_hash=H, plan=PLAN):
    return [
        {"node": "propose", "type": "tool", "status": "completed",
         "result": {"success": True, "data": {"proposal": {"plan": plan, "plan_hash": proposal_hash}}}},
        {"node": "approve", "type": "human_approval_gate", "status": "completed",
         "result": {"success": True, "approved": approved, "by": by, "plan_hash": gate_hash}},
    ]


@pytest.fixture
def ledger_db(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    GovernanceLedger.__table__.create(bind=eng)
    factory = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    monkeypatch.setattr(recover_tools, "SessionLocal", factory)
    yield factory
    eng.dispose()


def test_seal_success_records_ledger_and_never_performs(ledger_db):
    out = asyncio.run(recover_seal({}, {"run_id": "r1", "history": _hist()}))
    assert out["ok"] is True and out["sealed"] is True and out["performed"] is False
    assert out["plan_hash"] == H and out["approved_by"] == "bro@example.com" and out["ledger"] is True
    s = ledger_db()
    rows = s.query(GovernanceLedger).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.action == "recover_plan_approved" and row.tool_used == "hypercode.recover"
    assert row.decision == "approved" and row.approved_by == "bro@example.com"
    assert row.payload["run_id"] == "r1" and row.payload["performed"] is False and row.payload["plan_hash"] == H
    s.close()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"proposal_hash": "sha256:" + "0" * 64},                       # proposal hash != recomputed
        {"plan": {**PLAN, "target": "postgres"}},                       # tampered plan, old hash
        {"gate_hash": "sha256:" + "1" * 64},                            # approved a different hash
        {"approved": False},                                            # not approved
        {"by": None},                                                   # no recorded approver
        {"by": ""},
    ],
)
def test_seal_refuses_hash_or_approver_problems(ledger_db, kwargs):
    with pytest.raises(RecoverSealError):
        asyncio.run(recover_seal({}, {"run_id": "r1", "history": _hist(**kwargs)}))
    assert ledger_db().query(GovernanceLedger).count() == 0   # Review focus 7: nothing sealed


def test_seal_refuses_without_a_proposal_or_gate(ledger_db):
    with pytest.raises(RecoverSealError):
        asyncio.run(recover_seal({}, {"run_id": "r1", "history": []}))


def test_ledger_failure_does_not_block_the_seal(monkeypatch):
    monkeypatch.setattr(recover_tools, "_write_ledger", lambda entry: False)
    out = asyncio.run(recover_seal({}, {"run_id": "r1", "history": _hist()}))
    assert out["sealed"] is True and out["ledger"] is False


# ── registry + flow ──────────────────────────────────────────────────────────

def test_tools_and_catalog_registered():
    assert "local.recover_propose" in tools.LOCAL_TOOLS and "local.recover_seal" in tools.LOCAL_TOOLS
    assert catalog.TOOL_FLOWS["hypercode.recover"] == "operator-recover"
    assert catalog.tool_for_flow("operator-recover") == "hypercode.recover"


def test_flow_shape():
    fd = get_flow("operator-recover")
    assert fd is not None and fd.intent and fd.entry == "inspect"
    assert fd.node("inspect").idempotent is True and fd.node("propose").idempotent is True
    assert fd.node("propose").success_key == "has_proposal"
    assert fd.node("approve").params["show_from"] == "propose"
    assert fd.node("seal").idempotent is False


def test_operator_recover_flow_end_to_end(monkeypatch, ledger_db):
    """Real flow + real local tools + real runner: propose -> gate (hash shown) -> approve -> seal."""
    _docker(monkeypatch, [S("skillweaver", "running", "Up (unhealthy)", cid="f1f1f1f1f1f1")])

    async def fake_inspect(params, ctx=None):
        return {"ok": True, "attention": []}

    monkeypatch.setitem(tools.LOCAL_TOOLS, "local.inspect", fake_inspect)
    runner, final = _runner_with_io(get_flow("operator-recover"), "e2e-run", monkeypatch)

    async def scenario():
        runner._task = asyncio.create_task(runner._run())
        for _ in range(100):
            if runner.parked_gate == "approve":
                break
            await asyncio.sleep(0.02)
        assert runner.parked_gate == "approve"
        awaiting = [e for e in runner._history if e["status"] == "awaiting_approval"][0]
        shown_hash = awaiting["result"]["plan_hash"]
        assert awaiting["result"]["context"]["proposal"]["plan"]["target"] == "skillweaver"

        def take(node_id=None):
            runner._last_decision_meta = {"by": "bro@example.com", "plan_hash": shown_hash}
            return True

        monkeypatch.setattr(runner, "_take_persisted_decision", take)
        runner.resume(True)
        await runner._task

    asyncio.run(scenario())
    assert final["status"] is HyperFlowRunStatus.COMPLETED
    sealed = [e for e in runner._history if e["node"] == "seal" and e["status"] == "completed"][0]
    assert sealed["result"]["data"]["sealed"] is True and sealed["result"]["data"]["performed"] is False
    assert ledger_db().query(GovernanceLedger).count() == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_recover_tools.py -q -p no:cacheprovider --no-cov`
Expected: FAIL (`ModuleNotFoundError: app.broski_operator.recover_tools`).

- [ ] **Step 3: Create `backend/app/broski_operator/recover_tools.py`**

```python
"""Local tools for `hypercode.recover` (Phase 2a): deterministic propose + verified seal.

Read-only: only GETs through the read-only Docker socket proxy and a read of the healer's
restart counter in Redis. The seal writes one Governance Ledger row (fail-soft) and nothing else.
Nothing here restarts anything.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import redis.asyncio as aioredis

from app.broski_operator import recover
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.governance import GovernanceLedger

logger = logging.getLogger(__name__)

_DOCKER_TIMEOUT = 8.0
_HEX_ID = re.compile(r"[0-9a-f]{12,64}")
_COOLDOWN_LIMIT = 3
_COOLDOWN_WINDOW = 300
_PROPOSE_NODE = "propose"
_GATE_NODE = "approve"


class RecoverSealError(RuntimeError):
    """A sealing precondition failed. Messages are short and contain no untrusted text."""


def _last_data(history: list[dict[str, Any]], node_id: str) -> Optional[dict[str, Any]]:
    for entry in reversed(history):
        if entry.get("node") == node_id and entry.get("status") == "completed":
            data = (entry.get("result") or {}).get("data")
            return data if isinstance(data, dict) else None
    return None


def _last_result(history: list[dict[str, Any]], node_id: str) -> Optional[dict[str, Any]]:
    for entry in reversed(history):
        if entry.get("node") == node_id and entry.get("status") == "completed":
            return entry.get("result") or {}
    return None


async def _fetch_summaries() -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(
            f"{settings.DOCKER_SOCKET_PROXY_URL}/containers/json", params={"all": "true"}
        )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []


async def _get_detail(cid: str) -> Optional[dict[str, Any]]:
    if not isinstance(cid, str) or not _HEX_ID.fullmatch(cid):
        return None  # never build a URL path from anything but a Docker hex id
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.DOCKER_SOCKET_PROXY_URL}/containers/{cid}/json")
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else None
    except Exception:
        return None


async def _cooldown(name: str) -> dict[str, Any]:
    """Informational read of the healer's restart counter (2b enforces the limit)."""
    info: dict[str, Any] = {"count": None, "limit": _COOLDOWN_LIMIT, "window_s": _COOLDOWN_WINDOW}
    try:
        r = aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
        try:
            raw = await r.get(f"healer:restarts:{name}")
        finally:
            await r.aclose()
        info["count"] = int(raw) if raw is not None else 0
    except Exception:
        pass
    return info


async def recover_propose(params: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    history = (ctx or {}).get("history", [])
    run_id = str((ctx or {}).get("run_id", ""))
    notes: list[str] = []
    inspect_data = _last_data(history, "inspect")
    if inspect_data:
        notes.extend(str(a) for a in list(inspect_data.get("attention") or [])[:10])
    try:
        summaries = await asyncio.wait_for(_fetch_summaries(), timeout=_DOCKER_TIMEOUT)
        candidates = await recover.gather_candidates(summaries, _get_detail)
    except Exception as exc:  # fail-soft: an unreachable proxy is a finding, not a crash
        return {
            "ok": False, "has_proposal": False, "proposal": None, "candidates": [],
            "not_eligible": [],
            "notes": notes + [f"docker proxy unreachable ({type(exc).__name__})"],
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    for cand in candidates[:5]:
        cand["cooldown"] = await _cooldown(cand["container"])
    report = recover.build_report(candidates, run_id, notes)
    report["checked_at"] = datetime.now(timezone.utc).isoformat()
    return report


def _write_ledger(entry: dict[str, Any]) -> bool:
    db = SessionLocal()
    try:
        db.add(
            GovernanceLedger(
                user_id="broski-operator",
                action="recover_plan_approved",
                tool_used="hypercode.recover",
                payload=entry["payload"],
                decision="approved",
                agent_name="broski-operator",
                approved_by=entry["approved_by"],
            )
        )
        db.commit()
        return True
    except Exception:
        db.rollback()
        logger.warning("recover seal: governance ledger insert failed", exc_info=True)
        return False
    finally:
        db.close()


async def recover_seal(params: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    history = (ctx or {}).get("history", [])
    run_id = str((ctx or {}).get("run_id", ""))
    proposed = _last_data(history, _PROPOSE_NODE) or {}
    proposal = proposed.get("proposal")
    if not isinstance(proposal, dict) or not isinstance(proposal.get("plan"), dict):
        raise RecoverSealError("no proposal to seal")
    plan = proposal["plan"]
    claimed = proposal.get("plan_hash")
    if not claimed or recover.plan_hash(plan) != claimed:
        raise RecoverSealError("plan hash does not match the plan")
    gate = _last_result(history, _GATE_NODE)
    if not gate or gate.get("approved") is not True:
        raise RecoverSealError("plan was not approved")
    approver = gate.get("by")
    if not approver:
        raise RecoverSealError("no recorded approver")
    if gate.get("plan_hash") != claimed:
        raise RecoverSealError("approval was not for this plan hash")
    ledger_ok = await asyncio.to_thread(
        _write_ledger,
        {
            "approved_by": str(approver),
            "payload": {"plan": plan, "plan_hash": claimed, "run_id": run_id, "performed": False},
        },
    )
    return {
        "ok": True,
        "sealed": True,
        "performed": False,
        "plan": plan,
        "plan_hash": claimed,
        "approved_by": str(approver),
        "ledger": bool(ledger_ok),
        "note": "restart is NOT executed in Phase 2a; the governed executor (2b) consumes this plan",
    }
```

- [ ] **Step 4: Register the tools** — at the very bottom of `backend/app/broski_operator/tools.py`, after the `LOCAL_TOOLS` dict:

```python
from app.broski_operator.recover_tools import recover_propose, recover_seal  # noqa: E402

LOCAL_TOOLS["local.recover_propose"] = recover_propose
LOCAL_TOOLS["local.recover_seal"] = recover_seal
```

(`recover_tools` does not import `tools`, so there is no cycle; `tools` imports `recover` via Task 2 and `recover_tools` imports `recover`.)

- [ ] **Step 5: Catalog + flow**

`catalog.py`: add `"hypercode.recover": "operator-recover",` to `TOOL_FLOWS` (after `hypercode.inspect`).

`backend/app/agents/hyperflow/flows/operator_recover.yml`:

```yaml
# BROski operator: read-only recovery diagnosis. Proposes ONE allow-listed container restart for
# human approval and seals the approved plan. Phase 2a executes nothing.
# Run it: POST /api/v1/operator/tasks {"tool": "hypercode.recover", "arguments": {}}

name: operator-recover
version: 1
entry: inspect
intent: "BROski operator recovery diagnosis proposing one allow-listed container restart for human approval without executing it"

nodes:
  - id: inspect
    type: tool
    tool: local.inspect
    idempotent: true

  - id: propose
    type: tool
    tool: local.recover_propose
    idempotent: true
    success_key: has_proposal

  - id: approve
    type: human_approval_gate
    params:
      prompt: "Approve this restart plan? Phase 2a only records the approved plan; nothing is restarted."
      show_from: propose

  - id: seal
    type: tool
    tool: local.recover_seal

edges:
  - from: inspect
    to: propose
  - from: propose
    to: approve
    condition: true
  - from: approve
    to: seal
```

- [ ] **Step 6: Run to verify pass + neighbours**

Run: `cd backend && python -m pytest tests/test_recover_tools.py tests/test_recover_core.py tests/test_operator_tools.py tests/test_goal_matcher.py tests/test_flows_endpoint.py -q -p no:cacheprovider --no-cov`
Expected: all PASS. If a goal-matcher test regresses because of the new `intent`, reword only that flow's `intent:` (keep it non-empty; `test_all_registered_flows_declare_intent` requires it).

- [ ] **Step 7: Commit**

```bash
git add backend/app/broski_operator/recover_tools.py backend/app/broski_operator/tools.py backend/app/broski_operator/catalog.py backend/app/agents/hyperflow/flows/operator_recover.yml backend/tests/test_recover_tools.py
git commit -m "feat: hypercode.recover flow, propose/seal local tools and catalog entry

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: MCP tool `hypercode_recover`

**Files:**
- Modify: `services/hypercode-mcp-server/server.py`
- Test: `backend/tests/test_operator_mcp_tools.py` (append)

**Interfaces:**
- Consumes (Task 5): catalog tool name `hypercode.recover`.
- Produces: MCP tool `hypercode_recover() -> dict` posting `{"tool": "hypercode.recover", "arguments": {}}` to `/api/v1/operator/tasks`. **No approval tool.**

- [ ] **Step 1: Append the failing test** to `backend/tests/test_operator_mcp_tools.py`:

```python
def test_recover_posts_the_allow_listed_tool_and_no_approval_tool_exists(monkeypatch):
    import asyncio

    mod = _load(monkeypatch)
    mod._post = AsyncMock(return_value={"taskId": GOOD_ID})
    assert asyncio.run(mod.hypercode_recover()) == {"taskId": GOOD_ID}
    mod._post.assert_awaited_once_with(
        "/api/v1/operator/tasks", {"tool": "hypercode.recover", "arguments": {}}
    )
    tool_names = [n for n in dir(mod) if n.startswith("hypercode_")]
    assert not any("approve" in n or "input" in n for n in tool_names)
```

- [ ] **Step 2: Run to verify failure** — `cd backend && python -m pytest tests/test_operator_mcp_tools.py -q -p no:cacheprovider --no-cov` → FAIL (`AttributeError: hypercode_recover`).

- [ ] **Step 3: Implement** — in `services/hypercode-mcp-server/server.py`, add directly after `hypercode_inspect` (above `hypercode_task_get`):

```python
@mcp.tool()
async def hypercode_recover() -> dict:
    """
    Start a read-only recovery diagnosis as a background task. It looks for broken containers,
    proposes at most ONE allow-listed restart, and waits for a human (superuser) to approve the
    exact plan in the dashboard/API. Phase 2a NEVER restarts anything — approval only seals the
    plan for the future governed executor. Returns a task handle; poll with hypercode_task_get.
    """
    return await _post(
        f"{API_PREFIX}/operator/tasks", {"tool": "hypercode.recover", "arguments": {}}
    )
```

Also add `  hypercode_recover        — start a recovery diagnosis (background task, proposes only)` to the module docstring's tool list.

- [ ] **Step 4: Run to verify pass** — same command → PASS.

- [ ] **Step 5: Commit**

```bash
git add services/hypercode-mcp-server/server.py backend/tests/test_operator_mcp_tools.py
git commit -m "feat: hypercode_recover MCP tool (proposal only, no approval tool)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Live proof script, deploy, docs (controller-run live steps)

**Files:**
- Create: `scripts/prove-recover.py`
- Modify: `docs/superpowers/specs/2026-09-27-broski-recover-design.md` (amendments), `WHATS_DONE.md` (entry)

**Interfaces:**
- Consumes: everything above. Runs **inside `hypercode-core`**: `docker exec -i hypercode-core python - <phase> [args] < scripts/prove-recover.py`. Prints only PASS/FAIL/INFO/SKIP lines, never a token or env value; exits non-zero on the first FAIL.
- Phases: `phaseA` (proposal, hash rules, seal, not-restarted, reject, legacy no-leak), `phaseB1` (park a run at the gate, print `PARKED_TASK=<id>`), `phaseB2 <id>` (after `docker restart hypercode-core`: approve with the shown hash, expect sealed).

- [ ] **Step 1 (subagent, Steps 1-2 only): create `scripts/prove-recover.py`**

```python
"""Live proof for hypercode.recover (Phase 2a). Runs INSIDE hypercode-core.

Controller prerequisites (host, once): two throwaway containers, then remove them afterwards:
  docker run -d --name zz-recover-proof   --label hypercode.recover=restartable \
      --health-cmd "exit 1" --health-interval 5s --health-retries 1 alpine sleep 3600
  docker run -d --name zz-recover-nolabel \
      --health-cmd "exit 1" --health-interval 5s --health-retries 1 alpine sleep 3600
  (wait ~20 s until both report unhealthy)

    docker exec -i hypercode-core python - phaseA  < scripts/prove-recover.py
    docker exec -i hypercode-core python - phaseB1 < scripts/prove-recover.py   # prints PARKED_TASK=<id>
    docker restart hypercode-core                                                # then wait healthy
    docker exec -i hypercode-core python - phaseB2 <id> < scripts/prove-recover.py

Prints only PASS/FAIL/INFO lines. Never prints a token. Read-only Docker GETs only.
"""

import sys
import time

import httpx
from sqlalchemy import text

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.models import User

ROOT = "http://localhost:8000"
BASE = ROOT + "/api/v1/operator"
TARGET = "zz-recover-proof"
NOLABEL = "zz-recover-nolabel"


def _token() -> str:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.is_superuser.is_(True), User.is_active.is_(True)).first()
        if user is None:
            sys.exit("FAIL: no active superuser to mint a proof token for")
        return create_access_token(subject=user.id)
    finally:
        db.close()


HEADERS = {"Authorization": f"Bearer {_token()}"}


def call(method, path, **kw):
    r = httpx.request(method, BASE + path, headers=HEADERS, timeout=30, **kw)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}


def docker_state(name):
    """Read-only GET via the socket proxy: (StartedAt, RestartCount) or None."""
    r = httpx.get(f"{settings.DOCKER_SOCKET_PROXY_URL}/containers/{name}/json", timeout=10)
    if r.status_code != 200:
        return None
    j = r.json()
    return (j["State"]["StartedAt"], j["RestartCount"])


def check(ok, label):
    print(("PASS: " if ok else "FAIL: ") + label)
    if not ok:
        sys.exit(1)


def wait_for(task_id, want, timeout=120):
    end, last = time.time() + timeout, None
    while time.time() < end:
        try:
            code, body = call("GET", f"/tasks/{task_id}")
            last = body.get("status")
            if code == 200 and last in want:
                return body
        except httpx.HTTPError:
            pass
        time.sleep(2)
    sys.exit(f"FAIL: timed out waiting for {sorted(want)} on {task_id}; last status={last}")


def start_recover():
    code, h = call("POST", "/tasks", json={"tool": "hypercode.recover", "arguments": {}})
    check(code == 200 and h.get("taskId"), "hypercode.recover returns a handle immediately")
    return h["taskId"]


def cancel_quiet(tid):
    try:
        call("POST", f"/tasks/{tid}/cancel", json={"reason": "proof cleanup"})
    except Exception:
        pass


def phaseA():
    before = docker_state(TARGET)
    check(before is not None, f"throwaway container {TARGET} exists")
    tid = start_recover()
    try:
        body = wait_for(tid, {"input_required"})
        ap = body["inputRequests"]["approval"]
        ctx = ap["context"]
        plan = ctx["proposal"]["plan"]
        check(plan["target"] == TARGET, f"proposal targets exactly {TARGET}")
        check(plan["action"] == "restart" and plan["run_id"] == tid, "plan is a restart bound to this run")
        check(ap["plan_hash"] == ctx["proposal"]["plan_hash"], "gate shows the plan_hash of the proposal")
        check(any(NOLABEL in x and "not_allowlisted" in x for x in ctx["not_eligible"]),
              f"unlabelled unhealthy {NOLABEL} is refused (not_allowlisted)")
        check(all(c["container"] != "hypercode-core" or not c["eligibility"]["allowed"]
                  for c in ctx["candidates"]), "no protected container is ever eligible")
        good = ap["plan_hash"]

        code, _ = call("POST", f"/tasks/{tid}/input", json={"decision": "approve"})
        check(code == 422, f"approve without plan_hash -> {code} (expected 422)")
        code, b = call("POST", f"/tasks/{tid}/input",
                       json={"decision": "approve", "plan_hash": "sha256:" + "0" * 64})
        check(code == 409 and b.get("detail", {}).get("error") == "plan_hash_mismatch",
              f"approve with WRONG plan_hash -> {code} plan_hash_mismatch")
        time.sleep(3)
        _, still = call("GET", f"/tasks/{tid}")
        check(still["status"] == "input_required", "still parked after the rejected approvals")

        code, _ = call("POST", f"/tasks/{tid}/input", json={"decision": "approve", "plan_hash": good})
        check(code == 200, "approve with the shown plan_hash accepted")
        done = wait_for(tid, {"completed", "failed"})
        check(done["status"] == "completed", "run completed after approval")
        rep = done["result"]["report"]
        check(rep["sealed"] is True and rep["performed"] is False, "sealed with performed=false")
        check(rep["plan_hash"] == good and rep["approved_by"], "sealed plan_hash matches; approver recorded")
        db = SessionLocal()
        try:
            n = db.execute(
                text("SELECT count(*) FROM governance_ledger WHERE action='recover_plan_approved' "
                     "AND payload->>'run_id' = :r"), {"r": tid}).scalar()
        finally:
            db.close()
        check(n == 1, "exactly one Governance Ledger row for this run")
        after = docker_state(TARGET)
        check(after == before, f"{TARGET} was NOT restarted (StartedAt/RestartCount unchanged)")
        r = httpx.get(f"{ROOT}/api/v1/flows/runs/{tid}", timeout=30)
        check(r.status_code == 200, "legacy unauthenticated run endpoint reachable")
        leaked = [k for e in r.json().get("history", []) for k in ("data", "context")
                  if k in (e.get("result") or {})]
        check(not leaked, "legacy endpoint history has no result.data / result.context")
    finally:
        cancel_quiet(tid)

    tid2 = start_recover()
    try:
        wait_for(tid2, {"input_required"})
        code, _ = call("POST", f"/tasks/{tid2}/input", json={"decision": "reject"})
        check(code == 200, "reject needs no plan_hash")
        end = wait_for(tid2, {"failed", "completed"})
        check(end["status"] == "failed" and "approval rejected" in (end.get("error") or ""),
              "rejected plan fails the run and seals nothing")
        check(docker_state(TARGET) == before, f"{TARGET} still not restarted after reject")
    finally:
        cancel_quiet(tid2)
    print("PASS: phaseA complete")


def phaseB1():
    tid = start_recover()
    body = wait_for(tid, {"input_required"})
    check(body["inputRequests"]["approval"]["plan_hash"], "run parked at the approval gate with a plan_hash")
    print(f"PARKED_TASK={tid}")


def phaseB2(tid):
    body = wait_for(tid, {"input_required"})
    print("INFO: parked task is visible again after the restart")
    good = body["inputRequests"]["approval"]["plan_hash"]
    code, _ = call("POST", f"/tasks/{tid}/input", json={"decision": "approve", "plan_hash": good})
    check(code == 200, "approval with the shown plan_hash accepted after the restart")
    done = wait_for(tid, {"completed", "failed"})
    check(done["status"] == "completed" and done["result"]["report"]["sealed"] is True,
          "sealed after an approval that survived a core restart")
    check(docker_state(TARGET) is not None, f"{TARGET} untouched")
    print("PASS: phaseB2 complete")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "phaseA":
        phaseA()
    elif len(sys.argv) >= 2 and sys.argv[1] == "phaseB1":
        phaseB1()
    elif len(sys.argv) >= 3 and sys.argv[1] == "phaseB2":
        phaseB2(sys.argv[2])
    else:
        sys.exit("usage: phaseA | phaseB1 | phaseB2 <task_id>")
```

- [ ] **Step 2 (subagent): syntax check + commit**

Run: `python -c "import ast; ast.parse(open('scripts/prove-recover.py', encoding='utf-8').read()); print('syntax ok')"` → `syntax ok`, then:

```bash
git add scripts/prove-recover.py
git commit -m "feat: live proof script for hypercode.recover

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

- [ ] **Step 3 (controller): full regression on the host before any live step**

Run (background, ~4-5 min): `cd backend && python -m pytest tests/test_recover_policy.py tests/test_recover_core.py tests/test_recover_tools.py tests/test_operator_gate_context.py tests/test_operator_plan_hash.py tests/test_operator_api.py tests/test_operator_tools.py tests/test_operator_runner.py tests/test_operator_durable_approval.py tests/test_operator_recovery.py tests/test_operator_mcp_tools.py tests/test_hyperflow.py tests/test_flows_endpoint.py tests/test_goal_matcher.py -q -p no:cacheprovider --no-cov`
Expected: all PASS.

- [ ] **Step 4 (controller): RAM gate + baseline** — `wsl -e free -m` → `available` >= 1500 MB; capture `docker ps` / `docker stats --no-stream`; core healthy, RestartCount 0.

- [ ] **Step 5 (controller): build + recreate core only** — `docker compose -f docker-compose.yml -f docker-compose.agents.yml build hypercode-core` then `docker compose -f docker-compose.yml -f docker-compose.agents.yml up -d --no-deps hypercode-core`; poll health + RAM every ~7 s; expect healthy in ~3 min, restarts 0, boot log `HyperFlow recovery: {...}`. Then (if the MCP tool is being proven) build/recreate `hypercode-mcp-server` the same way (its key is already provisioned).

- [ ] **Step 6 (controller): throwaway containers + proof** — start the two `zz-recover-*` containers from the script header, wait until both are unhealthy, run `phaseA` (expect all `PASS:`), then `phaseB1`, `docker restart hypercode-core` (single container; wait healthy ~2 min), `phaseB2 <id>`. Then the MCP path: `hypercode_recover` → `hypercode_task_get` until `input_required`, read `inputRequests.approval.plan_hash`, and cancel with `hypercode_task_cancel` (approval stays human-only). **Always** `docker rm -f zz-recover-proof zz-recover-nolabel` afterwards. Stop immediately on any stop condition in Global Constraints.

- [ ] **Step 7 (controller): docs** — append to the spec: a "Refinements made while planning/executing" section (approve-only `plan_hash` requirement; OOM-137 detail lookup; `scrub_text` shared; `_last_decision_meta` side-channel; seal fails the run by raising) and add the live evidence (commands' PASS lines, StartedAt/RestartCount unchanged, ledger row count, min available RAM, health timings). Insert a `## 2026-09-27 — BROski operator Phase 2a: hypercode.recover (advisory, live-proven)` entry at the top of `WHATS_DONE.md` (update the "Last synced" line). Commit `docs: BROski recover 2a evidence`.

- [ ] **Step 8: whole-branch review, then stop for Bro** — final whole-branch review (most capable model) before any push; **do not push or open a PR until Bro says so.**

---

## Self-Review

**Spec coverage:** §4.1 flow/tool → Tasks 3, 5; §4.2 candidate rules + policy + evidence + dependents + cooldown → Tasks 1, 2, 5; §4.3 plan + hash → Task 2; §4.4 approval binding (context, `plan_hash`, approver) → Tasks 3, 4; §4.5 seal + ledger → Task 5; §4.6 MCP → Task 6; §6 safety properties 1-8 → Global Constraints + tests in Tasks 1-5 (no mutation: only GET code paths exist; default-deny/never-list: Task 1; on-purpose stops: Task 2; approve exactly what was shown: Tasks 3-5; seal re-verification: Task 5; scrub/cap: Task 2; Phase 1 rules unchanged: Task 4 keeps the existing 403 tests); §7 testing → per-task tests; §8 live proof → Task 7 (`prove-recover.py`); §9 2b outline → not built (documented); §10 limitations → carried into Task 7 docs.

**Placeholder scan:** no TBD/TODO; the only "adapt" instruction is Task 3 Step 1 (existing test stubs) which names the exact edits.

**Type consistency:** `gather_candidates` candidate keys `container/state/reason/evidence/eligibility/dependents` are used identically by `build_report`, `recover_propose` and the tests; `plan_hash` is the same function everywhere; local tools are always `(params, ctx)`; `_last_decision_meta` keys `by`/`plan_hash` match `store_decision`'s decision keys and the completed-gate entry keys; the gate/propose node ids `approve`/`propose` are constants in `recover_tools` and the flow YAML.

**Review Focus coverage:** 1 → Task 4 tests 2-3, Task 5 seal refusals; 2 → Task 2 `test_reason_from_summary_table` + 137 tests; 3 → Task 1; 4 → Task 3 `test_strip_data...` + legacy test and Task 7 proof; 5 → Task 5 unreachable-Docker test; 6 → Task 5 `test_get_detail_rejects_non_hex_ids...`; 7 → Task 5 ledger-failure and seal-refusal tests.

**Known deviation from the spec (to record in Task 7):** `/input` requires `plan_hash` for approvals only.
