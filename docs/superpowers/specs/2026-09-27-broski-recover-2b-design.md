# BROski Phase 2b — `hypercode.recover` authorization (fail-closed DRY_RUN proof)

**Date:** 2026-09-27 · **Status:** draft, awaiting review · **Builds on:** `2026-09-27-broski-recover-design.md` (Phase 2a, draft PR #538, not yet merged) and the north-star `2026-09-04-autonomous-control-plane-north-star-design.md` (Governor/Shepherd capability system, built and smoke-tested 2026-09-04, currently idle behind `--profile fleet`).

**Branch:** `feature/broski-recover-2b`, off `feature/broski-recover-2a` (not off `main`) — 2b's code depends directly on 2a's flow, tools and seal, which are not yet merged. Retarget to `main` once #538 lands.

## 1. Goal

Phase 2a (`hypercode.recover`) diagnoses broken containers and produces a sealed, human-approved plan to restart one — but performs no execution; `performed` is always `false`. Phase 2b wires that sealed plan into the pre-existing Governor/Safety-Shepherd capability system so a capability can be *requested* for the restart — while still executing nothing. Success for this increment = a live proof that the real wiring (not a mock) correctly asks Shepherd and Governor, and both correctly refuse, because no capability grant exists for this action yet. Nothing new mints. LIVE stays untouched.

## 2. What changed the scope while designing (verified 2026-09-27)

| Finding | Consequence |
|---|---|
| The north-star roadmap orders Phase 4 (`crew.plan.submit` only, explicitly "no Docker") before any Docker-mutating live capability, with Phase 5 (`compose_profile.start`) after that. Phases 1, 3, 4, 5 are all "not built"; only Phase 0 (preview) and Phase 2 (capabilities, DRY_RUN) exist. | Building a container-restart executor is genuinely ahead of the documented order. **Bro decided to proceed anyway**, as a scoped, explicitly-flagged exception — narrower than `compose_profile.start` (one named, already-vetted, already-approved container) — not a silent deviation. |
| `fleet-controller`'s `PlanRequest.requested_actions[].kind` is a closed `Literal` (`compose_profile.preview`/`crew.workflow.preview` only, by design — "later phases" per its own docstring), and `fleet-controller` itself has no Docker client anywhere in its code (`execution.performed = False` unconditionally). | 2b does not touch `fleet-controller` at all. It's the wrong integration point. |
| Governor keeps its **own copy** of that schema file (`agents/governor/models.py`) — a deliberate file-copy-never-cross-import convention between agents, confirmed by diffing the two files. | Only Governor's copy needs a new action kind. `fleet-controller` is entirely unaffected. |
| Safety Shepherd's `docker` category (`INFRASTRUCTURE_MUTATION` risk class) ESCALATEs by default for any action from an agent with no explicit grant (`policy.py`'s generic precedence rules — nothing `container`-specific needed). Governor's transition table (`transitions.py`) sends **every** ESCALATE decision through the two-person-approval gate **regardless of requested mode** — there is no "DRY_RUN gets a pass" carve-out; only a `READ_ONLY`+`ALLOW` verdict gets a mode override. | "DRY_RUN-only" cannot mean "mints a DRY_RUN capability" unless the caller is granted an explicit `container.restart` capability in `capabilities.json` — and that grant would **also** unlock LIVE minting the instant the lease is valid, undoing the "LIVE is separate" framing. **Bro chose the honest option**: no new grant. This increment proves the pipeline **fails closed** — Shepherd ESCALATEs, Governor refuses to mint (no second approver on record) — not that anything mints. |
| `governor_operator_key.txt` (needed for the two-person `/v1/approvals` endpoints) does not exist on disk; `governor_ed25519_private_key.txt` does. | Not needed for this increment — nothing reaches the approvals path successfully, since refusal happens before approval-satisfaction would even matter for the outcome shown to the caller. |

## 3. Scope

**In:** one new flow node `authorize` in `operator-recover`, run automatically after `seal`; a new local tool `backend/app/broski_operator/authorize_tools.py`; one new `Literal` entry in `agents/governor/models.py` (`"container.restart"`); a new Governance Ledger action `recover_authorization_attempted`; unit tests; a live proof extension.

