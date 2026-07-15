# Studio ESCALATE Approval Gate — Design

- **Date:** 2026-07-11
- **Repo:** `HyperCode-V2.4`
- **Service:** `coder-studio` (:8087) + dashboard `/ide`
- **Status:** Approved for implementation

---

## 1. Problem

When the Studio agent attempts a tool call, `coder-studio`'s Safety Shepherd gate
(`agent_runner.py::make_gate`) evaluates it and gets back one of `ALLOW` / `BLOCK`
/ `ESCALATE`. Today `ESCALATE` is **auto-denied**:

```python
# agent_runner.py (current)
if verdict.decision == ESCALATE:
    # No approval UI yet. An escalation must never fall through to allow.
    return PermissionResultDeny(message=f"Needs human approval ...")
```

The gate callback is already `async` and runs **inside** the agent's suspended
tool call. So an escalated action can be *paused at the exact decision point* and
resumed (or denied) by a human, without unwinding the agent's turn.

**Goal:** turn `ESCALATE` into an interactive approve/deny gate, surfaced inline
in `/ide`, resolved in-process, with a safe walk-away default.

## 2. Decisions (locked)

| Decision | Choice |
|---|---|
| Approval surface | **Studio-native, inline in `/ide`** — reuses the existing per-session SSE stream. No Redis, no bridge, no orphaned `ApprovalModal`. |
| Walk-away default | **Auto-deny after `STUDIO_APPROVAL_TIMEOUT` (default 300s)** — fail-closed, env-configurable, matches Shepherd's existing 300s TTL. |
| Approval granularity | **One click per escalated action** — simplest, most auditable. No session allowlist. |

### Contradiction surfaced (and resolved)

The kickoff briefing said *"reuse `ApprovalModal.tsx` + Shepherd's
`approval_requests` Redis channel."* Tracing the code, that is now the **heavier**
path:

- `ApprovalModal.tsx` is orphaned (mounted nowhere) and its WebSocket targets
  `/api/v1/orchestrator/ws/approvals` + responds to `/orchestrator/approvals/respond`
  — the **HyperFlow orchestrator's** approval system, not Shepherd's.
- Shepherd publishes to `approval_requests` but has **no respond endpoint**, and
  nothing bridges that channel to the modal.
- The gate that must block-and-wait lives in the Studio process, which already
  streams per-session decisions over SSE to `/ide`.

Reusing the Redis path would mean building a Shepherd respond endpoint **+** a
Redis→WS bridge **+** a Studio Redis client **+** mounting the modal. The
Studio-native path reuses what is already streaming. We chose Studio-native.

## 3. Architecture

The gate awaits a per-session `asyncio.Event`. The approve/deny HTTP endpoint
sets that event. Both live in the **same `coder-studio` process**, so the
`asyncio` primitive is the correct and sufficient synchronisation mechanism.

```text
agent → tool call → gate → Shepherd = ESCALATE
  1. create Approval(id, event, status=pending)
  2. register it in session.pending_approvals      ← BEFORE any SSE
  3. emit approval_request SSE (with expires_at)
  4. await event, max STUDIO_APPROVAL_TIMEOUT (300s)
  5. settle: approved | denied | timed_out | discarded   (atomic, first wins)
  6. emit approval_resolved SSE
  7. finally: remove entry from session.pending_approvals
  8. gate returns Allow ONLY for status == approved; otherwise Deny
UI: approval_request → card with Approve/Deny
  → POST /sessions/{id}/approvals/{approval_id}
  → event.set() → gate resumes
```

### 3.1 Single-process assumption (documented boundary)

This in-memory registry is correct **while a live Studio session and its approval
endpoint land on the same `coder-studio` process** — true today (one replica).
If `coder-studio` is later scaled horizontally, either add sticky routing
(session-id affinity) or move session + approval state to shared storage
(Redis/Postgres). Until then, in-memory is the right, simplest choice. This
boundary is called out so a future scaling change does not silently break
approvals.

## 4. Backend changes (`coder-studio`)

### 4.1 `sessions.py` — approval registry on the Session

Add an `Approval` record and a registry to `Session`:

```python
class ApprovalState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMED_OUT = "timed_out"
    DISCARDED = "discarded"

@dataclass
class Approval:
    id: str
    tool_name: str
    target: str
    rule: str
    reason: str
    expires_at: str                       # ISO 8601, for the UI countdown
    event: asyncio.Event = field(default_factory=asyncio.Event)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    status: ApprovalState = ApprovalState.PENDING

    async def settle(self, decision: ApprovalState) -> ApprovalState:
        """Atomically record the first terminal decision. Duplicate calls are
        no-ops that return the already-settled status (first valid wins)."""
        async with self._lock:
            if self.status is ApprovalState.PENDING:
                self.status = decision
                self.event.set()
            return self.status
```

`Session` gains `pending_approvals: dict[str, Approval] = {}`.

**Settlement is atomic:** `settle()` is the single mutation path. The endpoint,
the timeout, and discard all call it; the first `PENDING → terminal` transition
wins and sets the event exactly once. Later calls read back the settled status
without overwriting.

### 4.2 `agent_runner.py` — gate learns to wait

`make_gate` and `run_agent` take a new optional
`resolve_escalation: Optional[Callable[[str, dict, Verdict], Awaitable[bool]]]`.

```python
if verdict.decision == ESCALATE:
    if resolve_escalation is None:
        # Preserved safe default: keeps existing gate tests stable and any
        # caller that does not wire approval fail-closed.
        return PermissionResultDeny(message=f"Needs human approval ({verdict.rule}): {verdict.reason}")
    approved = await resolve_escalation(tool_name, tool_input, verdict)
    return PermissionResultAllow() if approved else PermissionResultDeny(
        message="Denied by human review (or timed out)"
    )
```

`on_decision` still fires first, so the `ESCALATE` decision appears in the feed
before the approval card.

### 4.3 `main.py` — the wait closure + endpoint

**Wait closure** (built in `_drive_agent`, closes over the session):

```python
async def resolve_escalation(tool_name, tool_input, verdict) -> bool:
    approval_id = str(uuid.uuid4())            # Studio mints its own id
    expires = _iso(now + STUDIO_APPROVAL_TIMEOUT)
    approval = Approval(
        id=approval_id,
        tool_name=tool_name,
        target=_describe_target(tool_name, tool_input),
        rule=verdict.rule,
        reason=verdict.reason,
        expires_at=expires,
    )
    session.pending_approvals[approval_id] = approval      # (1) register first
    session.add_event("approval_request", {                # (2) then emit SSE
        "approval_id": approval_id, "tool_name": tool_name,
        "target": approval.target, "rule": approval.rule,
        "reason": approval.reason, "expires_at": expires,
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
        session.pending_approvals.pop(approval_id, None)   # (7) always clean up
```

> Note: `settle()` sets `event` under its lock; `event.wait()` returning means a
> terminal status is already stored, so reading `approval.status` after the wait
> is race-free.

**Endpoint:**

```
POST /sessions/{session_id}/approvals/{approval_id}
Body: {"decision": "approved" | "denied"}
Auth: X-Agent-Key (via existing /api/studio/* proxy)
```

| Status | Meaning |
|---|---|
| `200` | Decision accepted, **or** a concurrent replay matches the already-settled decision (idempotent). |
| `404` | Session/approval not found — **never existed, or already resolved and cleaned up**. |
| `409` | A concurrent replay submits the **opposite** decision after settlement (real conflict / stale browser). |

Handler:

```python
session = store.get(session_id) or -> 404
approval = session.pending_approvals.get(approval_id)
if approval is None: -> 404          # never existed OR resolved+cleaned (see note)
requested = ApprovalState(body.decision)            # approved | denied only
final = await approval.settle(requested)
if final is requested: return 200
if final in (APPROVED, DENIED) and final is not requested: -> 409   # opposite human decision
return 200                                          # lost to timed_out/discarded; action not allowed either way
```

> **Idempotency window.** Because `resolve_escalation` clears the entry in its
> `finally` (§4.3) right after emitting `approval_resolved`, the `200`/`409`
> idempotent behaviour covers the realistic case — **concurrent** double-clicks
> that arrive while the entry still exists (`settle()` makes the first win). A
> **late** replay that arrives after full resolution + cleanup returns `404`.
> That is correct and unambiguous: the UI's source of truth for "already done"
> is the `approval_resolved` SSE event, not the endpoint, so it never needs to
> re-POST a settled approval.
>
> `409` fires only when a human `approved`/`denied` is contradicted by the
> opposite human decision within that window. A click that loses to a
> `timed_out`/`discarded` settlement returns `200` (the action was not allowed
> either way) — this avoids punishing an innocent late click while still
> surfacing genuine approve-vs-deny conflicts.

