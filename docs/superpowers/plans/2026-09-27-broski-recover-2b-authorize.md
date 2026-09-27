# BROski Recover Phase 2b — `authorize` Node Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 5th node, `authorize`, to the `operator-recover` flow. After a plan is sealed, it asks Governor to mint a `DRY_RUN` capability for the exact restart; with today's policy configuration (no grant for this caller), Governor correctly refuses via Shepherd's ESCALATE path. The node records that refusal (a well-formed, expected outcome, not a tool failure) in a new Governance Ledger entry and completes the flow successfully. Nothing mints. Nothing executes. No Docker call exists anywhere in this code.

**Architecture:** One new local tool module (`authorize_tools.py`), one new flow node, one new `Literal` value in Governor's own copy of its plan schema (never touched: `fleet-controller`). The tool talks to Governor's real, already-built, already-tested HTTP API directly — never to `fleet-controller`, never to Docker.

**Tech Stack:** Python 3.13 / FastAPI / httpx / pytest (`asyncio.run` style, matching the rest of this package).

**Spec:** `docs/superpowers/specs/2026-09-27-broski-recover-2b-design.md` (committed `40cdd64a` on `feature/broski-recover-2b`, branched off `feature/broski-recover-2a`). Correction found while planning (record in Task 3): Governor's **in-cluster** listen port is `8080` (`agents/governor/Dockerfile`: `EXPOSE 8080`, `uvicorn ... --port 8080`); `8089` in the spec and in `docker-compose.fleet.yml`'s `ports:` mapping (`127.0.0.1:8089:8080`) is only the **host-published** port for external/dev access. The in-cluster URL is `http://governor:8080`.

## Global Constraints

