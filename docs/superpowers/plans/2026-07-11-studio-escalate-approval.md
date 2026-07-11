# Studio ESCALATE Approval Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `coder-studio`'s auto-denied `ESCALATE` verdict into an interactive approve/deny gate, surfaced inline in `/ide`, resolved in-process with a fail-closed timeout.

**Architecture:** The Safety Shepherd gate callback is already `async` and runs *inside* the agent's suspended tool call. On `ESCALATE` it now awaits a per-session `asyncio.Event` instead of denying. An HTTP endpoint sets that event from a human click. Both live in the same `coder-studio` process, so an in-memory registry + `asyncio` primitives are the correct synchronisation. The approval flows to the browser over the session's existing SSE stream; no Redis, no orchestrator, no `ApprovalModal`.

**Tech Stack:** Python 3.13 · FastAPI · Claude Agent SDK · pytest (`asyncio_mode = auto`) · Next.js/React · vitest + @testing-library/react.

**Spec:** `docs/superpowers/specs/2026-07-11-studio-escalate-approval-design.md`

## Global Constraints

- Branch: `feat/studio-escalate-approval` (already created off `origin/main`). Commit continuously; `git fetch` + `--force-with-lease` only, never plain force-push.
- Commit prefixes: `feat:` / `fix:` / `docs:` / `test:` / `chore:` only.
- Python: absolute imports, 4-space indent. `coder-studio` modules import as top-level (`from sessions import ...`), matching the existing files.
- Fail-closed: any `ESCALATE` outcome that is not an explicit human `approved` returns `PermissionResultDeny`.
- Preserve the existing safe default: `make_gate(...)` / `run_agent(...)` with **no** `resolve_escalation` must still deny `ESCALATE` immediately.
- `STUDIO_APPROVAL_TIMEOUT` env, default `300` (seconds). Read at call time, never frozen at import.
- Settlement is atomic and first-wins via `Approval.settle()`; the entry is removed in a `finally` after resolution.
- Single-process assumption is intentional (see spec §3.1); do not add Redis/shared state.
- Endpoint contract: `200` accepted / concurrent-idempotent, `404` unknown-or-already-cleaned, `409` concurrent opposite human decision.
- Tests: bare `async def test_...` (no marker needed). Follow the existing seam-isolation style in `test_main.py` — never combine TestClient + background task + SSE polling (it deadlocks under the test portal).
- Run backend tests from `agents/coder-studio/` with `python -m pytest <file> -v`.
- Run frontend tests from `agents/dashboard/` with `npm run test -- <file>`.

---

## File Structure

**Backend (`agents/coder-studio/`):**
- `sessions.py` — MODIFY: add `ApprovalState` enum, `Approval` dataclass (`settle()`), `Session.pending_approvals`.
- `agent_runner.py` — MODIFY: `resolve_escalation` param threaded through `make_gate` + `run_agent`; `ESCALATE` awaits it.
- `main.py` — MODIFY: `STUDIO_APPROVAL_TIMEOUT`, `_describe_target`, the wait-closure in `_drive_agent`, the `POST /sessions/{id}/approvals/{approval_id}` endpoint, discard settles pending.
- `test_approval.py` — CREATE: unit tests for the `Approval`/`settle()` primitive (race-safety core).
- `test_agent_runner.py` — MODIFY: `resolve_escalation` gate tests.
- `test_main.py` — MODIFY: endpoint + closure + discard tests.

**Frontend (`agents/dashboard/`):**
- `hooks/useStudioSession.ts` — MODIFY: two SSE kinds, `respondApproval`, exported `pendingApprovals()` helper.
- `hooks/useStudioSession.test.ts` — CREATE: `pendingApprovals()` unit tests.
- `components/views/StudioView.tsx` — MODIFY: approval card UI wired to `respondApproval`.
- `components/views/StudioView.approval.test.tsx` — CREATE: approval-card render + click test.

---

## Task 1: Approval primitive + settle() (race-safety core)

**Files:**
- Modify: `agents/coder-studio/sessions.py`
- Test: `agents/coder-studio/test_approval.py` (create)

**Interfaces:**
- Consumes: nothing (foundation task).
- Produces:
  - `ApprovalState(str, Enum)` with members `PENDING="pending"`, `APPROVED="approved"`, `DENIED="denied"`, `TIMED_OUT="timed_out"`, `DISCARDED="discarded"`.
  - `Approval` dataclass: fields `id: str`, `tool_name: str`, `target: str`, `rule: str`, `reason: str`, `expires_at: str`, `event: asyncio.Event`, `status: ApprovalState`; method `async def settle(self, decision: ApprovalState) -> ApprovalState`.
  - `Session.pending_approvals: dict[str, Approval]`.

- [ ] **Step 1: Write the failing tests**

Create `agents/coder-studio/test_approval.py`:

```python
"""Unit tests for the Approval primitive — the race-safety core of the
interactive ESCALATE gate. settle() must be atomic and first-wins."""

from __future__ import annotations

import asyncio

from sessions import Approval, ApprovalState, Session


def _approval() -> Approval:
    return Approval(
        id="ap_1", tool_name="Write", target="app.py", rule="unknown_tool",
        reason="needs a human", expires_at="2026-07-11T09:35:00Z",
    )


async def test_settle_records_the_decision_and_sets_the_event():
    ap = _approval()
    assert ap.status is ApprovalState.PENDING
    assert not ap.event.is_set()

    result = await ap.settle(ApprovalState.APPROVED)

    assert result is ApprovalState.APPROVED
    assert ap.status is ApprovalState.APPROVED
    assert ap.event.is_set()


async def test_first_settle_wins_second_is_a_noop():
    ap = _approval()

    first = await ap.settle(ApprovalState.APPROVED)
    second = await ap.settle(ApprovalState.DENIED)

    assert first is ApprovalState.APPROVED
    assert second is ApprovalState.APPROVED   # returns the settled state, no overwrite
    assert ap.status is ApprovalState.APPROVED


async def test_concurrent_settles_produce_exactly_one_winner():
    ap = _approval()

    results = await asyncio.gather(
        ap.settle(ApprovalState.APPROVED),
        ap.settle(ApprovalState.DENIED),
        ap.settle(ApprovalState.DISCARDED),
    )

    # Every caller sees the same settled status; the event is set once.
    assert len(set(results)) == 1
    assert ap.status in (ApprovalState.APPROVED, ApprovalState.DENIED, ApprovalState.DISCARDED)
    assert ap.event.is_set()


def test_session_starts_with_an_empty_approval_registry():
    s = Session(id="cs_x", prompt="do a thing")
    assert s.pending_approvals == {}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest test_approval.py -v`
Expected: FAIL — `ImportError: cannot import name 'Approval' from 'sessions'`.

- [ ] **Step 3: Implement the primitive**

In `agents/coder-studio/sessions.py`, add `import asyncio` to the imports, then add the enum + dataclass above the `Session` class:

```python
class ApprovalState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMED_OUT = "timed_out"
    DISCARDED = "discarded"


@dataclass
class Approval:
    """One escalated tool call awaiting a human decision.

    settle() is the single mutation path: the first PENDING -> terminal
    transition wins and sets the event exactly once. Later callers read the
    settled status back without overwriting it. The lock makes concurrent
    clicks / timeout / discard safe on the one event loop this runs on.
    """
    id: str
    tool_name: str
    target: str
    rule: str
    reason: str
    expires_at: str
    event: asyncio.Event = field(default_factory=asyncio.Event)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    status: ApprovalState = ApprovalState.PENDING

    async def settle(self, decision: ApprovalState) -> ApprovalState:
        async with self._lock:
            if self.status is ApprovalState.PENDING:
                self.status = decision
                self.event.set()
            return self.status
```

Then add the registry field to `Session` (after `merge_sha`):

```python
    pending_approvals: dict[str, "Approval"] = field(default_factory=dict)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest test_approval.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Confirm nothing else broke**

Run: `python -m pytest test_session_store.py -v`
Expected: PASS (unchanged).

- [ ] **Step 6: Commit**

```bash
git add agents/coder-studio/sessions.py agents/coder-studio/test_approval.py
git commit -m "feat: add atomic Approval.settle() primitive for studio escalation gate"
```

---

## Task 2: Gate learns to wait (resolve_escalation)

**Files:**
- Modify: `agents/coder-studio/agent_runner.py`
- Test: `agents/coder-studio/test_agent_runner.py`

**Interfaces:**
- Consumes: nothing from Task 1 (decoupled — the callback is injected by Task 3).
- Produces:
  - `make_gate(shepherd, worktree, on_decision=None, resolve_escalation=None)` where `resolve_escalation: Optional[Callable[[str, dict[str, Any], Verdict], Awaitable[bool]]]`.
  - `run_agent(..., resolve_escalation=None)` forwarding the same callback.
  - Behaviour: `ESCALATE` + `resolve_escalation is None` -> `PermissionResultDeny` (unchanged). `ESCALATE` + callback -> `PermissionResultAllow()` if it returns `True`, else `PermissionResultDeny`.

- [ ] **Step 1: Write the failing tests**

In `agents/coder-studio/test_agent_runner.py`, add (the `worktree` fixture, `shepherd_saying`, `ctx`, and `ESCALATE` import already exist in this file):

```python
from claude_agent_sdk import PermissionResultAllow   # add to existing imports if absent


async def test_escalate_with_approval_granted_becomes_allow(worktree):
    async def approve(tool_name, tool_input, verdict):
        return True

    gate = make_gate(shepherd_saying(ESCALATE, reason="tool not granted"), worktree,
                     resolve_escalation=approve)

    result = await gate("Write", {"file_path": "app.py"}, ctx())

    assert isinstance(result, PermissionResultAllow)


async def test_escalate_with_approval_denied_becomes_deny(worktree):
    async def deny(tool_name, tool_input, verdict):
        return False

    gate = make_gate(shepherd_saying(ESCALATE, reason="tool not granted"), worktree,
                     resolve_escalation=deny)

    result = await gate("Write", {"file_path": "app.py"}, ctx())

    assert isinstance(result, PermissionResultDeny)


