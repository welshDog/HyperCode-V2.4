# BROski Operator — async MCP tasks on top of HyperFlow

**Date:** 2026-09-26 · **Status:** draft, awaiting review · **Origin:** `BROski` scratch doc (MCP Tasks proposal), re-based on what the repo actually has.

## 1. Goal

BROski is the operator layer for HyperCode: Bro states a goal, BROski starts durable
background work and returns a `task_id` immediately, Bro can disconnect and check later,
and risky steps pause for approval. Success = one end-to-end proof, live, with no mocks,
that (a) survives client disconnect, (b) survives a `hypercode-core` restart while parked
at an approval gate, (c) can be cancelled mid-flight, and (d) never touches production
without a Safety Shepherd verdict.

## 2. What the scratch doc got wrong (verified against code, 2026-09-26)

| Scratch doc | Reality |
|---|---|
| `POST :8820/tools/call`, `GET :8820/tasks/{id}` | `:8820` is stock `docker/mcp-gateway` (github server only). Not our code, no Tasks support, currently down. Our MCP server is `hypercode-mcp-server` `:8823` (`mcp[cli]==1.27.1`, pinned; backend pins `mcp==1.26.0`). |
| Celery task `hypercode.run_agent_task(goal, tool_name…)` | Real task is `hypercode.tasks.run_agent_task(agent_name, task_type, payload)` and only routes an LLM prompt. |
| New `hypercode_tasks` table | Not needed. `hyperflow_runs` already holds durable run state (JSONB history + context). The existing `tasks` table is a Kanban model (int id, todo/in_progress/review/done) — wrong semantics. |
| `/api/broski/tasks` | `broski.py` is the economy router (wallet/pulse). "BROski" already means economy/pets/COO. Use `/api/v1/operator/…`. |
| New policy engine | Safety Shepherd (ALLOW/BLOCK/ESCALATE) is already wired into `HyperFlowRunner._safety_gate`; Governor issues capability tokens. |
| `run_tests` as the safe first milestone | `pytest` OOM-killed twice on this box (WHATS_DONE N22). First tool is `inspect`; `run_tests` last, RAM-gated. |

## 3. What already exists (reuse, do not rebuild)

- `HyperFlowRun` (Postgres): id, flow_name, status (`String(24)`), current_node, state JSONB.
- `HyperFlowRunner` (`backend/app/agents/hyperflow_runner.py`): in-core asyncio task; node types `agent_role | tool | human_approval_gate`; retry/fallback/loop edges; Safety Shepherd gate per node via `SafetyHint`.
- Redis DB 1 snapshot + pub/sub (`run_cache_key`, `run_channel`) → SSE at `/flows/runs/{id}/events`.
- `/flows/active` feeds the dashboard Mission Graph panel.

## 4. Real gaps this spec closes

1. `/flows/runs/{id}/resume` uses in-process `get_runner()` → 409 if the run is not in that worker's memory. Approval is lost on restart.
2. No cancel; no `cancelled` status.
3. Nothing speaks the MCP Tasks vocabulary (`tasks/get`, `tasks/update`, `tasks/cancel`).
4. No real read-only tool nodes (flows only call the orchestrator/LLM).

Explicitly **out of scope (YAGNI):** moving the runner to Celery; a new task table; a new policy engine; a new dashboard panel.

## 5. Design

### 5.1 Operator API (new, thin, in `hypercode-core`)

`backend/app/api/v1/endpoints/operator.py`, mounted at `/api/v1/operator`:

| Route | MCP Tasks analogue | Behaviour |
|---|---|---|
| `POST /tasks` `{tool, arguments}` | `tools/call` → task handle | Validates `tool` against an allow-list mapping to a flow, starts a run via `start_flow_run`, returns `{taskId, status:"working", pollInterval}` immediately. Auth required. |
| `GET /tasks/{id}` | `tasks/get` | Reads `HyperFlowRun`; returns status, progress (nodes done / total), result (only when completed), error (only when failed/cancelled), `inputRequests` (only when input_required). |
| `POST /tasks/{id}/input` `{decision}` | `tasks/update` | Persists the approval decision (see 5.2). Auth required. |
| `POST /tasks/{id}/cancel` `{reason}` | `tasks/cancel` | See 5.3. Auth required. |

Status mapping (pure function, unit-tested): `running→working`, `awaiting_approval→input_required`, `completed`, `failed`, `cancelled` pass through. `status` is `String(24)`, so **no DB migration**; only `HyperFlowRunStatus` gains `CANCELLED`.

