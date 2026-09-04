# Autonomous Control Plane — North-Star Design

> **Status:** North-star architecture. Phases 0–1 partially built (see §8);
> this document is the target shape for Phases 1–5 and the governing
> reference for every phase's own implementation spec. **Only the Phase 2
> cut line (§9) is scheduled for build next** — everything else here is
> documented, not built.
>
> Supersedes nothing. Extends `2026-08-20-fleet-controller-phase0-design.md`,
> `2026-08-21-mission-director-phase1-design.md`,
> `2026-08-21-mission-evaluator-design.md`,
> `2026-08-24-fleet-dependency-graph-design.md`.

---

## Context & Constraints

### Where this comes from

Two verdict documents at the ecosystem root — `THE AGI-grade move` and
`The Hyper AGI Core Verdict` (both 2026-08-20) — argue that HyperCode's
25-agent fleet should evolve into an **autonomous control system with
constitutional separation of powers**, not a bigger swarm. This spec turns
that argument into a buildable architecture.

Explicitly **not literal AGI**. The source material's own framing: the goal
is *safe increasing autonomy with hard containment*, not general
intelligence. "AGI-grade" here means one thing — **increase capability only
after the control boundary is mechanically enforceable.**

### The governing invariant

> **No component may both interpret LLM output and hold
> infrastructure-mutation authority.**

If `mission-director` is fully compromised (prompt injection, model
misbehaviour, confused-deputy, retry bug, poisoned tool output) it can
produce bad *proposals* — but cannot alter Docker, dispatch agents, or
mutate the repo. If `fleet-controller` is fully compromised it cannot
*invent* authority, because every action it takes requires a signed,
scope-bound, unexpired, replay-checked capability that only the Governor
can mint.

### Success criteria — the AGI-readiness test

Not "how many agents." These five properties, each with a re-runnable
proof:

| Property | Target |
|---|---|
| Generality | Solves different mission types through one typed plan schema |
| Autonomy | Progresses without constant human prompting |
| **Correctability** | Bro can pause, revoke, roll back, and kill it — fast, and without a clean shutdown path |
| **Transparency** | Every decision reconstructable from the append-only ledger alone |
| **Containment** | A fully compromised planner causes **zero** infrastructure mutation |

Containment is the hard one and the acceptance gate for every live phase.

### Ground-truth findings (live repo audit, 2026-09-04)

- **`fleet-controller` (Phase 0) is live** at `:8094` behind `--profile
  fleet`. `agents/fleet-controller/{main,models,plan_validator,safety_client,
  ledger_client}.py`. Structurally inert: no Docker socket, no `DOCKER_HOST`,
  no crew credential, no LLM client. Fails **closed** on Shepherd
  unavailability. `PlanResponse` already reserves `capability:
  Optional[str] = None` (`models.py:57`) and `mode: Literal["DRY_RUN"]`
  (`models.py:53`). `execution.performed` has no code path that sets it
  `True`.
- **`mission-director` (Phase 1 + 2) is live** at `:8086`. Stateless LLM
  planner; zero mutation authority. Human-facing `propose`/`review`
  endpoints live in `hypercode-core`
  (`backend/app/api/v1/endpoints/missions.py`), the only sanctioned caller
  of its unauthenticated `/v1/plan` route. `review_mission` already
  hard-rejects (`409`) approval of a `BLOCK` mission and requires an
  explicit `escalation_reason` (`422`) for `ESCALATE`. Phase 2 added a
  purely-advisory dependency-`impact` list per proposal.
- **`safety-shepherd` is live** at `:8096`. `/evaluate` (`safety_shepherd.py`
  handler ~`:335`, request shape `EvaluateRequest` ~`:231`) returns
  `{decision, reason, rule, category}` with `decision ∈ {ALLOW, BLOCK,
  ESCALATE}`. `category: "docker"` is already in the `DANGEROUS` set
  (`policy.py:33`) and already defaults to `ESCALATE` without a capability
  grant (`policy.py` precedence rule 9). **Stateless. Holds no keys.**
- **Governance Ledger is live**: `POST /api/v1/governance/ledger`
  (`backend/app/api/v1/endpoints/governance.py`), append-only, free-form
  `payload: dict` column — no migration needed to log anything this spec
  introduces. `hypercode-core` reachable on `agents-net`.