**Out:** any Shepherd capability grant, any change to `capabilities.json`, any change to `agents/fleet-controller/*`, a standalone `recovery-executor` service, a scoped write-only Docker proxy, `governor_operator_key.txt` provisioning, anything LIVE-capable. All of these are legitimate future work, not this increment.

## 4. Design

### 4.1 Flow

`operator-recover` gains a 5th node:

```
inspect → propose → approve(gate) → seal → authorize
```

`authorize` is a `tool` node (`tool: local.authorize`), deterministic, no LLM, no orchestrator dispatch — consistent with the containment invariant ("no component may both interpret LLM output and hold infrastructure-mutation authority"). It runs unconditionally after a successful `seal` (an edge with no `condition`, matching `propose`→`approve`'s existing style where the flow always proceeds when the prior node succeeds). It calls only Governor's HTTP API — never Docker, never the socket proxy.

### 4.2 Two hashes, never conflated

2a's `plan_hash` (`sha256:` + hex over `{version, action, target, reason, evidence_digest, run_id}`, canonical JSON) proves *a human approved this specific restart for this specific reason*. Governor's own `plan_hash` (`agents/governor/models.py:canonical_hash`, `sha256:` + hex over its `PlanRequest.model_dump()`, same `sort_keys=True, separators=(",", ":")` convention) proves *this typed request to Governor wasn't tampered with between preview and mint* — an existing, unrelated Governor convention. `authorize`'s result carries both, labelled distinctly (`plan_hash` = 2a's, `governor_plan_hash` = Governor's), and never presents one as the other.

`agents/governor/models.py`'s `RequestedAction.kind` gains one literal:

```python
kind: Literal["compose_profile.preview", "crew.workflow.preview", "container.restart"]
```

The existing `profile: Optional[str]` field carries the container name for this new kind (reusing the generic slot `MintRequest.target` is already cross-checked against, rather than adding a new field to a schema shared by two other, unrelated action kinds).

### 4.3 The call sequence

`authorize`, following the exact fail-closed pattern already established in `agents/fleet-controller/safety_client.py` (no off/monitor/enforce modes; every failure branch returns one frozen result object; a component whose job is proving a containment boundary must never treat "couldn't check" as "fine"):

1. Read 2a's sealed plan and `plan_hash` from `ctx["history"]` (same pattern `recover_seal` already uses to read `propose`'s output).
2. Build `PlanRequest(schema_version=1, mission_id=<hyperflow run_id>, requested_actions=[RequestedAction(action_id=f"restart-{target}", kind="container.restart", profile=<target container>)])` and compute `governor_plan_hash = canonical_hash(plan)` using the **same algorithm** as Governor's own (so the value Governor recomputes server-side matches).
3. `POST http://governor:8089/v1/capabilities/mint` with `{plan, plan_hash: governor_plan_hash, mode: "DRY_RUN", action: "container.restart", target: <container>, proposer_id: "broski-operator"}`.
4. Governor validates the plan, recomputes and checks the hash, calls Shepherd's `/evaluate` with `category="docker"`, `agent="broski-operator"` — an identity with no entry in `capabilities.json` — which resolves to `ESCALATE` via Shepherd's existing generic rules (no Shepherd code change needed; verified by reading `policy.py`'s `evaluate()` in full — the docker-specific `_DOCKER_ALLOWED`/`_DOCKER_BLOCKED` lists are purely descriptive metadata in `Decision.as_dict()`, never consulted by the decision logic itself).
5. `transitions.resolve(mode="DRY_RUN", decision="ESCALATE", ...)` → `needs_approval=True` regardless of mode. `approvals_satisfied(...)` finds no matching two-person record → Governor responds `{"minted": false, "verdict": {...}, "reason": "policy verdict ESCALATE; human approval required"}` (HTTP 200 — this is Governor's normal, well-formed response shape for a refusal, not an error status).
6. `authorize` treats a well-formed refusal as a successful call: it records the outcome and returns `ok: true`. A refusal is the correct, expected outcome today — `authorize`'s job is to ask and faithfully report, not to force an outcome. Only a genuine failure to reach Governor (timeout, connection error, malformed response) is treated as a tool failure, in the same fail-closed spirit as `safety_client.py` — no result is fabricated on a communication failure.

### 4.4 Ledger and result shape

New Governance Ledger action `recover_authorization_attempted` (distinct from 2a's `recover_plan_approved`), written the same fail-soft way as 2a's `_write_ledger` (a ledger failure never blocks `authorize`'s own result; the whole write is inside one `try/except`, including session construction and rollback — the exact shape 2a's final review required). Payload: `{run_id, plan_hash, governor_plan_hash, governor_verdict: {decision, reason, risk_class}, minted: false, mode: "DRY_RUN"}`.

`authorize`'s tool result (persisted as this node's `result.data`, same convention as every other local tool in this flow):

```json
{"ok": true, "minted": false, "mode": "DRY_RUN",
 "verdict": {"decision": "ESCALATE", "reason": "...", "risk_class": "INFRASTRUCTURE_MUTATION"},
 "plan_hash": "sha256:...", "governor_plan_hash": "sha256:...", "ledger": true,
 "note": "Governor/Shepherd correctly refused — no capability minted, no second approver on record; this increment proves the pipeline, not a minted capability"}
```

## 5. Safety properties (each pinned by a test)

1. `authorize` never issues a Docker call of any kind — only HTTP calls to Governor.
2. A refusal (the expected outcome today) completes the flow successfully; it is never mistaken for a tool failure.
3. 2a's `plan_hash` and Governor's `governor_plan_hash` are never conflated in the result or the ledger payload.
4. A genuine communication failure to Governor (not a policy refusal) fails the node — fail-closed, matching `safety_client.py`'s stance.
5. A Governance Ledger write failure never blocks `authorize`'s own result (fail-soft, same as 2a).
6. Adding the `"container.restart"` literal to Governor's copy of `models.py` does not change `fleet-controller`'s copy or behavior at all.

## 6. Testing

Unit (`backend/tests/test_authorize_tools.py`): the Governor-plan builder is deterministic and its hash matches `canonical_hash`'s exact algorithm (mirrored, not imported, per the file-copy convention); `authorize` against a mocked `minted:false` mint response records the verdict and ledger entry without raising; a mocked connection failure to Governor is treated as a tool failure, not silently swallowed; a Ledger-write failure still returns `ok:true, ledger:false`; `get_flow("operator-recover").node("authorize")` exists with `tool: local.authorize` and connects from `seal` with no `condition`; `agents/governor/tests/test_transitions.py`-style parity check that adding the new literal doesn't change any existing transition-table test outcome (read-only confirmation, no code change to `transitions.py` needed).

## 7. Live proof (real containers, no mutation, no mocks)

Under the same RAM rules as Phase 1/2a (`available` ≥ 1.2GB always, ≥ 1.5GB before any build; build only what changed; `up -d --no-deps`; never `--force-recreate`):
1. Confirm whether `governor` can be started alone (`--no-deps`, named directly) without pulling in `fleet-controller`, despite both sharing `profiles: ["fleet"]` — resolve empirically, not a design blocker.
2. Extend `scripts/prove-recover.py`: after a plan seals, confirm `authorize` ran, its result shows `minted: false` and a Shepherd verdict of `ESCALATE`/`INFRASTRUCTURE_MUTATION`, and one new `recover_authorization_attempted` ledger row exists for the run.
3. Confirm, as in every prior live step, the target container's `StartedAt`/`RestartCount` are unchanged throughout.

## 8. Known limitations / deferred (not fixed in this increment)

- No capability ever mints in this increment, by design — the pipeline's fail-closed behavior is what's proven, not a working restart authorization.
- `governor_operator_key.txt` remains unprovisioned; the two-person `/v1/approvals` flow is untested here.
- Whether/how a future increment grants `container.restart` to a specific identity, and how the two-person rule is satisfied on a single-operator setup, are open decisions for a later, separate spec.
- The eventual LIVE-capable executor (a standalone, minimally-privileged service holding a restart-only write proxy) is not built here; this increment deliberately reuses `hypercode-core`'s existing footprint since nothing here can mutate anything.

## 9. Open items for review

1. The agent identity `authorize` presents to Shepherd (`"broski-operator"`) — confirm, since it's what any future capability grant would be scoped to.
2. Whether `governor` alone can be started without `fleet-controller` (§7.1) — resolved empirically during implementation, not blocking spec approval.

## 9.1 Amendments (2026-09-27, implementation)

**Port correction (§4.3 step 3):** the mint call is `POST http://governor:8080/v1/capabilities/mint`, **not** `:8089` as written above. `8080` is Governor's real in-cluster listen port (`agents/governor/Dockerfile`: `EXPOSE 8080`, `uvicorn ... --port 8080`); `8089` is only the host-published mapping in `docker-compose.fleet.yml` (`127.0.0.1:8089:8080`) for external/dev access, irrelevant to service-to-service calls. `authorize_tools.py`'s actual default (`_governor_url()` → `http://governor:8080`) was correct from the start; only this spec text had the wrong port. Independently verified by inspecting the real running containers: `governor` and `hypercode-core` share the network `hypercode_agents_net` (Docker's project-prefixed name — `agents-net` alone does not exist as a bare network name), so the container-name DNS resolution this URL depends on works as designed.

**§7.1 resolved:** `governor` starts alone via `--no-deps` named directly, but the bare 2-file set (`docker-compose.yml` + `docker-compose.fleet.yml`) fails at compose's `depends_on: safety-shepherd` resolution — that service is only *defined* in `docker-compose.agents.yml` (profile-gated `["agents","safety"]`), so `docker compose config`/`up` needs that file present too, plus both the `agents` and `fleet` profiles activated (`--profile agents --profile fleet`) for compose to resolve the reference at all. `--no-deps` on the `up` command itself then correctly limits what actually starts to `governor` alone — confirmed via `docker ps` immediately after: `fleet-controller` did not start, so no Lean-Operations-Mode cleanup was needed. Full working command:
```
docker compose -f docker-compose.yml -f docker-compose.agents.yml -f docker-compose.fleet.yml \
  --profile agents --profile fleet up -d --no-deps governor
```

**Live proof, real (no mocks), 2026-09-27:** `hypercode-core` rebuilt + recreated (`up -d --no-deps`, never `--force-recreate`) with the `authorize` wiring; `governor` built fresh (never built on this box before) and started via the command above, healthy in 27s. `scripts/prove-recover.py`'s `phaseA` (extended with the new `authorize`/Governor assertions in this increment) ran inside `hypercode-core` against a real throwaway unhealthy container: **all 27 lines PASS**, including the pipeline's core claim — a real, unmocked round-trip returned `minted: false`, `mode: "DRY_RUN"`, `verdict.decision: "ESCALATE"`, `verdict.risk_class: "INFRASTRUCTURE_MUTATION"`, and exactly one `recover_authorization_attempted` Governance Ledger row for the run. The target container's `StartedAt`/`RestartCount` were unchanged throughout. **Nothing minted, nothing executed** — this run is proof the pipeline fails closed exactly as designed, not proof of a working capability grant. RAM stayed at 2.0-2.1GB available throughout (host ceiling is 3.9GB total); both containers ended healthy, restarts=0, oom=false.

**Bug found and fixed during this increment, out of the original spec's scope:** `scripts/prove-recover.py`'s `phaseB2()` (the Phase 2a restart-recovery proof) read `done["result"]["report"]["sealed"]`, which no longer exists once `authorize` became `operator-recover`'s last node — `result.report` is always the *last completed node's* data (confirmed in `backend/app/broski_operator/status.py:build_result`), which is now `authorize`'s dict, not `seal`'s. Fixed with the same technique already used for `phaseA`: prove `seal` ran via `"seal" in done["result"]["nodes"]` instead of a key that no longer survives into `report`. Not re-run live in this increment (Task 4's live proof only exercises `phaseA`), but the fix means `phaseB1`/`phaseB2` won't `KeyError` the next time someone re-verifies the restart-recovery-survives-a-core-restart scenario from Phase 2a.