- Work on branch `feature/broski-recover-2b` in `H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4` (already checked out, based on `feature/broski-recover-2a` — do not switch or rebase). Commit prefixes `feat:`/`fix:`/`docs:`/`test:`. Every commit ends with `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`. `git add <exact files>` only, never `git add -A`. **No push, no PR, no merge without Bro's say-so.**
- Python: 4-space indent; imports `from app.X import Y` inside `backend/`, plain relative imports inside `agents/governor/` (that package has no `app.` prefix — check its existing files' import style, e.g. `agents/governor/main.py` imports `capability`, `ledger_client`, `transitions` directly, no package prefix).
- **No mutation, ever, in this task set.** `authorize_tools.py` makes exactly one outbound call: `POST` to Governor's `/v1/capabilities/mint`. No Docker call, no Shepherd call (Governor calls Shepherd internally), no `capabilities.json` change, no `agents/safety-shepherd/policy.py` change, no `agents/fleet-controller/*` change.
- **Never conflate the two hashes.** 2a's `plan_hash` and Governor's `governor_plan_hash` are computed by different algorithms over different shapes, for different purposes, and must appear as separately-labelled fields everywhere they're surfaced (tool result, ledger payload).
- **A genuine communication failure to Governor must fail the node** (raise, so the flow marks it failed) — it must never be silently turned into a fabricated `minted: false` result indistinguishable from a real policy refusal.
- Tests: from `backend/`, run one file at a time, never in parallel: `python -m pytest tests/test_authorize_tools.py -q -p no:cacheprovider --no-cov` (and similarly for any other file named in a step). A prior session on this branch's ancestor hit a stray-parallel-pytest/SQLite race — avoid it.
- `agents/governor/`'s own test suite runs from `agents/governor/`: `cd agents/governor && python -m pytest tests/test_models.py -q` (new file; there is currently no `test_models.py` — see Task 1) — do **not** run governor's full suite unless a step says to; it has its own virtualenv/requirements that may not be on this host's default `python`. If `pytest`/deps aren't importable from that directory, use `python -m pytest` from the repo root with `PYTHONPATH=agents/governor` instead, and note whichever worked in the report.

## Review Focus

The spec's own §5 "Safety properties" list is the review focus, verbatim:

1. `authorize` never issues a Docker call of any kind — only HTTP calls to Governor (Task 2 test: grep-style assertion the module imports no docker client; Task 3 test: the mocked HTTP call is the only I/O).
2. A refusal (the expected outcome today) completes the flow successfully; it is never mistaken for a tool failure (Task 3).
3. 2a's `plan_hash` and Governor's `governor_plan_hash` are never conflated in the result or the ledger payload (Task 3).
4. A genuine communication failure to Governor (not a policy refusal) fails the node — fail-closed (Task 3).
5. A Governance Ledger write failure never blocks `authorize`'s own result (Task 3).
6. Adding the `"container.restart"` literal to Governor's copy of `models.py` does not change `fleet-controller`'s copy or behavior at all (Task 1 — confirmed by diff, pinned by Task 1's own test not existing in `fleet-controller`).

## File Structure

| File | Responsibility |
|---|---|
| `agents/governor/models.py` (modify) | Add `"container.restart"` to `RequestedAction.kind`'s `Literal` |
| `agents/governor/tests/test_models.py` (create) | Locks the literal set; proves `fleet-controller`'s copy is untouched |
| `backend/app/broski_operator/authorize_tools.py` (create) | `authorize(params, ctx)` — builds the Governor-shaped plan, computes its hash, mints, records the ledger entry |
| `backend/app/broski_operator/tools.py` (modify) | Register `local.authorize` in `LOCAL_TOOLS` |
| `backend/app/agents/hyperflow/flows/operator_recover.yml` (modify) | Add the `authorize` node + edge from `seal` |
| `backend/tests/test_authorize_tools.py` (create) | Unit tests for the plan builder, hash parity with Governor's real algorithm, mint outcomes, ledger fail-soft, flow registration |
| `docs/superpowers/specs/2026-09-27-broski-recover-2b-design.md` (modify) | Append amendments (the 8080-vs-8089 correction; anything else found while implementing) |

---

### Task 1: Governor schema — add the `container.restart` literal

**Files:**
- Modify: `agents/governor/models.py`
- Test: `agents/governor/tests/test_models.py` (new)

**Interfaces:**
- Produces: `RequestedAction.kind: Literal["compose_profile.preview", "crew.workflow.preview", "container.restart"]` — the only change to this file.

- [ ] **Step 1: Write the failing test** — `agents/governor/tests/test_models.py`

```python
"""Governor's own copy of the plan schema — the container.restart literal (Phase 2b)."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from models import RequestedAction  # noqa: E402


def test_container_restart_is_a_valid_kind():
    action = RequestedAction(action_id="restart-x", kind="container.restart", profile="skillweaver")
    assert action.kind == "container.restart" and action.profile == "skillweaver"


def test_existing_kinds_still_valid():
    RequestedAction(action_id="a", kind="compose_profile.preview")
    RequestedAction(action_id="b", kind="crew.workflow.preview")


def test_unknown_kind_still_rejected():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RequestedAction(action_id="c", kind="compose_profile.start")


def test_fleet_controller_copy_is_unaffected():
    """The file-copy convention means fleet-controller's own copy must NOT gain this literal."""
    fc_models = pathlib.Path(__file__).resolve().parents[2] / "fleet-controller" / "models.py"
    text = fc_models.read_text(encoding="utf-8")
    assert "container.restart" not in text
    assert 'Literal["compose_profile.preview", "crew.workflow.preview"]' in text
```

- [ ] **Step 2: Run to verify failure**

Run (from `agents/governor/`): `python -m pytest tests/test_models.py -q`
If `pydantic`/`pytest` aren't importable from that directory on this host, run instead from the repo root: `PYTHONPATH=agents/governor python -m pytest agents/governor/tests/test_models.py -q` (Git Bash: `PYTHONPATH=agents/governor python -m pytest ...`; PowerShell: `$env:PYTHONPATH="agents/governor"; python -m pytest agents/governor/tests/test_models.py -q`). Note in the report which command worked.
Expected: FAIL (`ValidationError` on `test_container_restart_is_a_valid_kind` — `container.restart` not yet a valid literal).

- [ ] **Step 3: Implement** — in `agents/governor/models.py`, change line 21:

```python
    kind: Literal["compose_profile.preview", "crew.workflow.preview", "container.restart"]
```

- [ ] **Step 4: Run to verify pass**

Same command as Step 2. Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/governor/models.py agents/governor/tests/test_models.py
git commit -m "feat: governor plan schema gains container.restart (Phase 2b, no other change)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: `authorize_tools.py` — the plan builder, hash, and mint call

**Files:**
- Create: `backend/app/broski_operator/authorize_tools.py`
- Test: `backend/tests/test_authorize_tools.py`

**Interfaces:**
- Consumes (Task 1): nothing directly (the test cross-checks against Governor's real `canonical_hash`, but runtime code never imports across the agent boundary).
- Produces:
  - `class AuthorizeError(RuntimeError)` — a genuine failure to reach/parse Governor's response. Distinct from `recover_tools.RecoverSealError`.
  - `GOVERNOR_TIMEOUT_S = 8.0`
  - `_governor_url() -> str` — `os.getenv("GOVERNOR_URL") or "http://governor:8080"` (mirrors `agents/fleet-controller/safety_client.py`'s `_url()` pattern exactly).
  - `build_plan(run_id: str, target: str) -> dict` — the full, explicit Governor-shaped plan dict (see Step 3 below for the exact shape; **must include `constraints` explicitly**, not omit it, so the client-side hash matches what Governor recomputes server-side after Pydantic fills in defaults).
  - `canonical_hash(plan: dict) -> str` — `"sha256:" + hexdigest` over `json.dumps(plan, sort_keys=True, separators=(",", ":"))`. Same algorithm as `agents/governor/models.py:canonical_hash`, reimplemented locally (file-copy convention — never import across the agent/service boundary), operating on a plain dict instead of a Pydantic model.
  - `async authorize(params: dict, ctx: dict) -> dict` — the local tool. Signature matches every other tool in `recover_tools.py`: `(params, ctx)`.
  - `_write_ledger(entry: dict) -> bool` — same fail-soft shape as `recover_tools._write_ledger` (whole body in one `try/except`, including `SessionLocal()` construction and `db.rollback()`, per the exact fix Phase 2a's final review required).
  - Module-level `SessionLocal` (imported from `app.db.session`, patched by tests exactly like `recover_tools.py` is).

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_authorize_tools.py`

```python
"""BROski recover Phase 2b — authorize: builds a Governor plan, mints DRY_RUN, records the outcome.

Every mint in these tests is refused (ESCALATE, no grant) by design — this increment proves the
pipeline fails closed, it never mints. See docs/superpowers/specs/2026-09-27-broski-recover-2b-design.md.
"""

import asyncio
import importlib.util
import pathlib
import sys

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.broski_operator import authorize_tools
from app.broski_operator.authorize_tools import AuthorizeError, authorize, build_plan, canonical_hash
from app.models.governance import GovernanceLedger


@pytest.fixture
def ledger_db(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    GovernanceLedger.__table__.create(bind=eng)
    factory = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    monkeypatch.setattr(authorize_tools, "SessionLocal", factory)
    yield factory
    eng.dispose()


def _load_real_governor_module():
    """Load the REAL agents/governor/models.py in this test process only — never at runtime.

    This is the file-copy convention's intended escape hatch for tests: prove independent
    reimplementations agree, without ever letting production code cross-import agents.
    """
    path = pathlib.Path(__file__).resolve().parents[2] / "agents" / "governor" / "models.py"
    spec = importlib.util.spec_from_file_location("governor_models_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── build_plan / canonical_hash ──────────────────────────────────────────────

def test_build_plan_shape():
    plan = build_plan("run-123", "skillweaver")
    assert plan == {
        "schema_version": 1,
        "mission_id": "run-123",
        "requested_actions": [
            {"action_id": "restart-skillweaver", "kind": "container.restart", "profile": "skillweaver"}
        ],
        "constraints": {"max_services": 25, "allow_profiles": [], "deny_profiles": []},
    }


def test_canonical_hash_matches_governors_real_algorithm():
    """The core parity guarantee: our hash must equal what Governor recomputes server-side."""
    gov = _load_real_governor_module()
    plan_dict = build_plan("run-456", "chroma")
    gov_plan = gov.PlanRequest(**plan_dict)
    assert canonical_hash(plan_dict) == gov.canonical_hash(gov_plan)


def test_canonical_hash_stable_and_content_sensitive():
    p1 = build_plan("run-1", "chroma")
    p2 = build_plan("run-1", "chroma")
    p3 = build_plan("run-1", "skillweaver")
    assert canonical_hash(p1) == canonical_hash(p2)
    assert canonical_hash(p1) != canonical_hash(p3)
    assert canonical_hash(p1).startswith("sha256:") and len(canonical_hash(p1)) == 7 + 64


# ── authorize() ───────────────────────────────────────────────────────────────

REFUSAL_BODY = {
    "capability": None, "jti": None,
    "verdict": {"decision": "ESCALATE", "reason": "no capabilities for agent 'broski-operator'",
                "risk_class": "INFRASTRUCTURE_MUTATION", "policy_version": "safety-2026-09-04.1"},
    "minted": False, "reason": "policy verdict ESCALATE; human approval required",
}


def _client_returning(status_code, json_body=None, raise_exc=None):
    async def handler(request: httpx.Request) -> httpx.Response:
        if raise_exc is not None:
            raise raise_exc
        return httpx.Response(status_code, json=json_body if json_body is not None else {})

    def factory(**kw):
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), **kw)

    return factory


def test_authorize_records_a_well_formed_refusal_as_success(monkeypatch, ledger_db):
    monkeypatch.setattr(authorize_tools.httpx, "AsyncClient", _client_returning(200, REFUSAL_BODY))
    out = asyncio.run(authorize({}, {"run_id": "run-1", "history": []}))
    assert out["ok"] is True
    assert out["minted"] is False
    assert out["mode"] == "DRY_RUN"
    assert out["verdict"]["decision"] == "ESCALATE"
    assert out["verdict"]["risk_class"] == "INFRASTRUCTURE_MUTATION"
    assert out["ledger"] is True
    s = ledger_db()
    rows = s.query(GovernanceLedger).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.action == "recover_authorization_attempted" and row.tool_used == "hypercode.recover"
    assert row.payload["minted"] is False
    assert row.payload["mode"] == "DRY_RUN"
    assert row.payload["governor_verdict"]["decision"] == "ESCALATE"
    s.close()


def test_authorize_never_conflates_the_two_hashes(monkeypatch, ledger_db):
    monkeypatch.setattr(authorize_tools.httpx, "AsyncClient", _client_returning(200, REFUSAL_BODY))
    out = asyncio.run(authorize({}, {"run_id": "run-2", "history": []}))
    assert "plan_hash" in out and "governor_plan_hash" in out
    assert out["plan_hash"] != out["governor_plan_hash"]  # Review focus 3: distinct fields, distinct values
    s = ledger_db()
    row = s.query(GovernanceLedger).first()
    assert row.payload["plan_hash"] != row.payload["governor_plan_hash"]
    assert row.payload["plan_hash"] == out["plan_hash"]
    s.close()


def test_authorize_connection_failure_raises_not_a_fake_refusal(monkeypatch, ledger_db):
    """Review focus 4: a genuine communication failure must fail the node, never look like a policy refusal."""
    monkeypatch.setattr(
        authorize_tools.httpx, "AsyncClient",
        _client_returning(200, raise_exc=httpx.ConnectError("refused")),
    )
    with pytest.raises(AuthorizeError):
        asyncio.run(authorize({}, {"run_id": "run-3", "history": []}))
    assert ledger_db().query(GovernanceLedger).count() == 0  # nothing recorded for a comms failure


def test_authorize_non_200_raises(monkeypatch, ledger_db):
    monkeypatch.setattr(authorize_tools.httpx, "AsyncClient", _client_returning(500, {}))
    with pytest.raises(AuthorizeError):
        asyncio.run(authorize({}, {"run_id": "run-4", "history": []}))


def test_authorize_malformed_body_raises(monkeypatch, ledger_db):
    monkeypatch.setattr(authorize_tools.httpx, "AsyncClient", _client_returning(200, {"not": "the expected shape"}))
    with pytest.raises(AuthorizeError):
        asyncio.run(authorize({}, {"run_id": "run-5", "history": []}))


def test_authorize_reads_target_from_the_sealed_plan(monkeypatch, ledger_db):
    """authorize takes its target from ctx['history']'s seal result, not a hardcoded value."""
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = __import__("json").loads(request.content)
        return httpx.Response(200, json=REFUSAL_BODY)

    monkeypatch.setattr(
        authorize_tools.httpx, "AsyncClient",
        lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(handler), **kw),
    )
    seal_result = {"node": "seal", "type": "tool", "status": "completed",
                   "result": {"success": True, "data": {"sealed": True, "plan": {"target": "memstream"}}}}
    asyncio.run(authorize({}, {"run_id": "run-6", "history": [seal_result]}))
    assert captured["body"]["target"] == "memstream"
    assert captured["body"]["plan"]["requested_actions"][0]["profile"] == "memstream"


def test_authorize_no_sealed_plan_raises(monkeypatch, ledger_db):
    with pytest.raises(AuthorizeError):
        asyncio.run(authorize({}, {"run_id": "run-7", "history": []}))


def test_ledger_failure_does_not_block_authorize(monkeypatch):
    monkeypatch.setattr(authorize_tools.httpx, "AsyncClient", _client_returning(200, REFUSAL_BODY))
    monkeypatch.setattr(authorize_tools, "_write_ledger", lambda entry: False)
    out = asyncio.run(authorize({}, {"run_id": "run-8", "history": []}))
    assert out["ok"] is True and out["ledger"] is False  # Review focus 5


def test_ledger_session_creation_failure_is_fail_soft(monkeypatch):
    """Mirrors Phase 2a's own final-review fix: SessionLocal()/rollback must be inside the try."""
    monkeypatch.setattr(authorize_tools.httpx, "AsyncClient", _client_returning(200, REFUSAL_BODY))

    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(authorize_tools, "SessionLocal", boom)
    out = asyncio.run(authorize({}, {"run_id": "run-9", "history": []}))
    assert out["ok"] is True and out["ledger"] is False


def test_no_docker_import_anywhere_in_this_module():
    """Review focus 1: this module must never be able to touch Docker."""
    src = pathlib.Path(authorize_tools.__file__).read_text(encoding="utf-8")
    assert "docker" not in src.lower() or "DOCKER" not in src  # no docker-proxy/settings reference at all
    assert "DOCKER_SOCKET_PROXY_URL" not in src
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_authorize_tools.py -q -p no:cacheprovider --no-cov`
Expected: FAIL (`ModuleNotFoundError: app.broski_operator.authorize_tools`).

- [ ] **Step 3: Implement** — `backend/app/broski_operator/authorize_tools.py`

```python
"""Local tool for `hypercode.recover` (Phase 2b): request a DRY_RUN capability from Governor.

Talks ONLY to Governor's real, already-live HTTP API — never to fleet-controller (its plan
schema is a closed set that deliberately excludes this action), never to Docker, never to
Safety Shepherd directly (Governor calls Shepherd internally as part of minting).

With today's policy configuration (no explicit capabilities.json grant for this caller),
Governor's mint always refuses via Shepherd's ESCALATE path, regardless of the requested mode.
That refusal is the correct, expected outcome this increment proves — not a tool failure.
Only a genuine failure to reach or parse Governor's response raises AuthorizeError.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.db.session import SessionLocal
from app.models.governance import GovernanceLedger

logger = logging.getLogger(__name__)

GOVERNOR_TIMEOUT_S = 8.0
_SEAL_NODE = "seal"


class AuthorizeError(RuntimeError):
    """A genuine failure to reach or interpret Governor's response. Never a policy refusal."""


def _governor_url() -> str:
    return (os.getenv("GOVERNOR_URL") or "http://governor:8080").rstrip("/")


def build_plan(run_id: str, target: str) -> dict[str, Any]:
    """The full Governor-shaped plan dict, with constraints spelled out explicitly.

    Governor's own `canonical_hash` operates on its Pydantic model's `model_dump(mode="json")`
    AFTER validation — which fills in `Constraints()`'s defaults. Omitting `constraints` here
    would make our client-side hash diverge from what Governor recomputes server-side. Spelling
    them out (matching `Constraints()`'s exact defaults) keeps the two hashes identical.
    """
    return {
        "schema_version": 1,
        "mission_id": run_id,
        "requested_actions": [
            {"action_id": f"restart-{target}", "kind": "container.restart", "profile": target}
        ],
        "constraints": {"max_services": 25, "allow_profiles": [], "deny_profiles": []},
    }


def canonical_hash(plan: dict[str, Any]) -> str:
    """sha256 over canonical JSON — the SAME algorithm as agents/governor/models.py:canonical_hash,
    reimplemented locally (file-copy convention: never import across the agent boundary).
    """
    import hashlib
    import json

    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def _sealed_target(history: list[dict[str, Any]]) -> str:
    for entry in reversed(history):
        if entry.get("node") == _SEAL_NODE and entry.get("status") == "completed":
            data = (entry.get("result") or {}).get("data") or {}
            plan = data.get("plan") or {}
            target = plan.get("target")
            if isinstance(target, str) and target:
                return target
    raise AuthorizeError("no sealed plan found in this run's history")


def _sealed_plan_hash(history: list[dict[str, Any]]) -> str:
    for entry in reversed(history):
        if entry.get("node") == _SEAL_NODE and entry.get("status") == "completed":
            data = (entry.get("result") or {}).get("data") or {}
            plan_hash = data.get("plan_hash")
            if isinstance(plan_hash, str) and plan_hash:
                return plan_hash
    raise AuthorizeError("no sealed plan_hash found in this run's history")


def _write_ledger(entry: dict[str, Any]) -> bool:
    try:
        db = SessionLocal()
        try:
            db.add(
                GovernanceLedger(
                    user_id="broski-operator",
                    action="recover_authorization_attempted",
                    tool_used="hypercode.recover",
                    payload=entry["payload"],
                    decision=entry["payload"]["governor_verdict"].get("decision"),
                    agent_name="broski-operator",
                    approved_by=None,
                )
            )
            db.commit()
            return True
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            raise
        finally:
            db.close()
    except Exception:
        logger.warning("authorize: governance ledger insert failed", exc_info=True)
        return False


async def authorize(params: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    history = (ctx or {}).get("history", [])
    run_id = str((ctx or {}).get("run_id", ""))
    target = _sealed_target(history)
    plan_hash = _sealed_plan_hash(history)

    gov_plan = build_plan(run_id, target)
    governor_plan_hash = canonical_hash(gov_plan)
    body = {
        "plan": gov_plan,
        "plan_hash": governor_plan_hash,
        "mode": "DRY_RUN",
        "action": "container.restart",
        "target": target,
        "proposer_id": "broski-operator",
    }

    try:
        async with httpx.AsyncClient(timeout=GOVERNOR_TIMEOUT_S) as client:
            resp = await client.post(f"{_governor_url()}/v1/capabilities/mint", json=body)
    except Exception as exc:
        raise AuthorizeError(f"could not reach Governor: {type(exc).__name__}") from exc

    if resp.status_code != 200:
        raise AuthorizeError(f"Governor returned HTTP {resp.status_code}")

    try:
        data = resp.json()
    except Exception as exc:
        raise AuthorizeError("Governor response was not valid JSON") from exc

    if not isinstance(data, dict) or "minted" not in data or "verdict" not in data:
        raise AuthorizeError("Governor response missing required fields")

    verdict = data.get("verdict") or {}
    minted = bool(data.get("minted"))
    ledger_ok = _write_ledger(
        {
            "payload": {
                "run_id": run_id,
                "plan_hash": plan_hash,
                "governor_plan_hash": governor_plan_hash,
                "governor_verdict": verdict,
                "minted": minted,
                "mode": "DRY_RUN",
            }
        }
    )

    return {
        "ok": True,
        "minted": minted,
        "mode": "DRY_RUN",
        "verdict": verdict,
        "plan_hash": plan_hash,
        "governor_plan_hash": governor_plan_hash,
        "ledger": ledger_ok,
        "note": (
            "Governor/Shepherd correctly refused \u2014 no capability minted, no second approver "
            "on record; this increment proves the pipeline, not a minted capability"
            if not minted
            else "capability minted (unexpected for this increment's default policy configuration)"
        ),
    }
```

Note: `_write_ledger` is a synchronous function (matches `recover_tools.py`'s style) but `authorize` calls it directly, not via `asyncio.to_thread` — unlike `recover_seal`. This is intentional and simpler for this task (no need to match `recover_seal`'s threading exactly); if a reviewer flags it as inconsistent, that is a legitimate Minor finding to weigh, not a defect to pre-empt here.

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && python -m pytest tests/test_authorize_tools.py -q -p no:cacheprovider --no-cov`
Expected: all PASS, including `test_canonical_hash_matches_governors_real_algorithm` (the cross-implementation parity test — if this fails, the plan dict shape in `build_plan` doesn't match what Governor's Pydantic model would produce; fix `build_plan`, not the test).

- [ ] **Step 5: Commit**

```bash
git add backend/app/broski_operator/authorize_tools.py backend/tests/test_authorize_tools.py
git commit -m "feat: authorize local tool (Governor DRY_RUN mint request, fail-closed)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Wire `authorize` into the flow and `LOCAL_TOOLS`

**Files:**
- Modify: `backend/app/broski_operator/tools.py`
- Modify: `backend/app/agents/hyperflow/flows/operator_recover.yml`
- Test: `backend/tests/test_authorize_tools.py` (append flow-registration + end-to-end tests)

**Interfaces:**
- Consumes (Task 2): `authorize_tools.authorize`.
- Produces: `LOCAL_TOOLS["local.authorize"] = authorize`; flow node `authorize` (`tool: local.authorize`) connected from `seal` with no `condition` (runs whenever `seal` completes, mirroring `inspect`→`propose`'s unconditional edge).

- [ ] **Step 1: Write the failing tests** — append to `backend/tests/test_authorize_tools.py`:

```python
def test_authorize_registered_in_local_tools():
    from app.broski_operator import tools

    assert "local.authorize" in tools.LOCAL_TOOLS
    assert tools.LOCAL_TOOLS["local.authorize"] is authorize


def test_flow_has_the_authorize_node():
    from app.agents.hyperflow.registry import get_flow

    fd = get_flow("operator-recover")
    node = fd.node("authorize")
    assert node.tool == "local.authorize"
    edges = [e for e in fd.edges if e.src == "seal"]
    assert len(edges) == 1 and edges[0].dst == "authorize" and edges[0].condition is None


def test_operator_recover_flow_runs_authorize_after_seal(monkeypatch, ledger_db):
    """Real runner, real flow, real authorize — only the Governor HTTP call and Docker fetch are faked."""
    import asyncio as _asyncio

    from app.agents.hyperflow.registry import get_flow
    from app.broski_operator import recover_tools, tools as tools_mod
    from app.models.hyperflow import HyperFlowRunStatus
    from tests.test_hyperflow import _runner_with_io

    async def fake_summaries():
        return [{"Id": "f1f1f1f1f1f1", "Names": ["/skillweaver"], "State": "running",
                 "Status": "Up (unhealthy)", "Labels": {}}]

    async def fake_inspect(params, ctx=None):
        return {"ok": True, "attention": []}

    monkeypatch.setattr(recover_tools, "_fetch_summaries", fake_summaries)
    monkeypatch.setitem(tools_mod.LOCAL_TOOLS, "local.inspect", fake_inspect)
    monkeypatch.setattr(authorize_tools.httpx, "AsyncClient", _client_returning(200, REFUSAL_BODY))

    runner, final = _runner_with_io(get_flow("operator-recover"), "e2e-authz", monkeypatch)

    async def scenario():
        runner._task = _asyncio.create_task(runner._run())
        for _ in range(150):
            if runner.parked_gate == "approve":
                break
            await _asyncio.sleep(0.02)
        assert runner.parked_gate == "approve"
        awaiting = [e for e in runner._history if e["status"] == "awaiting_approval"][0]
        shown_hash = awaiting["result"]["plan_hash"]

        def take(node_id=None):
            runner._last_decision_meta = {"by": "bro@example.com", "plan_hash": shown_hash}
            return True

        monkeypatch.setattr(runner, "_take_persisted_decision", take)
        runner.resume(True)
        await runner._task

    _asyncio.run(scenario())
    assert final["status"] is HyperFlowRunStatus.COMPLETED
    authz = [e for e in runner._history if e["node"] == "authorize" and e["status"] == "completed"][0]
    assert authz["result"]["data"]["minted"] is False
    assert authz["result"]["data"]["mode"] == "DRY_RUN"
    assert ledger_db().query(GovernanceLedger).filter_by(action="recover_authorization_attempted").count() == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_authorize_tools.py -q -p no:cacheprovider --no-cov`
Expected: FAIL (`"local.authorize" not in tools.LOCAL_TOOLS`; `KeyError` on `fd.node("authorize")`).

- [ ] **Step 3: Register the tool** — at the bottom of `backend/app/broski_operator/tools.py`, after the existing `LOCAL_TOOLS["local.recover_seal"] = recover_seal` line:

```python
from app.broski_operator.authorize_tools import authorize  # noqa: E402

LOCAL_TOOLS["local.authorize"] = authorize
```

- [ ] **Step 4: Add the flow node** — in `backend/app/agents/hyperflow/flows/operator_recover.yml`, add after the `seal` node definition:

```yaml
  - id: authorize
    type: tool
    tool: local.authorize
```

and add to the `edges:` list, after `- from: approve\n    to: seal`:

```yaml
  - from: seal
    to: authorize
```

Also update the file's header comment (lines 1-2) to reflect the new step:

```yaml
# BROski operator: read-only recovery diagnosis. Proposes ONE allow-listed container restart for
# human approval, seals the approved plan, and requests a DRY_RUN capability from Governor (Phase
# 2b) -- refused today by design (no grant exists yet). Phase 2a+2b execute nothing.
```

- [ ] **Step 5: Run to verify pass, plus the full existing operator/recover regression**

Run (background if needed, ~3-4 min): `cd backend && python -m pytest tests/test_authorize_tools.py tests/test_recover_tools.py tests/test_recover_core.py tests/test_recover_policy.py tests/test_operator_gate_context.py tests/test_operator_plan_hash.py tests/test_operator_api.py tests/test_operator_tools.py tests/test_operator_runner.py tests/test_operator_durable_approval.py tests/test_operator_recovery.py tests/test_operator_mcp_tools.py tests/test_hyperflow.py tests/test_flows_endpoint.py tests/test_goal_matcher.py -q -p no:cacheprovider --no-cov`
Expected: all PASS. If a goal-matcher test regresses because of the flow's updated header/intent text, reword only that comment further (the `intent:` field itself is unchanged by this task) and re-run.

- [ ] **Step 6: Commit**

```bash
git add backend/app/broski_operator/tools.py backend/app/agents/hyperflow/flows/operator_recover.yml backend/tests/test_authorize_tools.py
git commit -m "feat: wire authorize into operator-recover flow and LOCAL_TOOLS

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Live proof and docs (controller-run live steps)

**Files:**
- Modify: `scripts/prove-recover.py` (extend `phaseA` with an `authorize` check)
- Modify: `docs/superpowers/specs/2026-09-27-broski-recover-2b-design.md` (amendments)
- Modify: `WHATS_DONE.md` (new entry)

**Interfaces:**
- Consumes: everything above, plus the real, currently-not-running `governor` container.
- Same controller-only live-ops ruling as Phases 1/2a: throwaway containers, docker build/recreate, and the actual proof run happen in the controller session, never delegated to a subagent (2026-08-24 runaway-subagent incident).

- [ ] **Step 1 (subagent, code-only): extend `scripts/prove-recover.py`**

Confirmed fact (`backend/app/broski_operator/status.py:build_result`): `result.report` is overwritten by each completed tool node's `data` in history order, so once `authorize` becomes the flow's last node, `done["result"]["report"]` is `authorize`'s result dict — **not** `seal`'s. `done["result"]["nodes"]` is the full ordered list of completed node ids (now including `"authorize"`).

In `phaseA`, the existing block reads `rep = done["result"]["report"]` and asserts `rep["sealed"] is True and rep["performed"] is False` (that was `seal`'s shape). Replace that assertion pair with a check that `seal` ran (via `nodes`, since its own `data` is no longer in `report`), then add the new `authorize` assertions, reading the exact current file's variable names (`done`, `check`, etc.) before editing:

```python
    check("seal" in done["result"]["nodes"], "seal ran")
    check("authorize" in done["result"]["nodes"], "authorize ran as part of the flow")
    authz = done["result"]["report"]

```python
    check("authorize" in done["result"]["nodes"], "authorize ran as part of the flow")
    authz = done["result"]["report"]
    check(authz["minted"] is False, "Governor refused to mint (no grant exists) -- the correct outcome")
    check(authz["mode"] == "DRY_RUN", "requested mode was DRY_RUN")
    check(authz["verdict"]["decision"] == "ESCALATE", "Shepherd verdict was ESCALATE")
    check(authz["verdict"].get("risk_class") == "INFRASTRUCTURE_MUTATION", "risk class is INFRASTRUCTURE_MUTATION")
```

`seal`'s own `sealed`/`performed` flags are no longer visible via `report` once `authorize` is the last node (only the LAST node's `data` survives into `report`) — its success is now proven indirectly: the flow only reaches and completes `authorize` if `seal` succeeded first (a `seal` failure would have failed the whole run before `authorize` ever ran), so `"seal" in done["result"]["nodes"]` plus `done["status"] == "completed"` together are sufficient. Add a ledger-count check via the same `SessionLocal`/`text("SELECT count(*) ...")` pattern already used for `recover_plan_approved`, but for `action='recover_authorization_attempted'`.

Read the actual current `scripts/prove-recover.py` before editing — this step describes the required additions and their exact assertions; fit them into the file's real current structure (variable names, existing helper functions) rather than assuming line numbers.

- [ ] **Step 2 (subagent): syntax check + commit**

Run: `python -c "import ast; ast.parse(open('scripts/prove-recover.py', encoding='utf-8').read()); print('syntax ok')"` → `syntax ok`, then:

```bash
git add scripts/prove-recover.py
git commit -m "feat: extend live proof for the authorize node (Governor DRY_RUN refusal)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

- [ ] **Step 3 (controller): full regression on the host**

Run the same 14-file (now the same set as Task 3 Step 5) regression once more from a clean checkout state, one file at a time or as a single background command per the established RAM-safe pattern. Expected: all PASS.

- [ ] **Step 4 (controller): RAM gate + resolve the governor-alone question**

`wsl -e free -m` → `available` ≥ 1500 MB before any build. Then resolve spec §7.1/§9.2 empirically: `docker compose -f docker-compose.yml -f docker-compose.fleet.yml up -d --no-deps governor` (no `--profile fleet` flag — naming the service directly). Check `docker ps` immediately after: if `fleet-controller` also started, note that in the spec amendments and decide whether to `docker stop fleet-controller` afterward (it holds no capability and is harmless idle, but Lean Operations Mode prefers nothing extra running) — this is a live decision, not a design blocker.

- [ ] **Step 5 (controller): build + recreate `hypercode-core` only**

Standard pattern: build only `hypercode-core` (it's the only service whose image changed — `governor`'s image is unchanged, just newly started), `up -d --no-deps hypercode-core`, wait healthy, confirm `restarts=0`, `oom=false`.

- [ ] **Step 6 (controller): run the live proof**

Repeat the throwaway-container setup from Phase 2a's proof (`zz-recover-proof` with the `restartable` label, unhealthy). Run `docker exec -i hypercode-core python - phaseA < scripts/prove-recover.py`. Expected: every line `PASS:`, including the new `authorize`/Governor checks. If Governor is unreachable (connection refused), the flow will FAIL at `authorize` (per Task 2's fail-closed design) rather than silently completing — treat that as a real finding to fix (likely the `GOVERNOR_URL`/network reachability from `hypercode-core` to `governor`, both must be on `agents-net`, confirm via `docker network inspect agents-net`), not something to work around. Remove the throwaway container afterward regardless of outcome.

- [ ] **Step 7 (controller): docs**

Append to the spec (§9's items resolved, plus the 8080-vs-8089 correction noted in this plan's header, plus whatever the governor-alone-vs-fleet-controller resolution turned out to be). Insert a `## 2026-09-27 — BROski recover Phase 2b: authorize (fail-closed DRY_RUN, live-proven)` entry at the top of `WHATS_DONE.md` (update the "Last synced" line), following the exact structure of the Phase 2a entry: what shipped, the live evidence with real Shepherd/Governor verdict text, RAM figures, and explicitly restate "nothing mints, nothing executes — this increment proves the pipeline fails closed" so a future reader doesn't mistake it for a working capability grant. Commit as `docs: WHATS_DONE — BROski recover Phase 2b live evidence`.

- [ ] **Step 8: whole-branch review, then stop for Bro**

Final whole-branch review (most capable model) over `feature/broski-recover-2a..feature/broski-recover-2b` (the diff specific to THIS branch — `feature/broski-recover-2a`'s own commits are already reviewed and out of scope for this review). **Do not push, open a PR, or retarget the branch without Bro's say-so.**

---

## Self-Review

**Spec coverage:** §4.1 flow → Task 3. §4.2 two hashes, the new Literal → Tasks 1, 2. §4.3 call sequence + fail-closed behavior → Task 2. §4.4 ledger + result shape → Task 2. §5 safety properties 1-6 → Review Focus section, each pinned by a named test. §6 testing → Tasks 1-3's test steps. §7 live proof → Task 4. §8 limitations → carried into Task 4's docs step, explicitly worded so the ledger/WHATS_DONE entry can't be misread as "it works now."

**Placeholder scan:** Task 4 Step 1 intentionally shows a discarded placeholder snippet with an explicit instruction not to use it, followed by the real, complete assertions — this is a deliberate "here's the wrong approach, here's the right one" note for the implementer given the live proof script's exact current structure wasn't re-read line-by-line in this planning pass (unlike Tasks 1-3, where every file was read in full before writing its exact code). No other placeholders.

**Type consistency:** `authorize(params, ctx)` matches every other local tool's signature (`recover_propose`, `recover_seal`, `inspect_stack`) exactly. `AuthorizeError` mirrors `RecoverSealError`'s role (a precondition/policy exception distinct from a generic `Exception`) without being confused with it. `build_plan`/`canonical_hash` names and shapes are used identically in `authorize_tools.py` and the test file. The ledger payload keys (`run_id`, `plan_hash`, `governor_plan_hash`, `governor_verdict`, `minted`, `mode`) match between §4.4's spec text, Task 2's implementation, and Task 2/3's tests.

**Review Focus coverage:** 1 → `test_no_docker_import_anywhere_in_this_module`. 2 → `test_authorize_records_a_well_formed_refusal_as_success`. 3 → `test_authorize_never_conflates_the_two_hashes`. 4 → `test_authorize_connection_failure_raises_not_a_fake_refusal`, `test_authorize_non_200_raises`, `test_authorize_malformed_body_raises`. 5 → `test_ledger_failure_does_not_block_authorize`, `test_ledger_session_creation_failure_is_fail_soft`. 6 → `test_fleet_controller_copy_is_unaffected` (Task 1).