- **`crew-orchestrator`** (`:8081`) has `safety_gate.py` that fails **open**
  on Shepherd error — deliberate, for routine task dispatch, 3 live callers
  (`crew-orchestrator`, `hyperflow_runner.py`, `coder-studio/shepherd.py`).
  **Out of scope here** — nothing in this architecture routes through it;
  changing shared fail-open behaviour for 3 callers is its own decision.
  It has no multi-step plan-submission endpoint (`/execute` takes one
  task); `workflow_engine.py` `/workflow/execute` is the Phase 1/4
  investigation target.
- Redis convention (Sacred Rule): DB 1 = cache, DB 2 = rate limits, never
  mixed. The replay/lease/kill state this spec adds needs a **dedicated
  logical DB**, not 1 or 2.
- The dashboard-session JWT dependency is **HS256 (symmetric)** — reused as
  a starting point only for the *operator token* on `/v1/kill`, never for
  capabilities (see §5 rationale).

### The architecture choice (settled)

Three approaches to the planner/executor split were weighed in the verdict
docs; **Approach C — hard separation** was chosen (the planner has zero
mutation authority, the deterministic controller has zero LLM). Confirmed
2026-09-04. This spec assumes it.

Realization approach for governance state: **Approach B — synchronous
Governor, state in existing infra** (Governance Ledger + Redis), no new
datastore. A queue-mediated Governor (Approach C-realization) is documented
as the Phase 1 evolution, arriving with the typed-dispatch queue.

Autonomy ceiling (stated 2026-09-04): **full autonomous ops** — the
long-term goal is the system running its own infrastructure end-to-end,
humans auditing after the fact and holding the kill switch. The full
lease / rollback / replay / two-person machinery is therefore in this
design. The *path* there still runs through every gated phase in order.

---

## Goal

Define the end-state architecture — three planes, a structured verdict, a
signed capability model, a Governor service holding kill-switch + keys +
leases + approvals, and a fixed transition table — such that each of the
five AGI-readiness properties has a mechanically-enforced basis rather than
a policy promise. Then cut the smallest slice (Phase 2) that makes the
capability boundary real while keeping `execution.performed` structurally
`false`.

---

## Design

### 1. The three planes

| Plane | Services | May | May **not** |
|---|---|---|---|
| **Cognitive** | `mission-director`, `project-strategist`, `brain-agent`, model router, memory retrieval | read project context; write proposed plans; write explanations; answer "which agents are suitable? (score + evidence + confidence)" | mutate anything; mint authority; decide what is *allowed*; answer "which agents are *permitted* to execute" |
| **Governance** | `safety-shepherd` (verdict), **`governor`** (new), Governance Ledger | evaluate proposals; issue scope-bound signed capabilities; revoke; record; hold the kill switch; renew the system lease; record approvals | invent mission plans; execute actions |
| **Execution** | `fleet-controller`, `hyperflow`, `crew-orchestrator`, `coder-studio`, Compose/Docker adapters | execute **only** a typed, signed, unexpired, replay-checked capability | interpret natural language; hold a model credential; act without a capability |

`brain-agent` is a **recommender, not an authority**. Recommended response
shape (documented target, not built here):

```json
{
  "candidates": [
    {"agent": "database-architect", "score": 0.87, "evidence": ["3 prior successful migration missions"], "confidence": 0.76}
  ],
  "missing_capabilities": [],
  "recommendation_ttl_seconds": 900
}
```

The Governor / fleet-controller still verify role, scope, health, capacity,
and policy independently of any recommendation.

### 2. Upgrade A — structured verdict (Safety Shepherd)

`/evaluate` keeps returning today's `{decision, reason, rule, category}`
(additive change, no breakage for current callers) and **adds**:

```json
{
  "decision": "ESCALATE",
  "risk_class": "INFRASTRUCTURE_MUTATION",
  "reasons": ["Requested profile changes runtime state", "Human approval required outside DRY_RUN"],
  "allowed_actions": ["compose_profile.preview", "compose_config.validate"],
  "blocked_actions": ["compose_profile.start", "compose_profile.stop"],
  "policy_version": "safety-2026-09-04.1"
}
```

- `risk_class ∈ {READ_ONLY, REVERSIBLE_ACTION, INFRASTRUCTURE_MUTATION,
  DESTRUCTIVE}` — drives the Governor's transition table (§7) and the
  two-person rule (§6).
- `policy_version` is a constant string bumped by hand when policy changes;
  stamped into every capability and every ledger row so any past decision
  is reconstructable against the policy that produced it.
- Shepherd **stays stateless**. No keys, no kill-switch, no minting. It
  became more precise, nothing else.