async def test_escalate_receives_the_tool_and_verdict(worktree):
    seen = {}

    async def capture(tool_name, tool_input, verdict):
        seen["tool"] = tool_name
        seen["rule"] = verdict.rule
        return True

    gate = make_gate(shepherd_saying(ESCALATE, rule="unknown_tool"), worktree,
                     resolve_escalation=capture)

    await gate("Write", {"file_path": "app.py"}, ctx())

    assert seen == {"tool": "Write", "rule": "unknown_tool"}
```

The existing `test_escalate_denies_rather_than_allowing` (no callback) stays and now documents the preserved default — leave it unchanged.

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `python -m pytest test_agent_runner.py -k "approval_granted or approval_denied or receives_the_tool" -v`
Expected: FAIL — `make_gate() got an unexpected keyword argument 'resolve_escalation'`.

- [ ] **Step 3: Implement**

In `agents/coder-studio/agent_runner.py`:

Add to the typing import line: `Awaitable` (i.e. `from typing import Any, AsyncIterator, Awaitable, Callable, Optional`).

Add near `DecisionSink`:

```python
EscalationResolver = Callable[[str, dict[str, Any], Any], Awaitable[bool]]
```

Change `make_gate` signature and the `ESCALATE` branch:

```python
def make_gate(
    shepherd: ShepherdClient,
    worktree: Worktree,
    on_decision: Optional[DecisionSink] = None,
    resolve_escalation: Optional[EscalationResolver] = None,
):
    ...
        if verdict.decision == ESCALATE:
            if resolve_escalation is None:
                # Preserved safe default: no approval wired -> fail closed.
                return PermissionResultDeny(
                    message=f"Needs human approval ({verdict.rule}): {verdict.reason}"
                )
            approved = await resolve_escalation(tool_name, tool_input, verdict)
            if approved:
                return PermissionResultAllow()
            return PermissionResultDeny(message="Denied by human review (or timed out)")
```

Thread it through `run_agent`:

```python
async def run_agent(
    worktree: Worktree,
    shepherd: ShepherdClient,
    prompt: str,
    *,
    model: Optional[str] = None,
    env: Optional[dict[str, str]] = None,
    on_decision: Optional[DecisionSink] = None,
    resolve_escalation: Optional[EscalationResolver] = None,
) -> AsyncIterator[Any]:
    ...
    gate = make_gate(shepherd, worktree, on_decision=on_decision, resolve_escalation=resolve_escalation)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_agent_runner.py -v`
Expected: PASS (all, including the preserved `test_escalate_denies_rather_than_allowing`).

- [ ] **Step 5: Commit**

```bash
git add agents/coder-studio/agent_runner.py agents/coder-studio/test_agent_runner.py
git commit -m "feat: let the studio gate await a human decision on ESCALATE"
```

---

## Task 3: Wait closure + SSE events + timeout

**Files:**
- Modify: `agents/coder-studio/main.py`
- Test: `agents/coder-studio/test_main.py`

**Interfaces:**
- Consumes: `Approval`, `ApprovalState`, `Session.pending_approvals` (Task 1); `run_agent(..., resolve_escalation=...)` (Task 2).
- Produces:
  - `STUDIO_APPROVAL_TIMEOUT` env read via a module-level default `int(os.getenv("STUDIO_APPROVAL_TIMEOUT", "300"))`.
  - `_describe_target(tool_name: str, tool_input: dict) -> str`.
  - `_make_escalation_resolver(session: Session) -> EscalationResolver` — registers an `Approval` (before emitting SSE), emits `approval_request`, awaits with timeout, emits `approval_resolved`, cleans up in `finally`, returns `bool`.
  - `_drive_agent` passes `resolve_escalation=_make_escalation_resolver(session)` to `run_agent`.
  - Two new SSE event kinds emitted: `approval_request`, `approval_resolved`.

- [ ] **Step 1: Write the failing tests**

In `agents/coder-studio/test_main.py`, add:

```python
import asyncio
from sessions import Approval, ApprovalState   # add alongside existing sessions imports


def _seed_session_with_pending(store, approval_id="ap_1"):
    session = store.create("do a thing")
    ap = Approval(id=approval_id, tool_name="Write", target="app.py",
                  rule="unknown_tool", reason="needs a human",
                  expires_at="2026-07-11T09:35:00Z")
    session.pending_approvals[approval_id] = ap
    return session, ap


async def test_resolver_returns_true_when_approved(monkeypatch):
    monkeypatch.setenv("STUDIO_APPROVAL_TIMEOUT", "5")
    session = main.store.create("t")
    resolve = main._make_escalation_resolver(session)

    from shepherd import Verdict
    verdict = Verdict("ESCALATE", "tool not granted", "unknown_tool")

    async def approve_soon():
        await asyncio.sleep(0.01)
        # exactly one approval was registered
        ap = next(iter(session.pending_approvals.values()))
        await ap.settle(ApprovalState.APPROVED)

    granted, _ = await asyncio.gather(
        resolve("Write", {"file_path": "app.py"}, verdict),
        approve_soon(),
    )
    assert granted is True
    # cleaned up after resolution
    assert session.pending_approvals == {}
    # SSE trail: an approval_request then an approval_resolved(approved)
    kinds = [(e.kind, e.data.get("status")) for e in session.events]
    assert ("approval_request", None) in kinds
    assert ("approval_resolved", "approved") in kinds


