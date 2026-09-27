# BROski `hypercode.recover` — Phase 2 (2a advisory now, 2b governed restart next)

**Date:** 2026-09-27 · **Status:** draft, awaiting review · **Builds on:** `2026-09-26-broski-operator-design.md` (Phase 1, merged as `22c3a7b7`) and the north-star `2026-09-04-autonomous-control-plane-north-star-design.md`.

## 1. Goal

Give BROski a safe way to answer "something is broken — what should we restart?" **without any mutation authority in this increment (2a)**: diagnose from real Docker data with deterministic rules, propose exactly one allow-listed restart, put it in front of a superuser with the exact plan and a `plan_hash`, and seal the approved plan as a tamper-evident artifact that the governed executor (2b) will later consume. Success = a live proof where a deliberately unhealthy throwaway container is proposed, a protected container is refused, a wrong-hash approval is rejected, the right-hash approval seals the plan, and **nothing was restarted**.

Staged delivery (decided with Bro, 2026-09-27): **2a = this build** (zero mutation, no new secrets). **2b = next build** (governed executor, §9), specified here only at architecture level.

## 2. Findings that shape the design (verified 2026-09-27)

| Finding | Consequence |
|---|---|
| Safety Shepherd's `docker` category only allows `compose_profile.preview` / `compose_config.validate` and blocks `compose_profile.start` / `.stop`; there is **no container-restart action**. | A `container_restart` action + policy is a 2b prerequisite. 2a does not call Shepherd. |
| North-star governing invariant: *no component may both interpret LLM output and hold infrastructure-mutation authority.* Real infra mutation is scheduled for its own Phases 4–5 behind Governor capabilities. | 2a has **no LLM in the plan path and no write path**. 2b puts mutation in a separate LLM-free executor behind a Governor capability. |
| `governor` and `fleet-controller` are behind `--profile fleet` and are **not running**; the Governor needs an Ed25519 private key and an operator key as Docker secrets, which only Bro can provision. | Nothing in 2a depends on them. 2b's live proof is gated on Bro provisioning those secrets. |
| `healer-agent` (running, healthy) has an LLM (`ai_diagnostics.py`) **and** the write socket proxy; `agent-registry` exposes an unauthenticated `POST /agents/{name}/restart`. Pre-existing. | Not touched. Phase 2 must not build on either. Recorded as known pre-existing violations. |
| Lean Operations Mode (Bro, 2026-09-26): observability is stopped; no autonomous mutation beyond proven Phase 1 scope until monitoring is back. | 2a is read-only by construction; 2b LIVE stays behind an explicit flag and Bro's go. |
| Phase 1's approval gate shows a **static** prompt; the approver's identity is consumed and lost (`_take_persisted_decision` returns only a bool). | 2a extends the gate: dynamic context + `plan_hash` binding + recorded approver (§5). These are small, generic runner/API changes. |

## 3. Scope

**In (2a):** flow `operator-recover`; catalog tool `hypercode.recover`; MCP tool `hypercode_recover`; deterministic candidate selection; restart allow-list / never-list policy module; read-only Docker evidence gathering; `plan` + `plan_hash`; gate context + `plan_hash` check + approver recording; sealed result; Governance Ledger entry; tests; live proof with a throwaway container.

**Out (2a):** any Docker write; Shepherd changes; Governor / fleet-controller; the executor; LLM diagnosis or explanations; multi-target plans; auto-triggered recovery.

## 4. Design

### 4.1 Flow and tool

`hypercode.recover` → flow `operator-recover` (`intent` worded to stay out of free-text goal matching):

```
inspect (local.inspect, idempotent) ──▶ propose (local.recover_propose, idempotent, success_key=has_proposal)
   propose ──[condition: true]──▶ approve (human_approval_gate, show_from: propose) ──▶ seal (local.recover_seal, NOT idempotent)
   propose ──[false / no edge]──▶ terminal: completed, "nothing to recover"
```

Arguments must be `{}` (unchanged Phase 1 rule). Approval is superuser-only via the existing `/operator/tasks/{id}/input`. A rejected approval fails the run (existing runner semantics) and seals nothing.

Local tools gain a context argument: `async tool(params, ctx)` where `ctx` carries `run_id` and the run's `history` (so `propose` can read `inspect`'s report and `seal` can read the proposal and the approval). `inspect` ignores it. The runner's local-tool wrapper also surfaces `data[node.success_key]` as the node's success value (today `_is_success` reads `success_key` from the wrapper result, which only carries `ok`/`green`/`data`), so `propose`'s `success_key: has_proposal` actually drives the conditional edge.

### 4.2 Candidate rules (`local.recover_propose`, pure code, no LLM)

Data source: the read-only socket proxy (`DOCKER_SOCKET_PROXY_URL`, GET only). One `GET /containers/json?all=true`, then `GET /containers/{id}/json` for at most 10 pre-candidates.