### 3. Upgrade B — the plan hash becomes load-bearing

`fleet-controller` already computes `plan_hash =
"sha256:" + sha256(canonical_json(plan))` with sorted keys and
`separators=(",", ":")` (`models.py:canonical_hash`). Phase 0 only asserts
tamper-evidence by test. From Phase 2:

- Shepherd's verdict is requested **for a specific `plan_hash`** and the
  Governor records `(verdict_id, plan_hash)` together.
- The minted capability embeds `plan_hash`.
- The execution plane recomputes the hash of the plan it holds and refuses
  if it differs from the capability's `plan_hash` by one character.

Tamper-evidence stops being a test assertion and becomes a signature check.

### 4. Capability token format

**PASETO v4.public** (Ed25519). Chosen over JWT to remove
algorithm-confusion and `alg:none` foot-guns — the token type *is* the
algorithm. Governor holds the Ed25519 **private key** (Docker secret, never
an env var); every verifier holds **only the public key** and can verify
offline.

Claims:

```json
{
  "iss": "governor",
  "sub": "fleet-controller",
  "mission_id": "mission_01J...",
  "plan_hash": "sha256:...",
  "action": "compose_profile.start",
  "target": "agents",
  "mode": "DRY_RUN",
  "max_attempts": 1,
  "not_before": "2026-09-04T13:00:00Z",
  "expires_at": "2026-09-04T13:10:00Z",
  "jti": "cap_01J...",
  "verdict_id": "verdict_01J...",
  "policy_version": "safety-2026-09-04.1",
  "approval_id": null
}
```

- Short TTL — minutes, not hours. `not_before` guards clock-skew abuse.
- `max_attempts: 1` + `jti` recorded in the replay store on first use =
  single-use.
- `approval_id` is `null` unless the transition table required a human
  approval, in which case it references a recorded, two-person-checked
  approval.

**Verification order (execution plane, all must pass):**

1. signature valid against the Governor public key
2. `iss == "governor"`
3. `sub` == my own service identity
4. `plan_hash` == hash of the plan I actually hold
5. `action` + `target` are within the scope I was asked to perform
6. `mode` matches my current run mode
7. now ∈ [`not_before`, `expires_at`]
8. `jti` not present in the replay store (then: record it)
9. kill-switch clear (Governor `/v1/capabilities/verify` or cached lease)
10. system lease currently valid

Any failure → refuse, write a `capability.rejected` ledger row, execute
nothing.

### 5. The Governor service — `agents/governor/`

New boring daemon. Same containment as `fleet-controller`: **no Docker
socket, no `DOCKER_HOST`, no crew credential, no LLM/MCP/GitHub-write.** Its
one privileged asset is the Ed25519 private key.

- Directory shape mirrors `fleet-controller/`: `Dockerfile`,
  `requirements.txt` (fastapi, uvicorn, httpx, pydantic, a PASETO/Ed25519
  lib — `pyseto` or `paseto` + `cryptography`), `main.py`, `models.py`,
  `keys.py`, `transitions.py`, `replay.py` (Redis), `lease.py`,
  `killswitch.py`, `ledger_client.py`, `tests/`.
- Port: next free `80xx` (candidate `:8089` — confirm at implementation;
  `:8095`–`:8099` are taken).
- Compose: behind `--profile fleet`, on `agents-net` (to reach Shepherd
  and be reached by `fleet-controller`) + Redis reachable (dedicated
  logical DB). `depends_on: safety-shepherd: condition: service_started`.
  **No** `crew-orchestrator` health gate (same named exception as
  `fleet-controller`).
- Private key: Docker secret mounted at a read-only path; `keys.py` loads
  it once at startup and never logs it. Public key published as a
  non-secret file / config value that verifiers bake in.