async def test_resolver_denies_on_timeout(monkeypatch):
    monkeypatch.setenv("STUDIO_APPROVAL_TIMEOUT", "0")   # expire immediately
    session = main.store.create("t")
    resolve = main._make_escalation_resolver(session)

    from shepherd import Verdict
    granted = await resolve("Write", {"file_path": "app.py"},
                            Verdict("ESCALATE", "r", "unknown_tool"))

    assert granted is False
    assert session.pending_approvals == {}
    assert any(e.kind == "approval_resolved" and e.data["status"] == "timed_out"
               for e in session.events)


async def test_resolver_registers_before_emitting_sse(monkeypatch):
    """A fast UI must never see approval_request before the entry exists."""
    monkeypatch.setenv("STUDIO_APPROVAL_TIMEOUT", "5")
    session = main.store.create("t")
    order = []
    real_add = session.add_event

    def spy(kind, data):
        if kind == "approval_request":
            # registry must already hold the approval at emit time
            order.append(("registered", len(session.pending_approvals) == 1))
        return real_add(kind, data)

    session.add_event = spy   # type: ignore[method-assign]
    resolve = main._make_escalation_resolver(session)

    from shepherd import Verdict

    async def approve_soon():
        await asyncio.sleep(0.01)
        ap = next(iter(session.pending_approvals.values()))
        await ap.settle(ApprovalState.APPROVED)

    await asyncio.gather(
        resolve("Write", {"file_path": "app.py"}, Verdict("ESCALATE", "r", "unknown_tool")),
        approve_soon(),
    )
    assert order == [("registered", True)]
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_main.py -k "resolver" -v`
Expected: FAIL — `AttributeError: module 'main' has no attribute '_make_escalation_resolver'`.

- [ ] **Step 3: Implement in `main.py`**

Add the env default near the other module constants:

```python
# Seconds the gate waits for a human before failing closed on an escalation.
STUDIO_APPROVAL_TIMEOUT = int(os.getenv("STUDIO_APPROVAL_TIMEOUT", "300"))
```

Add imports at the top: `import uuid`, `from datetime import datetime, timedelta, timezone`, and extend the sessions import to `from sessions import Approval, ApprovalState, Session, SessionStore, Status`.

Add the helpers (near `_drive_agent`):

```python
def _describe_target(tool_name: str, tool_input: dict[str, Any]) -> str:
    """A short, human-readable subject for the approval card."""
    for key in ("file_path", "notebook_path", "path"):
        value = tool_input.get(key)
        if value:
            return str(value)
    if tool_name == "Bash":
        return str(tool_input.get("command", ""))
    if tool_name in ("WebFetch", "WebSearch"):
        return str(tool_input.get("url", ""))
    return tool_name


def _make_escalation_resolver(session: Session):
    """Build the resolve_escalation callback bound to one session.

    Registers the approval BEFORE emitting SSE (so a fast click can't beat the
    entry into existence), awaits a human up to STUDIO_APPROVAL_TIMEOUT, then
    always removes the entry. Returns True only for an explicit approval.
    """
    async def resolve(tool_name: str, tool_input: dict[str, Any], verdict) -> bool:
        approval_id = f"ap_{uuid.uuid4().hex[:12]}"
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=STUDIO_APPROVAL_TIMEOUT)).isoformat()
        approval = Approval(
            id=approval_id,
            tool_name=tool_name,
            target=_describe_target(tool_name, tool_input),
            rule=getattr(verdict, "rule", ""),
            reason=getattr(verdict, "reason", ""),
            expires_at=expires_at,
        )
        session.pending_approvals[approval_id] = approval          # (1) register first
        session.add_event("approval_request", {                    # (2) then emit
            "approval_id": approval_id,
            "tool_name": approval.tool_name,
            "target": approval.target,
            "rule": approval.rule,
            "reason": approval.reason,
            "expires_at": approval.expires_at,
        })
        try:
            try:
                await asyncio.wait_for(approval.event.wait(), timeout=STUDIO_APPROVAL_TIMEOUT)
                status = approval.status
            except asyncio.TimeoutError:
                status = await approval.settle(ApprovalState.TIMED_OUT)
            session.add_event("approval_resolved", {
                "approval_id": approval_id, "status": status.value,
            })
            return status is ApprovalState.APPROVED
        finally:
            session.pending_approvals.pop(approval_id, None)       # (7) always clean up

    return resolve
```

Wire it into `_drive_agent` — change the `_run_agent_with_timeout` call to pass the resolver. First extend `_run_agent_with_timeout` to accept + forward it:

```python
async def _run_agent_with_timeout(
    worktree,
    shep: ShepherdClient,
    prompt: str,
    *,
    model: str | None,
    on_decision,
    resolve_escalation=None,
) -> AsyncIterator[Any]:
    async with asyncio.timeout(AGENT_TIMEOUT_SECONDS):
        async for message in run_agent(
            worktree, shep, prompt,
            model=model, on_decision=on_decision, resolve_escalation=resolve_escalation,
        ):
            yield message