A container is a **candidate** only if:
- `State == "running"` and health `unhealthy`; or
- `State == "restarting"`; or
- `State == "exited"` **with a crash signature**: `OOMKilled` is true, or `ExitCode` not in `{0, 137, 143}`.

The exit-code rule deliberately excludes containers stopped on purpose (e.g. the 13 observability containers stopped by `docker stop`), so they are never proposed.

**Eligibility (default-deny), evaluated by a pure function `classify(name, labels) -> Eligibility`:**
1. Name in the **never-list** → not eligible, `blocked_by: never_list` (always wins).
2. Name in the **allow-list** → eligible, `basis: allow_list`.
3. Label `hypercode.recover=restartable` present → eligible, `basis: label`.
4. Otherwise → not eligible, `blocked_by: not_allowlisted`.

Initial lists (`backend/app/broski_operator/recover_policy.py`, **Bro to confirm — §11**):
- **Never-list:** `hypercode-core`, `postgres`, `redis`, `docker-socket-proxy`, `docker-socket-proxy-build`, `docker-socket-proxy-healer`, `safety-shepherd`, `governor`, `fleet-controller`, `crew-orchestrator`, `hypercode-mcp-server`, `hypercode-ollama`, `agent-registry`, `healer-agent`.
- **Allow-list:** `agent-focus-tracker`, `agent-hyper-brain-core`, `agent-mcp-bridge`, `agent-morning-briefing`, `broski-bot`, `chroma`, `coder-studio`, `evolve-relay`, `github-sync`, `github-sync-brain`, `hyper-brain`, `hyperhealth-worker`, `memstream`, `obsidian-watcher`, `skillweaver`.
- **Undecided (default: not eligible until Bro says):** `celery-worker`, `hypercode-dashboard`, anything else.

**Ranking:** unhealthy-running, then restarting, then crashed-exited; ties by name. The **proposal is the top eligible candidate only** (one target per plan keeps approvals meaningful); the rest appear in the report as listed candidates.

**Evidence per candidate** (all scrubbed and capped): `state`, `exit_code`, `oom_killed`, `restart_count`, `started_at`, `finished_at`, the last ≤3 health-probe outputs (each passed through the Phase 1 `_safe_error`-style scrubber and truncated to 200 chars), `cooldown` (read-only Redis `healer:restarts:<name>`: `{count, limit: 3, window_s: 300}`, informational — 2b enforces), and `dependents` (best effort from `com.docker.compose.depends_on` labels when present, else `null`).

### 4.3 Plan and `plan_hash`

```json
{"version": 1, "action": "restart", "target": "<container>", "reason": "<unhealthy|restarting|crashed>",
 "evidence_digest": "<sha256 of canonical evidence JSON>", "run_id": "<run id>"}
```