### 5.2 Durable approval

- `/input` writes `{decision, by, ts}` into `state.context.pending_decision` (Postgres) and publishes on the run's Redis channel.
- `HyperFlowRunner._await_approval` waits on the in-memory event **and** re-reads Postgres for a persisted decision (poll interval ≤ 2 s), so a decision made while the runner was down is still honoured.
- `recover_runs()` runs at core startup (lifespan hook): for each run in `running` / `awaiting_approval` not owned by a live runner:
  - parked at a `human_approval_gate` → rebuild runner at that node and continue waiting (safe: no side effects re-run);
  - parked mid tool node → resume only if the node is flagged `idempotent: true` (new optional `FlowNode` field, default `false`); otherwise mark `failed` with `error="interrupted by restart"`.
- Recovery never resumes a `cancelled` run.

### 5.3 Cancel

Set status `cancelled`, append a history entry (`type: "terminal"`, reason, by), cancel the runner's asyncio task if present in this process, publish a terminal event. If the run is not in this process, only Postgres is updated (recovery then skips it). Audit record is the run history; no deletion.

### 5.4 MCP surface

On `hypercode-mcp-server` (:8823): tools `hypercode_inspect` (later `hypercode_recover`, `hypercode_run_tests`) call `POST /operator/tasks` and return the task handle; `task_get`, `task_update`, `task_cancel` proxy the other three routes.
**Probe first:** check whether `mcp 1.27.1` exposes the 2026-07-28 Tasks extension. If not, ship as ordinary tools with identical payload shapes (native extension is a later swap, not a redesign). Tool-name format (`.` vs `_`) verified in the probe.

### 5.5 Tools and flows

- `inspect` is a **local read-only tool** registered in a small in-core registry (bypasses the orchestrator): container/agent state via `docker-socket-proxy` GET endpoints only, Redis + Postgres reachability, Celery queue depths, disk, DMR model list. Returns a structured report and `ok`.
- Flow `operator_inspect`: single `tool` node → completed.
- Flow `operator_recover` (phase 2): `inspect` → `agent_role` (propose fix) → `human_approval_gate` → `tool` restart node with `SafetyHint(category="docker")` so Safety Shepherd rules on it; ESCALATE goes through the existing approval path.
- Flow `operator_run_tests` (phase 3): behind a RAM-gate precheck node (refuses below a free-RAM threshold).

### 5.6 Safety

No new policy engine. Forbidden actions from the scratch doc (delete prod data, expose secrets, disable scans, edit approval policy) are expressed as Safety Shepherd BLOCK rules / absence from the tool allow-list. The LLM never enforces its own permissions; the runner + Shepherd do. Operator routes require an authenticated user.

## 6. Testing and proof

**Unit (pytest, backend):** status mapping; `/tasks` allow-list rejects unknown tools; cancel (in-process and not-in-process); `recover_runs` for gate-parked, idempotent-tool, non-idempotent-tool and cancelled runs (simulated restart via fresh runner registry); `get` hides result/error unless terminal.

**Live proof (no mocks), in order:**
1. `POST /operator/tasks inspect` → handle in <1 s; disconnect; `GET` later → completed report.
2. Start a gate flow → `input_required`; `docker restart hypercode-core` (never `--force-recreate`); after healthy, `POST /input` → run completes.
3. Start a slow flow → `cancel` → `cancelled`, no further node transitions.
4. Same three via the MCP tools.

**RAM discipline:** check free RAM before every Docker step; stop if <0.8 GB. Do not run `pytest` for the whole repo, only the new test files, and only with obs stack down.

## 7. Phasing