```

Then in `_drive_agent`, pass the resolver:

```python
        async for message in _run_agent_with_timeout(
            session.worktree,
            shepherd(),
            session.prompt,
            model=model,
            on_decision=lambda d: session.add_event("decision", d),
            resolve_escalation=_make_escalation_resolver(session),
        ):
```

> Note on the timeout interaction: the per-approval wait (`STUDIO_APPROVAL_TIMEOUT`, 300s) sits inside the per-run `AGENT_TIMEOUT_SECONDS` (1200s). A single walk-away denies in 5 min and the agent continues; the 20-min ceiling still bounds the whole run.

- [ ] **Step 4: Run to verify they pass**

Run: `python -m pytest test_main.py -k "resolver" -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Full backend regression**

Run: `python -m pytest test_main.py test_approval.py test_agent_runner.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add agents/coder-studio/main.py agents/coder-studio/test_main.py
git commit -m "feat: studio waits for human approval on ESCALATE with a fail-closed timeout"
```

---

## Task 4: Approval endpoint + discard safety

**Files:**
- Modify: `agents/coder-studio/main.py`
- Test: `agents/coder-studio/test_main.py`

**Interfaces:**
- Consumes: `Approval.settle()` (Task 1), `Session.pending_approvals`, the resolver (Task 3).
- Produces:
  - `class ApprovalDecision(BaseModel)` with `decision: str` (`"approved"` | `"denied"`).
  - `POST /sessions/{session_id}/approvals/{approval_id}` returning `{"status": <settled>}` with codes `200` / `404` / `409`.
  - `discard()` settles every pending approval as `DISCARDED` before cancelling the task.

- [ ] **Step 1: Write the failing tests**

In `test_main.py` add (uses the existing `client` fixture / `KEY`; check the file's top for the exact fixture name and reuse it — the pattern below assumes a `TestClient(main.app)` with the `X-Agent-Key` header helper already present):

```python
def test_approve_endpoint_settles_the_approval(client):
    session, ap = _seed_session_with_pending(main.store, "ap_ok")
    res = client.post(f"/sessions/{session.id}/approvals/ap_ok",
                      json={"decision": "approved"}, headers=auth())
    assert res.status_code == 200
    assert res.json()["status"] == "approved"
    assert ap.status is ApprovalState.APPROVED
    assert ap.event.is_set()


def test_approve_endpoint_is_idempotent_for_the_same_decision(client):
    session, ap = _seed_session_with_pending(main.store, "ap_same")
    body = {"decision": "approved"}
    first = client.post(f"/sessions/{session.id}/approvals/ap_same", json=body, headers=auth())
    second = client.post(f"/sessions/{session.id}/approvals/ap_same", json=body, headers=auth())
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "approved"


def test_opposite_decision_after_settlement_conflicts(client):
    session, ap = _seed_session_with_pending(main.store, "ap_conf")
    client.post(f"/sessions/{session.id}/approvals/ap_conf", json={"decision": "approved"}, headers=auth())
    res = client.post(f"/sessions/{session.id}/approvals/ap_conf", json={"decision": "denied"}, headers=auth())
    assert res.status_code == 409


def test_unknown_approval_is_404(client):
    session = main.store.create("t")
    res = client.post(f"/sessions/{session.id}/approvals/nope",
                      json={"decision": "approved"}, headers=auth())
    assert res.status_code == 404


def test_unknown_session_is_404(client):
    res = client.post("/sessions/cs_missing/approvals/ap",
                      json={"decision": "approved"}, headers=auth())
    assert res.status_code == 404


async def test_discard_settles_pending_approvals():
    session, ap = _seed_session_with_pending(main.store, "ap_disc")
    # No live task registered -> discard just settles + cleans. discard() reads
    # the module-global store, which _seed_session_with_pending wrote to.
    await main.discard(session.id)
    assert ap.status is ApprovalState.DISCARDED
    assert ap.event.is_set()
```

> Reuse the `client` fixture and `auth()` helper already in `test_main.py`; do not introduce a second TestClient. Note `test_discard_settles_pending_approvals` does NOT take the `client` fixture, so it runs against the module-global `main.store` — which is exactly what `main.discard` reads.

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_main.py -k "approve_endpoint or opposite_decision or unknown_approval or unknown_session or discard_settles" -v`
Expected: FAIL — `404` for a route that does not exist yet / `AttributeError`.

- [ ] **Step 3: Implement the endpoint + discard change in `main.py`**

Add the request model near the other models:

```python
class ApprovalDecision(BaseModel):
    decision: str = Field(..., pattern="^(approved|denied)$")
```

Add the endpoint (near the other `/sessions/...` routes):

```python
@app.post("/sessions/{session_id}/approvals/{approval_id}", dependencies=[Depends(require_key)])
async def resolve_approval(session_id: str, approval_id: str, body: ApprovalDecision) -> dict[str, Any]:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="no such session")
    approval = session.pending_approvals.get(approval_id)
    # Absent means it never existed OR already resolved + cleaned. Either way
    # 404 — the UI learns "already done" from the approval_resolved SSE event.
    if approval is None:
        raise HTTPException(status_code=404, detail="no such approval (never existed or already resolved)")

    requested = ApprovalState(body.decision)          # approved | denied (validated)
    final = await approval.settle(requested)
    if final is requested:
        return {"approval_id": approval_id, "status": final.value}
    if final in (ApprovalState.APPROVED, ApprovalState.DENIED):
        # A human decision already stands and this asks for the opposite.
        raise HTTPException(status_code=409, detail=f"already {final.value}")
    # Lost to timed_out / discarded — action was not allowed either way.
    return {"approval_id": approval_id, "status": final.value}
