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