1. **Phase 1 (this spec's build):** 5.1–5.4, `inspect` tool + flow, live proof.
2. **Phase 2:** `recover` flow with Shepherd-gated restart.
3. **Phase 3:** `run_tests` with RAM-gate.
Each phase gets its own plan-checked increment; Phase 1 alone must be shippable.

## 8. Open questions (resolve in the plan, not blockers)

- Exact MCP Tasks support in `mcp 1.27.1` (probe, §5.4).
- Whether `docker-socket-proxy` already allows the GET endpoints `inspect` needs (verify; otherwise add the minimal read endpoints, never the raw socket).

## 9. Amendments made during planning and execution (2026-09-26)

Decided while the plan was written and reviewed; the binding record is the SDD ledger, summarised here so the spec matches what shipped.

**Behavior that differs from §5 above**
- **Approvals are superuser-only and human-only.** `POST /tasks/{id}/input` requires a Bearer JWT for a *superuser*; an `X-Agent-Key` gets 403 and so does a non-superuser human. The MCP server holds only an agent key, so it exposes **no approval tool** (§5.4's `task_update` is dropped). Approvals happen in the dashboard / authenticated API.
- **`/input` only works when the run is parked at a real human gate**: newest history entry is `awaiting_approval` of type `human_approval_gate` for `current_node`. Safety-Shepherd escalation waits are not approvable through the operator API (GET shows `inputRequests.kind = "safety_escalation"`). An optional body `node` that differs from the parked gate gets 409 `gate_mismatch`.
- **Persisted decisions are gate-scoped**: `{"approved","by","ts","node"}`; a decision whose `node` is missing or differs from the gate consuming it is stale and discarded. A runner only receives the in-memory wake-up if `runner.parked_gate` equals the gate.
- **`arguments` must be `{}`** in Phase 1; anything else is a 422. Unknown tools are a 404.
- **Operator routes only see catalog flows** (`hypercode.inspect` -> `operator-inspect`, `hypercode.smoke` -> `hyperflow-smoke`); any other HyperFlow run id is a 404 through `/operator`, and the legacy `/flows/runs/{id}/resume` returns 409 `use_operator_api` for catalog runs and only resumes a runner that is parked at a gate.
- **Recovery rules**: a run parked at a gate resumes at the gate; a step in flight at crash time is re-run only if `idempotent: true` or it is a human gate, otherwise the run fails with `interrupted by restart`. Trailing `safety_allow`/`safety_skipped` history entries count as "the node is in flight"; `safety_escalate`/`safety_block`/`safety_resolved` fail conservatively. Runs idle longer than `RECOVERY_MAX_AGE_HOURS` (default 24) are failed as `stale at recovery` instead of resumed. Loop counters and the originating `user_id` are not restored. Startup recovery is bounded by a 15 s timeout and is skipped when `HYPERFLOW_RECOVERY=0` (used by the test suite).
- **Persistence**: runner writes lock the row (`FOR UPDATE`) and never un-terminate a completed/failed/cancelled run. A live cancel/complete/fail appends the same terminal history entry as the DB-only path.
- **Legacy exposure**: `result.data` (the inspect report) is stripped from the unauthenticated legacy `/flows` GET endpoints and from the Redis snapshot/pub-sub payloads; the operator API reads Postgres and still returns it. Local-tool `data` is persisted only for local-tool nodes.
- **Inspect errors are scrubbed** (`_safe_error`): HTTP status only for `HTTPStatusError`, exception type only for Postgres, URL userinfo / `password=` fragments removed elsewhere.
- **Run status vs health**: a run is `completed` when the graph finishes; whether the stack is healthy is `result.report.ok` / `result.success`.
- **MCP SDK probe**: `mcp 1.27.1` exposes native Tasks types (e.g. `ServerTasksCapability`), so swapping the ordinary `hypercode_task_*` tools for the native Tasks extension is feasible later; the payloads already use the Tasks vocabulary.

**Known limitations / deferred (not fixed in Phase 1)**
- Two superusers racing `/input` on one gate: last decision wins in memory and a leftover gate-stamped decision remains (only consumable if a loop edge returns to the same gate id; no shipped flow does).
- `/input` and DB-only cancel do not publish to the run's Redis channel, so SSE watchers do not see those transitions until the runner's next emit.
- Every recovery re-park re-publishes to the `approval_requests` channel (duplicate prompts after each restart); an approval consumed just before a crash, before the gate's `completed` emit, is lost and the run re-parks (safe direction).
- A parked runner polls Postgres every 2 s with no expiry, and logs an exception every poll during a database blip.
- Read/cancel through `/operator` are open to any authenticated principal for catalog runs (no per-user ownership); the inspect report (container names, queue depths) is visible to them. Ownership checks are a Phase 2 item.
- `HYPERCODE_AGENT_KEY` is a plain env var (no `*_FILE` Docker-secret support); existing MCP tools now also send it to core, which skips the IP rate limiter for those calls.
- The `_safe_error` scrubber is a blacklist with known exotic bypasses (raw `@` in a password, `*_password=` keys, spaced/colon forms, `token=`/`Bearer`); the sections that run do not emit credentials. An allow-list is the Phase 2 hardening. `RECOVERY_MAX_AGE_HOURS=0`, negative or non-finite values are not rejected.
- `operator-inspect`'s intent joins free-text goal matching for `/flows/runs`; the cancel proof uses a gate-parked run rather than a slow flow.