| Endpoint | Purpose |
|---|---|
| `POST /v1/capabilities/mint` | Body: proposal + `plan_hash` + `mode` + requested `action`/`target`. Validates schema/allowlist (reuse `fleet-controller`'s `plan_validator`), calls Shepherd `/evaluate` for that `plan_hash`, applies the transition table (§7). Mints a capability **only** if the table says so AND kill-switch clear AND (approval satisfied where required) AND lease valid. Otherwise returns the structured verdict with `capability: null` and a machine reason. Writes `verdict.issued` + (`capability.minted` \| `mint.refused`) ledger rows. |
| `POST /v1/capabilities/verify` | Public-key verification is offline-doable; this endpoint adds the stateful checks (`jti` unused, not revoked, kill-switch, lease) for callers that want them centralized. Idempotent read; does **not** burn the `jti` (the executor does that when it acts). |
| `POST /v1/capabilities/revoke` | Body: `jti` or `mission_id`. Adds to the revocation set (Redis + ledger). Effective immediately for all future verifies. |
| `POST /v1/kill` / `POST /v1/unkill` | `kill`: authenticated with an **operator token** (HS256, reusing the dashboard-session secret is acceptable *here* — this is a human-to-Governor call, not a service authority) **or** triggered by the sentinel file `/governance/KILL` appearing on a watched volume (file present ⇒ killed, even with the API and Redis down). `unkill`: API + operator token + a mandatory `reason` — deleting the file alone never un-kills. Both write ledger rows. |
| `POST /v1/approvals` / `GET /v1/approvals/{id}` | Records a human decision (`approver_id`, `mission_id`, `plan_hash`, `decision`, `reason`). Enforces the **two-person rule** for `risk_class ∈ {INFRASTRUCTURE_MUTATION, DESTRUCTIVE}`: two distinct `approver_id`s, neither equal to the mission's proposer. |
| `GET /v1/lease` + internal renew loop | Returns the current system-lease record + expiry. A background loop re-issues the lease every ~2–3 min with a ~5 min TTL **iff** kill-switch clear and Shepherd `/health` OK. |
| `GET /health` | Liveness only. |

**State (Approach B — no new datastore):**

- **Governance Ledger** (append-only, existing endpoint, free-form
  `payload`): every verdict, mint, refusal, rejection, revoke, approval,
  kill/unkill, lease issuance, action start/result/rollback.
- **Redis, dedicated logical DB:** `jti` replay set (with TTL ≥ max
  capability TTL), revocation set, current lease record, kill flag.
- **Sentinel file** on a watched volume: the un-clearable-by-executors
  kill trigger.
- Governor is **restart-safe**: on boot it rebuilds live state (kill flag,
  lease, revocations) from Redis, and can reconstruct history from the
  ledger. It stores nothing that only exists in its own memory.

### 6. Human approval & the two-person rule

- Phase 2 ships `/v1/approvals` as a **recording + enforcement** endpoint
  only — no UI. An approval is created by an authenticated call carrying an
  `approver_id`.
- Phase 3 adds the surface: extend `hypercode-core` Mission Control (where
  `mission-director`'s `propose`/`review` already live). The view shows:
  mission, plan, `risk_class`, services affected (from the existing
  dependency-`impact` list), expected diff, rollback plan, and
  **Approve / Reject / Kill** controls.
- Two-person rule (enforced by the Governor, not the UI): for
  `INFRASTRUCTURE_MUTATION` and `DESTRUCTIVE`, a mint requires two distinct
  approvals from two distinct `approver_id`s, neither being the proposer.
- Dangerous classes that always require approval regardless of mode:
  `DRY_RUN`→`LIVE` switch, `prod`/`gpu` profiles, stopping core services,
  DB migrations, image builds from untrusted code, write-enabled worktrees,
  external GitHub mutations.

### 7. The transition table (fixed code — never LLM-decided)

`transitions.py`, one function, exhaustive over `(mode, decision,
kill_switch)`, one test per row:

| Mode | Verdict | Kill-switch | Result |
|---|---|---|---|
| `DRY_RUN` | `ALLOW` | clear | mint `mode:DRY_RUN` capability — preview only; `performed` always `false` |
| `DRY_RUN` | `ESCALATE` | clear | preview + open an approval request; capability withheld until `approval_id` exists |
| `DRY_RUN` | `BLOCK` | — | reject, no capability |
| `LIVE` | `ALLOW` | clear | mint `mode:LIVE` capability — scoped, single-use, short TTL |
| `LIVE` | `ESCALATE` | clear | **no capability** until a matching `approval_id` (two-person for dangerous classes) |
| `LIVE` | `BLOCK` | — | reject |
| any | any | **ON** | reject every mutation; only `READ_ONLY` / preview capabilities may be minted |

### 8. Lease-based execution (corrigibility without a clean shutdown)

- The execution plane holds authority only while the **system lease** is
  valid.
- The Governor renews it on a loop *only if* kill-switch clear and Shepherd
  healthy.
- `fleet-controller` (and every executor) checks `lease valid` as the
  **last** gate before any live action.
- **Kill switch flips ⇒ Governor stops renewing ⇒ the entire execution
  plane goes inert within one lease period (~5 min) on its own** — no
  reliance on signals, orchestrated shutdown, or the executors
  cooperating.

---

## Data flow — end to end

A mission that wants to start the `agents` Compose profile:

```
human goal ──▶ mission-director            [COGNITIVE]
                 │  LLM reasoning ONLY → typed PlanRequest + canonical plan_hash
                 │  ledger: plan.proposed {mission_id, plan_hash, goal, context}
                 ▼
              governor  POST /v1/capabilities/mint   [GOVERNANCE]
                 │  1. schema/allowlist validate (reuse fleet-controller plan_validator)
                 │  2. safety-shepherd /evaluate(plan_hash) → structured verdict
                 │     ledger: verdict.issued {verdict_id, risk_class, policy_version, plan_hash}
                 │  3. transition table (mode × decision × kill_switch)
                 │  4. if ESCALATE → require approval_id (two-person if dangerous class)
                 │  5. kill-switch clear? system lease valid?
                 │  6. mint PASETO v4.public capability bound to plan_hash+action+target+jti
                 │     ledger: capability.minted {jti, verdict_id, expires_at}   (or mint.refused)
                 ▼
              fleet-controller               [EXECUTION]
                 │  verify: sig → iss → sub → plan_hash → scope → mode → time
                 │          → jti unused (record) → kill-switch → lease
                 │  DRY_RUN → preview only, performed=false        (Phase 0 behaviour, unchanged)
                 │  LIVE    → execute ONE scoped action, burn the jti, renew-or-expire the lease
                 │     ledger: action.started / action.result / rollback.status
                 ▼
              crew-orchestrator / Compose adapter   [EXECUTION]
                 typed command — no natural language, no model credential
```

Every hop writes an append-only Governance Ledger row. **Transparency =
the full chain (goal → context → plan → hash → verdict → approver →
capability `jti` → action → result → rollback) is reconstructable from the
ledger alone.**

---

## The phase roadmap, mapped onto this architecture

| Phase | Adds | Execution ceiling | Status |
|---|---|---|---|
| **0** | `fleet-controller`, fail-closed, `DRY_RUN` preview | previews nothing | ✅ live |
| **1** | typed dispatch queue: `crew.plan.submit` action kind; durable proposal queue (queue-mediated realization); investigate `workflow_engine.py` `/workflow/execute` as the target | still zero mutation | not built |
| **2** ⬅ **first build** | `governor` service; structured verdict schema; PASETO capabilities; replay store; kill-switch (+ sentinel file); lease loop; `fleet-controller` *requires* a valid capability | still `DRY_RUN`, `performed=false` always | not built |
| **3** | human-approval surface in `hypercode-core` Mission Control; two-person rule wired to the UI | approval gating live; still no execution | not built |
| **4** | **one** live action — `crew.plan.submit` only (lowest-risk, reversible, no Docker); `LIVE` capabilities issued; replay + failure + kill-switch + rollback tests must pass first | 1 reversible action type | not built |
| **5** | `compose_profile.start` — `agents` profile only, never `prod`/`gpu`/destructive; full lease/rollback/replay/two-person gate | scoped infra mutation | not built |
| later | hash-chained verdict ledger; `brain-agent` capability-recommender; auto-improvement loop feeding proposals into the cognitive plane | — | not built |

**Full autonomous ops** (the stated ceiling) = Phase 5 running unattended,
permitted only once every AGI-readiness property — especially
**Containment: compromised planner → zero mutation** — has a passing,
re-runnable proof in CI.

---

## Phase 2 — the cut line for the next implementation spec

### In scope

- **`agents/governor/`** — new service, containment-minimal, Ed25519 private
  key as a Docker secret. Endpoints: `/v1/capabilities/mint`,
  `/v1/capabilities/verify`, `/v1/capabilities/revoke`, `/v1/kill`,
  `/v1/unkill`, `/v1/approvals` (+ `GET /v1/approvals/{id}`), `/v1/lease`,
  `/health`. `/v1/approvals` records + enforces the two-person rule; **no
  dashboard**.
- **PASETO v4.public mint/verify** — canonical claim set (§4),
  `plan_hash` binding, short TTL, `not_before`.
- **Redis replay store** — `jti` set + revocation set + lease record + kill
  flag, in a **dedicated logical DB** (not 1/cache, not 2/rate-limits).
- **System lease** — record + background renew loop (renew iff kill-switch
  clear and Shepherd `/health` OK).
- **Kill-switch** — Redis flag **and** a watched sentinel file
  (`/governance/KILL`); either set ⇒ killed; unreachable dependency ⇒
  fail-closed (treated as killed for mint purposes).
- **Transition table** — `transitions.py` as fixed code; one test per row
  of §7.
- **Safety Shepherd** — additive structured-verdict fields on `/evaluate`
  (§2); `policy_version` constant; `risk_class` mapping for the existing
  `DANGEROUS` categories. Existing callers unaffected (old fields retained).
- **`fleet-controller`** — new capability-verify step on
  `/v1/plans/preview` (verification order §4); populates the already-
  reserved `capability` response field; **`execution.performed` stays
  hard-`false`** — no execution code added, no Docker client added.
- **Governance Ledger** — new `action` values written at each hop; no
  migration (`payload` is free-form).
- **Compose wiring** — `governor` behind `--profile fleet`, `agents-net` +
  Redis, no socket / `DOCKER_HOST` / crew credential; `depends_on:
  safety-shepherd`. CI negative-capability check (`docker inspect ... Env`
  grep; `docker compose config` no `docker.sock`) extended to `governor`.

### Contract tests (the ones that matter)

- forged signature → `mint`/`verify` reject
- expired / not-yet-valid capability → reject
- replayed `jti` (second use) → reject
- `plan_hash` mismatch (plan mutated after minting) → reject
- kill-switch ON → `mint` refused for any mutation; lease renew loop stops;
  existing `LIVE` capabilities fail their lease gate within one period
- sentinel file present → same as kill-switch ON, even with Redis down
- Shepherd unreachable / malformed / missing `decision` → `mint` refused
  (fail-closed), never a silent allow
- `ESCALATE` + `INFRASTRUCTURE_MUTATION` → no capability without two
  distinct approvals, neither the proposer
- **`execution.performed` is `false` in every `fleet-controller` response
  Phase 2 can produce** — mocked "would dispatch" callable never invoked
- CI: rendered `governor` manifest has no `docker.sock`, no `DOCKER_HOST`,
  no `*_API_KEY` beyond what it legitimately needs (Shepherd URL, Redis
  URL, ledger URL, operator-token secret)

### Out of scope (documented above, not built in Phase 2)

- durable proposal queue and `crew.plan.submit` (Phase 1)
- approval dashboard UI (Phase 3)
- any `LIVE` capability issuance or execution code path (Phase 4+)
- `compose_profile.start` / real infra mutation (Phase 5)
- hash-chained verdict ledger; `brain-agent` recommender changes
- `crew-orchestrator/safety_gate.py` fail-open behaviour (separate decision,
  3 live callers)

---

## Rollout order (Phase 2)

1. Scaffold `agents/governor/` — Dockerfile, requirements, empty FastAPI
   app with `/health`, matching every other agent's build/port/healthcheck
   convention. Compose entry behind `--profile fleet`.
2. `keys.py` — load Ed25519 private key from the Docker secret at startup;
   publish the public key; unit test sign/verify round-trip.
3. `models.py` + capability mint/verify (§4) + tests for signature, expiry,
   `not_before`, `plan_hash` binding.
4. `replay.py` (Redis, dedicated DB) — `jti` set, revocation set + tests
   (replay rejected, revoke effective).
5. `killswitch.py` — Redis flag + sentinel-file watcher, fail-closed +
   tests.
6. `lease.py` — lease record + renew loop (renew iff kill clear + Shepherd
   healthy) + tests.
7. `transitions.py` — the §7 table as pure code + one test per row.
8. Safety Shepherd structured-verdict fields (§2) — additive, with a test
   proving existing callers still parse the response.
9. `POST /v1/capabilities/mint` — wire validate → Shepherd → transition →
   gates → mint, with ledger writes; contract tests.
10. `/v1/capabilities/verify`, `/v1/capabilities/revoke`, `/v1/approvals`
    (+ two-person enforcement), `/v1/kill` + `/v1/unkill` + tests.
11. `fleet-controller` — capability-verify step on `/v1/plans/preview`;
    populate `capability`; prove `performed` stays `false`.
12. CI negative-capability check extended to `governor`.
13. Manual smoke test: valid plan + Shepherd `ALLOW` → `DRY_RUN` capability
    minted, `fleet-controller` verifies it, `performed=false`; kill-switch
    ON → mint refused + lease stops; sentinel file with Redis stopped →
    still killed; Shepherd killed mid-request → mint refused fail-closed;
    replayed capability → rejected. Confirm each lands exactly where the
    transition table and verification order say.