### 4.4 `main.py` — discard safety

In `discard()`, settle every pending approval as `DISCARDED` **before**
cancelling the task, so the awaiting gate coroutine unblocks normally rather than
being torn down mid-`await`:

```python
session.set_status(Status.DISCARDED)
for approval in list(session.pending_approvals.values()):
    await approval.settle(ApprovalState.DISCARDED)   # unblock the gate first
# ... then cancel the task and discard the worktree (existing code)
```

### 4.5 SSE payloads

```json
{ "kind": "approval_request", "approval_id": "uuid", "tool_name": "Write",
  "target": "config/prod.env", "rule": "unknown_tool",
  "reason": "Requires human confirmation", "expires_at": "2026-07-11T09:35:00Z" }
```

```json
{ "kind": "approval_resolved", "approval_id": "uuid",
  "status": "approved | denied | timed_out | discarded" }
```

`expires_at` lets the frontend render a five-minute countdown without inventing
its own timer.

## 5. Frontend changes (`/ide`)

### 5.1 `hooks/useStudioSession.ts`

- Extend `StreamItem` with `approval_request` and `approval_resolved` variants.
- Add `'approval_request'` and `'approval_resolved'` to `KINDS`.
- Add action `respondApproval(approvalId, decision)` → `POST /api/studio/sessions/{id}/approvals/{approvalId}` with `{decision}`.
- **Pending approvals are derived** from the stream: an `approval_request` whose
  `approval_id` has no matching `approval_resolved`. No extra reducer state.

### 5.2 `components/views/StudioView.tsx`

Replace the static "held & denied" banner with a live **approval card**:

- Shows `tool_name`, `target`, `rule`, `reason`, and a countdown from `expires_at`.
- **Approve** / **Deny** buttons call `respondApproval`.
- On the matching `approval_resolved`, the card flips to the outcome
  (approved = green, denied/timed_out/discarded = muted).
- Amber-pending styling matches the existing escalation treatment.

No proxy changes: `/api/studio/[...path]` already forwards `POST` with a body.

## 6. Error handling

| Case | Behaviour |
|---|---|
| Timeout | `settle(TIMED_OUT)` → deny, reason "approval timed out". |
| Discard mid-wait | `settle(DISCARDED)` before cancel → gate unblocks, denied. |
| Double-click / stale id | `settle()` idempotent; endpoint `200` on same decision, `409` on opposite. |
| Approval not found | `404`. |
| Agent crash during wait | existing `_drive_agent` catch → session `FAILED`; `finally` still clears the entry. |

## 7. Testing

**Backend (pytest, follows `test_policy_integration.py` / `test_main.py`):**

- Gate: `resolve_escalation → True` = Allow; `→ False` = Deny; `None` = Deny (legacy default preserved).
- Wait closure: approve / deny / timeout (inject a tiny `STUDIO_APPROVAL_TIMEOUT`).
- Endpoint: approve sets event → `200`; unknown session/approval → `404`; replay same decision → `200`; opposite decision after settlement → `409`.
- **Race:** discard and approve fire together → assert exactly one final status, no hang, no orphan in `pending_approvals`.
- **Cleanup:** timeout, task cancellation, and a tool-raised exception each leave `pending_approvals` empty for that id.
- Integration: fake-Shepherd transport returns `ESCALATE` → SSE emits `approval_request` → `POST approve` → tool proceeds → `approval_resolved{approved}`.

**Frontend:** derive-pending logic + `respondApproval` wiring, if the dashboard
has a test runner (confirm in planning; add a light test if vitest is present).

## 8. Config

| Env | Default | Meaning |
|---|---|---|
| `STUDIO_APPROVAL_TIMEOUT` | `300` | Seconds the gate waits for a human before fail-closed deny. |

## 9. Scope

Studio-local interactive approval. One active `coder-studio` process/session
route today; a shared-state upgrade (sticky routing or Redis/Postgres) is
required only when horizontal scaling arrives (see §3.1). No changes to
Shepherd, the HyperFlow orchestrator, or the Redis approval channel.