```

Update `discard()` to settle pending approvals **before** cancelling the task. After `session.set_status(Status.DISCARDED)` and before `task = _session_tasks.pop(...)`:

```python
    # Unblock any gate awaiting a human before we tear the task down, so it
    # exits its await normally rather than dying mid-flight.
    for approval in list(session.pending_approvals.values()):
        await approval.settle(ApprovalState.DISCARDED)
```

- [ ] **Step 4: Run to verify they pass**

Run: `python -m pytest test_main.py -k "approve_endpoint or opposite_decision or unknown_approval or unknown_session or discard_settles" -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Race + cleanup edge tests**

Add to `test_main.py`:

```python
async def test_discard_and_approve_race_has_one_winner(monkeypatch):
    monkeypatch.setenv("STUDIO_APPROVAL_TIMEOUT", "5")
    session = main.store.create("t")
    resolve = main._make_escalation_resolver(session)
    from shepherd import Verdict

    async def racer():
        await asyncio.sleep(0.01)
        ap = next(iter(session.pending_approvals.values()))
        # discard and approve land together
        await asyncio.gather(ap.settle(ApprovalState.DISCARDED),
                             ap.settle(ApprovalState.APPROVED))

    granted, _ = await asyncio.gather(
        resolve("Write", {"file_path": "app.py"}, Verdict("ESCALATE", "r", "unknown_tool")),
        racer(),
    )
    # Exactly one terminal status won; no hang; registry emptied.
    assert granted in (True, False)
    assert session.pending_approvals == {}


async def test_resolver_cleans_up_even_when_the_agent_task_is_cancelled(monkeypatch):
    monkeypatch.setenv("STUDIO_APPROVAL_TIMEOUT", "30")
    session = main.store.create("t")
    resolve = main._make_escalation_resolver(session)
    from shepherd import Verdict

    task = asyncio.create_task(
        resolve("Write", {"file_path": "app.py"}, Verdict("ESCALATE", "r", "unknown_tool"))
    )
    await asyncio.sleep(0.02)              # let it register + start awaiting
    assert len(session.pending_approvals) == 1
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert session.pending_approvals == {}   # finally cleared it
```