`plan_hash = sha256(canonical JSON of plan)` (sorted keys, `(",",":")` separators — same canonicalisation rule as `fleet-controller`'s `canonical_hash`). The hash covers `run_id`, so a plan cannot be replayed from another run.

### 4.4 Approval binding (generic runner/API changes)

- A gate node may declare `show_from: <node_id>`. When it parks, the awaiting history entry carries `result.context` = that node's last `data`, and — if `context.proposal.plan_hash` exists — `result.plan_hash`.
- `GET /operator/tasks/{id}` shows `inputRequests.approval.context` and `.plan_hash`.
- `POST …/input` **requires** `plan_hash` when the parked gate declares one: missing → 422; mismatch → 409 `{"error":"plan_hash_mismatch"}`. The decision stored for the runner carries `plan_hash` and `by`.
- On consumption the gate's completed history entry records `result: {"approved": true, "by": "<approver>", "plan_hash": "…"}` so the approver's identity survives (2b's two-person rule needs it).

### 4.5 Seal (`local.recover_seal`)

Reads the proposal and the approval from `ctx.history`; **recomputes** the plan hash and refuses (`ok: false`, fails the run) if it does not equal the approved `plan_hash` or if no recorded approver exists. On success it returns:

```json
{"ok": true, "sealed": true, "performed": false, "plan": {…}, "plan_hash": "…", "approved_by": "<email>",
 "note": "restart is NOT executed in Phase 2a; the governed executor (2b) consumes this plan"}
```

and writes one `GovernanceLedger` row (fail-soft, same pattern as `IdentityAgent.log_action`): `action="recover_plan_approved"`, `tool_used="hypercode.recover"`, `decision="approved"`, `approved_by=<approver>`, `agent_name="broski-operator"`, `payload={plan, plan_hash, run_id, performed: false}`. A rejected approval fails the run before `seal`, so no ledger row is written for rejections (accepted, noted in §10).

### 4.6 MCP

`hypercode_recover()` on `hypercode-mcp-server` starts `hypercode.recover` and returns the task handle (same `_post` helper, same agent-key rules). There is still no approval tool.

## 5. Data shape of the propose report

```json
{"ok": true, "checked_at": "…", "has_proposal": true,
 "proposal": {"plan": {…}, "plan_hash": "…", "summary": "restart <container>: unhealthy (3 failing probes)"},
 "candidates": [{"container": "…", "state": "…", "reason": "…", "evidence": {…},
                 "eligibility": {"allowed": true, "basis": "allow_list", "blocked_by": null}}],
 "not_eligible": ["<container>: never_list"], "notes": []}
```

`has_proposal` is the node's `success_key`; with no eligible candidate the flow ends `completed` with `has_proposal: false` and an empty proposal (no gate).

## 6. Safety properties (each pinned by a test)

1. **No mutation anywhere in 2a**: no Docker write call exists in the code path; the socket proxy used is the read-only one (GET only; POST disabled at the proxy).
2. **No LLM in the plan path.**
3. **Default-deny**: unknown containers are never eligible; the never-list beats the allow-list and the label.
4. A container stopped on purpose (exit 0/137/143, not OOM) is never proposed.
5. **Approve exactly what was shown**: wrong/missing `plan_hash` cannot approve.
6. `seal` re-verifies the hash and the recorded approver; it cannot be reached without an approved gate.
7. Evidence text is scrubbed and capped; no env vars or full inspect blobs are stored.
8. All Phase 1 rules stay: superuser-only approval, agent keys can start/read/cancel but never approve, node-scoped decisions, catalog-only visibility.

## 7. Testing

Unit: `classify` (table over never/allow/label/unknown, never-list precedence); candidate extraction from canned Docker JSON (unhealthy, restarting, OOM exit, stopped-on-purpose exit 0/137/143, healthy); ranking; evidence scrubbing/capping; plan canonical hash stability + `run_id` sensitivity; propose with no candidates; seal refuses on hash mismatch / missing approver; runner gate `show_from` context + `plan_hash`; API `plan_hash` 422/409 paths and approver recorded; ledger write fail-soft (table missing must not fail the seal); MCP tool posts the right tool name; recovery: a run parked at the `approve` gate resumes at the gate after a restart.

## 8. Live proof (real containers, no mutation)

Under the Phase 1 RAM rules (available >= 1.2 GB always, >= 1.5 GB before build/recreate; build only `hypercode-core` (+ `hypercode-mcp-server` for the new MCP tool); `up -d --no-deps`):
1. Start a throwaway `zz-recover-proof` container (tiny image, failing `--health-cmd`, label `hypercode.recover=restartable`). Remove it at the end.
2. `hypercode.recover` proposes exactly `zz-recover-proof`; the report lists a protected container (`hypercode-core`) as refused if it were a candidate (proved by unit test; live proof shows `not_eligible` for a second throwaway unhealthy container **without** the label).
3. Approve with a wrong `plan_hash` → 409; with the right one → `completed`, sealed, `performed: false`, approver recorded, one ledger row.
4. Verify the target container's `StartedAt`/`RestartCount` did not change (nothing restarted).
5. Restart-recovery of a run parked at `approve`, and the MCP path (`hypercode_recover` → `hypercode_task_get`).

## 9. 2b outline (next build; not built now)

A separate, LLM-free **`recovery-executor`** service, the only holder of the restart-only write proxy (`docker-socket-proxy-healer` scope, or a new tighter proxy allowing only `POST /containers/{id}/restart`). It: verifies a **Governor capability** (single-use, bound to `plan_hash`, scope `restart:<container>`, short TTL, kill-switch and lease honoured); re-checks the never/allow-list and cooldown; restarts; verifies health afterwards; writes the outcome to the ledger. Shepherd gains a `container_restart` action in its docker policy (ESCALATE by default; two-person rule for `INFRASTRUCTURE_MUTATION`, using the approver recorded by 2a). Defaults to `DRY_RUN` (mint a `DRY_RUN` capability, `performed: false`); `LIVE` needs an explicit env flag **and** Bro's go while Lean Operations Mode is on. **Needs from Bro:** the Governor's Ed25519 private key and operator key provisioned as Docker secrets and the `fleet` profile brought up. Its own spec/plan follow this build.

## 10. Known limitations (accepted for 2a)

- One target per plan; no batch recovery.
- When there is nothing to recover the run is `completed` but `result.success` is `false` (it mirrors the last node's `has_proposal`); clients should read `result.report.has_proposal` / `notes`, not `success`, to tell "nothing to do" from a failure.
- Rejected approvals are not ledgered (the run fails without sealing).
- `dependents` is best effort (the `depends_on` label is not present on every container).
- Cooldown is informational in 2a.
- The gate's `plan_hash` requirement is generic but only the recover flow uses it; other flows are unchanged.
- The Phase 1 known limitations (spec §9 of the operator design) still apply.

## 11. Decisions for Bro to confirm in review

1. The **allow-list / never-list** in §4.2, especially `celery-worker` and `hypercode-dashboard` (currently undecided = not eligible).
2. Whether `agent-registry` and `healer-agent` should stay on the never-list (recommended: yes, they are recovery infrastructure).
3. Any container that should carry the `hypercode.recover=restartable` label in compose later.