Run: `python -m pytest test_main.py -k "race or cleans_up" -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Full backend regression**

Run: `python -m pytest -v` (from `agents/coder-studio/`)
Expected: PASS (all files).

- [ ] **Step 7: Commit**

```bash
git add agents/coder-studio/main.py agents/coder-studio/test_main.py
git commit -m "feat: add studio approval endpoint (200/404/409) and discard-safe settlement"
```

---

## Task 5: Frontend hook — SSE kinds, respondApproval, derive pending

**Files:**
- Modify: `agents/dashboard/hooks/useStudioSession.ts`
- Test: `agents/dashboard/hooks/useStudioSession.test.ts` (create)

**Interfaces:**
- Consumes: the SSE `approval_request` / `approval_resolved` events (Task 3), the endpoint (Task 4), the existing `/api/studio/*` proxy.
- Produces:
  - `StreamItem` gains `{ kind: 'approval_request'; approvalId: string; toolName: string; target: string; rule: string; reason: string; expiresAt: string; seq: number }` and `{ kind: 'approval_resolved'; approvalId: string; status: string; seq: number }`.
  - Exported `pendingApprovals(stream: StreamItem[]): Extract<StreamItem, { kind: 'approval_request' }>[]`.
  - Hook return gains `respondApproval(approvalId: string, decision: 'approved' | 'denied'): Promise<void>`.

- [ ] **Step 1: Write the failing test**

Create `agents/dashboard/hooks/useStudioSession.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { pendingApprovals, type StreamItem } from './useStudioSession'

const req = (approvalId: string, seq: number): StreamItem => ({
  kind: 'approval_request', approvalId, toolName: 'Write', target: 'app.py',
  rule: 'unknown_tool', reason: 'needs a human', expiresAt: '2026-07-11T09:35:00Z', seq,
})
const resolved = (approvalId: string, seq: number): StreamItem => ({
  kind: 'approval_resolved', approvalId, status: 'approved', seq,
})

describe('pendingApprovals', () => {
  it('returns an unresolved request', () => {
    expect(pendingApprovals([req('a', 1)]).map((i) => i.approvalId)).toEqual(['a'])
  })

  it('drops a request once its resolution arrives', () => {
    expect(pendingApprovals([req('a', 1), resolved('a', 2)])).toEqual([])
  })

  it('keeps only the still-pending ones', () => {
    const stream = [req('a', 1), req('b', 2), resolved('a', 3)]
    expect(pendingApprovals(stream).map((i) => i.approvalId)).toEqual(['b'])
  })
})
```

- [ ] **Step 2: Run to verify it fails**

Run (from `agents/dashboard/`): `npm run test -- hooks/useStudioSession.test.ts`
Expected: FAIL — `pendingApprovals is not exported`.

- [ ] **Step 3: Implement in `useStudioSession.ts`**

Extend the `StreamItem` union with the two variants (matching the Interfaces block above).

Add `'approval_request'` and `'approval_resolved'` to the `KINDS` tuple:

```ts
const KINDS = ['message', 'decision', 'status', 'error', 'approval_request', 'approval_resolved', 'end'] as const
```

In the `addEventListener` handler, add branches before the final `else` (the SSE payload uses snake_case; map to camelCase):

```ts
} else if (kind === 'approval_request') {
  dispatch({
    type: 'item',
    item: {
      kind: 'approval_request',
      approvalId: String(data.approval_id ?? ''),
      toolName: String(data.tool_name ?? ''),
      target: String(data.target ?? ''),
      rule: String(data.rule ?? ''),
      reason: String(data.reason ?? ''),
      expiresAt: String(data.expires_at ?? ''),
      seq,
    },
  })
} else if (kind === 'approval_resolved') {
  dispatch({
    type: 'item',
    item: { kind: 'approval_resolved', approvalId: String(data.approval_id ?? ''), status: String(data.status ?? ''), seq },
  })
```

Add the exported helper at module scope:

```ts
export function pendingApprovals(
  stream: StreamItem[],
): Extract<StreamItem, { kind: 'approval_request' }>[] {
  const resolved = new Set(
    stream.filter((i) => i.kind === 'approval_resolved').map((i) => (i as Extract<StreamItem, { kind: 'approval_resolved' }>).approvalId),
  )
  return stream.filter(
    (i): i is Extract<StreamItem, { kind: 'approval_request' }> =>
      i.kind === 'approval_request' && !resolved.has(i.approvalId),
  )
}
```

Add the `respondApproval` action (near `merge`/`discard`) and include it in the returned object:

```ts
const respondApproval = useCallback(
  async (approvalId: string, decision: 'approved' | 'denied') => {
    if (!state.sessionId) return
    await fetch(`/api/studio/sessions/${state.sessionId}/approvals/${approvalId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision }),
    })
  },
  [state.sessionId],
)
```

```ts
return { ...state, start, merge, discard, reset, respondApproval }
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm run test -- hooks/useStudioSession.test.ts`
Expected: PASS (3 passed).

- [ ] **Step 5: Typecheck**

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add agents/dashboard/hooks/useStudioSession.ts agents/dashboard/hooks/useStudioSession.test.ts
git commit -m "feat: stream studio approval events and expose respondApproval"
```

---

## Task 6: Frontend — the approval card

**Files:**
- Modify: `agents/dashboard/components/views/StudioView.tsx`
- Test: `agents/dashboard/components/views/StudioView.approval.test.tsx` (create)

**Interfaces:**
- Consumes: `pendingApprovals` + `respondApproval` (Task 5).
- Produces: an approval card rendered per pending approval with **Approve** / **Deny** buttons that call `respondApproval(approvalId, 'approved' | 'denied')`.

- [ ] **Step 1: Write the failing test**

Create `agents/dashboard/components/views/StudioView.approval.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ApprovalCard } from './StudioView'

describe('ApprovalCard', () => {
  const approval = {
    kind: 'approval_request' as const, approvalId: 'ap_1', toolName: 'Write',
    target: 'config/prod.env', rule: 'unknown_tool', reason: 'needs a human',
    expiresAt: '2026-07-11T09:35:00Z', seq: 1,
  }

  it('shows the tool and target', () => {
    render(<ApprovalCard approval={approval} onRespond={vi.fn()} />)
    expect(screen.getByText(/config\/prod\.env/)).toBeTruthy()
    expect(screen.getByText(/Write/)).toBeTruthy()
  })

  it('calls onRespond with approved when Approve is clicked', () => {
    const onRespond = vi.fn()
    render(<ApprovalCard approval={approval} onRespond={onRespond} />)
    fireEvent.click(screen.getByRole('button', { name: /approve/i }))
    expect(onRespond).toHaveBeenCalledWith('ap_1', 'approved')
  })

  it('calls onRespond with denied when Deny is clicked', () => {
    const onRespond = vi.fn()
    render(<ApprovalCard approval={approval} onRespond={onRespond} />)
    fireEvent.click(screen.getByRole('button', { name: /deny/i }))
    expect(onRespond).toHaveBeenCalledWith('ap_1', 'denied')
  })
})
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm run test -- components/views/StudioView.approval.test.tsx`
Expected: FAIL — `ApprovalCard is not exported`.

- [ ] **Step 3: Implement in `StudioView.tsx`**

Import the helper + type and the new pieces:

```tsx
import { useStudioSession, pendingApprovals, type StudioStatus, type StreamItem } from '@/hooks/useStudioSession'
```

Add the exported card component at the bottom of the file (near `StatusPill`):

```tsx
type ApprovalItem = Extract<StreamItem, { kind: 'approval_request' }>

export function ApprovalCard({
  approval,
  onRespond,
}: {
  approval: ApprovalItem
  onRespond: (approvalId: string, decision: 'approved' | 'denied') => void
}): React.JSX.Element {
  return (
    <div
      className="studio-banner"
      role="group"
      aria-label="Action needs your approval"
      style={{ borderColor: 'rgba(255,170,0,0.35)', background: 'rgba(255,170,0,0.08)' }}
    >
      <span style={{ color: 'var(--accent-amber)' }}>⚠ Approval needed</span>
      <div style={{ color: 'var(--text-secondary)', fontSize: 10, marginTop: 4, fontFamily: 'var(--font-mono)' }}>
        <div><strong style={{ color: 'var(--text-primary)' }}>{approval.toolName}</strong> → {approval.target}</div>
        <div style={{ opacity: 0.8 }}>{approval.rule}: {approval.reason}</div>
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <button className="btn" type="button" onClick={() => onRespond(approval.approvalId, 'denied')}>
          Deny
        </button>
        <button className="btn studio-build" type="button" onClick={() => onRespond(approval.approvalId, 'approved')}>
          Approve
        </button>
      </div>
    </div>
  )
}
```

Replace the static escalation banner in `StudioView`. Remove the old `escalations` `useMemo` + its banner block, and derive pending approvals instead:

```tsx
const pending = useMemo(() => pendingApprovals(s.stream), [s.stream])
```

Where the old escalation banner was, render one card per pending approval, wired to a handler that shows a toast:

```tsx
{pending.map((ap) => (
  <ApprovalCard
    key={ap.approvalId}
    approval={ap}
    onRespond={(id, decision) => {
      void s.respondApproval(id, decision)
      toast({
        variant: decision === 'approved' ? 'success' : 'info',
        title: decision === 'approved' ? 'Approved' : 'Denied',
        message: decision === 'approved' ? 'Letting the agent continue.' : 'Action blocked.',
      })
    }}
  />
))}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm run test -- components/views/StudioView.approval.test.tsx`
Expected: PASS (3 passed).

- [ ] **Step 5: Typecheck + full frontend tests**

Run: `npx tsc --noEmit && npm run test`
Expected: no type errors; all tests pass.

- [ ] **Step 6: Commit**

```bash
git add agents/dashboard/components/views/StudioView.tsx agents/dashboard/components/views/StudioView.approval.test.tsx
git commit -m "feat: interactive approve/deny card in the studio IDE"
```

---

## Task 7: Docs + verify end-to-end

**Files:**
- Modify: `agents/coder-studio/README.md` (approval flow + `STUDIO_APPROVAL_TIMEOUT`)
- Modify: `HyperCode-V2.4/WHATS_DONE.md` (record the shipped feature)

**Interfaces:** none (documentation + manual verification).

- [ ] **Step 1: Document the env + flow in `agents/coder-studio/README.md`**

Add a short "Interactive approval" section: `ESCALATE` now pauses the tool call and waits up to `STUDIO_APPROVAL_TIMEOUT` (default 300s) for an approve/deny in `/ide`; a walk-away denies (fail-closed); single-process assumption per the spec §3.1.

- [ ] **Step 2: Add a WHATS_DONE.md line**

One bullet: interactive ESCALATE approval gate in coder-studio + `/ide` (studio-native SSE, fail-closed 300s, `feat/studio-escalate-approval`).

- [ ] **Step 3: Full backend + frontend suites**

Run: `cd agents/coder-studio && python -m pytest -v`
Run: `cd agents/dashboard && npx tsc --noEmit && npm run test`
Expected: all green.

- [ ] **Step 4: Manual E2E (verify skill)**

Bring the stack up, open `/ide`, submit a task that triggers an escalation (e.g. a tool the manifest does not grant / an unknown tool), confirm the card appears, click **Approve**, confirm the tool proceeds; repeat with **Deny** and with a walk-away timeout. Capture the observed behaviour.

- [ ] **Step 5: Commit**

```bash
git add agents/coder-studio/README.md WHATS_DONE.md
git commit -m "docs: document studio interactive approval and STUDIO_APPROVAL_TIMEOUT"
```

- [ ] **Step 6: Open the PR**

```bash
git push
gh pr create --fill --base main --head feat/studio-escalate-approval
```

---

## Self-Review Notes (author)

- **Spec coverage:** §3 flow → Tasks 3–4; §4.1 registry/settle → Task 1; §4.2 gate → Task 2; §4.3 closure+endpoint → Tasks 3–4; §4.4 discard → Task 4; §4.5 SSE payloads → Tasks 3 (emit) + 5 (consume); §5 frontend → Tasks 5–6; §6 error handling → Tasks 3–4 tests; §7 tests incl. race + cleanup → Tasks 1/4; §8 config → Task 3; §9 scope note → Task 7 docs. No gaps.
- **Ordering:** race-safety core (`settle()`) is Task 1, proven before any endpoint or UI, per the explicit requirement.
- **Type consistency:** `resolve_escalation` signature identical in Tasks 2/3; `Approval` fields identical in Tasks 1/3/4; SSE field names (`approval_id`, `tool_name`, `target`, `rule`, `reason`, `expires_at`, `status`) identical between Task 3 (emit) and Task 5 (consume, mapped to camelCase); `pendingApprovals`/`respondApproval`/`ApprovalCard` names identical between Tasks 5 and 6.
