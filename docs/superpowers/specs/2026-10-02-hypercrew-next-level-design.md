# HyperCrew — agents working together, the next level

**Date:** 2026-10-02 · **Status:** draft, awaiting Bro's review · **Origin:** `HyperCode Future Research Brief` (MCP stateless core × Celery), re-based on what the repo actually has — same method as `2026-09-26-broski-operator-design.md`.

---

## 0. TL;DR (read this, skip the rest if you're tired)

- **Don't build the brief's `mcp_tasks` + outbox + Celery path.** `hyperflow_runs` + `/api/v1/operator/tasks` + `hypercode-mcp-server` already give durable, resumable, cancellable async tasks, live-proven 2026-09-26/27. Celery stays for batch work only.
- **The missing piece is collaboration, not plumbing.** Agents today are individually live but hand work over as free text. HyperCrew adds a typed **Baton** (handoff contract), a **Squad flow** (plan → build → verify → guard → human gate → seal), and a **Calm Card** (one next action, always).
- **RAM is the real constraint** (N22: 4 GB box, ≥1.2 GB floor). So: max **3 agents awake per squad**, on-demand wake, RAM-gated.
- **Safety first:** Phase 1 squads are **read / propose / draft-PR only**. No container mutation until the Governor grant decision (2b) is made.
- **Gamification is server-side and evidence-backed.** XP only for sealed, verified work. Agents can't farm it.
- **Two weeks, 10 days, one proof gate per day.** Details in §8.

---

## 1. Contradictions surfaced (per CLAUDE.md rule)

| Source A | Source B | Resolution |
|---|---|---|
| Research brief: add `mcp_tasks` table, Celery MCP adapter, outbox | `WHATS_DONE` 2026-09-26: operator tasks on `hyperflow_runs` already shipped + MCP-proven | Use HyperFlow. Brief's *ideas* (idempotency, cancellation flag, progress stream, tool allow-list) are kept where HyperFlow lacks them. |
| `CLAUDE.md`: 25–27 agents "Live", zero unhealthy / 67 containers | `STATUS.md` + 09-26 entry: ~27–30 containers up, obs stack stopped, "Lean Operations Mode" | Plan targets **lean mode** as the baseline. Live status beats CLAUDE.md. |
| Brief: outbox needed so DB row and queue never drift | HyperFlow run row is the source of truth and `recover_runs()` resumes on boot | Outbox not needed for HyperFlow. Only relevant if a flow node enqueues Celery — then enqueue is idempotent by `run_id:node`. |

---

## 2. Principles

1. **Reuse, don't rebuild.** `WHATS_DONE.md` is the do-not-rebuild list.
2. **Humans approve. Agents never self-approve.** Same rule as operator Phase 1 (superuser JWT only).
3. **Fail closed.** Shepherd/Governor unreachable → BLOCK, as today.
4. **One thing at a time.** Every surface ends in a single next action (§6).
5. **RAM-gated.** No optional service starts below 1.2 GB available.
6. **Evidence or it didn't happen.** XP, "done", and handovers all point at stored evidence.

---

## 3. Architecture

```
 Bro / Discord / Claude (MCP client) / Dashboard "Crew Board"
                    │
        hypercode-mcp-server :8823        ← MCP façade (stateless requests)
          hypercode_crew_start / _status / task_get / task_cancel
                    │
        hypercode-core  /api/v1/operator/tasks   ← exists
                    │
        HyperFlowRunner  (hyperflow_runs: durable state + Baton chain)
          │ node types: agent_role | tool | human_approval_gate
          │            + NEW agent_dispatch (via crew-orchestrator)
          │
   ┌──────┼──────────────┬───────────────┬─────────────────┐
   ▼      ▼              ▼               ▼                 ▼
 mission- crew-         safety-       governor         throttle-agent
 director orchestrator  shepherd      (capabilities,   (RAM slots)
 (plan)   (dispatch)    (every node)  kill-switch)
   │          │
   │   ┌──────┴───────── squad members (≤3 awake) ──────────┐
   │   coder / specialists · qa-engineer · security-engineer │
   └───────────────────────────────────────────────────────┘
                    │
   Evidence bundle (in run state)  →  Governance Ledger  →  Quest Settler → broski-economy-mcp
```

**What's new vs. what exists**

| Layer | Exists | New in HyperCrew |
|---|---|---|
| Durable tasks, approvals, cancel, restart recovery | ✅ operator Phase 1 | — |
| MCP façade, agent-key auth | ✅ `hypercode-mcp-server` | 2 tools: `hypercode_crew_start`, `hypercode_crew_status` |
| Safety per node, capability tokens, kill-switch | ✅ Shepherd + Governor | — (squad uses them as-is) |
| Dispatch to agents | ✅ crew-orchestrator | Wire seam card (c) / N13 so dispatch is Shepherd-checked |
| Handoff between agents | ❌ free text | **Baton** contract |
| Multi-agent flow | ❌ only `inspect`, `smoke`, `recover` | **`hypercode.crew`** flow |
| RAM awareness | ❌ manual rules | **Slot gate** (cap 3) |
| ND-friendly output | partial | **Calm Card** formatter + dashboard panel |
| Rewards | ✅ economy MCP, pets | **Quest Settler** (server-side, idempotent) |

### 3.1 The Baton (handoff contract)

Typed JSON stored in `hyperflow_runs.state.batons[]`. Pydantic model, validated on every handoff.

```json
{
  "baton_id": "run123:build:1",
  "from_role": "builder", "to_role": "verifier",
  "goal": "one sentence",
  "done_so_far": ["max 5 short bullets"],
  "next_action": "one sentence",
  "constraints": ["no container mutation", "draft PR only"],
  "evidence": [{"kind": "diff|test|log", "ref": "…", "sha256": "…"}],
  "open_questions": [],
  "risk_hint": "read|propose|mutation"
}
```

Rules: summary fields have hard length caps (forces short, ADHD-friendly handoffs and keeps context small). `risk_hint` feeds Shepherd's existing `SafetyHint`. Evidence is referenced, never pasted.

### 3.2 Why Postgres JSON, not a new Redis blackboard

Redis DB 1 = cache, DB 2 = rate limits — sacred, no mixing. The run row already holds durable context, survives core restarts, and is what `recover_runs()` reads. No new store.

### 3.3 Where Celery fits

Only for work that shouldn't live in core's event loop (long test runs, report generation). A `tool` node may `send_task` to `hypercode-low/normal`, idempotent by `run_id:node`. Existing queues + DLQ unchanged. No MCP-specific queue.

### 3.4 Carry over from the brief (only the parts HyperFlow lacks)

- **Idempotency key on start.** Verify whether `POST /operator/tasks` already dedups; if not, add `idempotency_key` (unique per caller+key).
- **Static tool registry.** MCP tools resolve through an allow-list; LLM never names queues, containers, Redis keys. (Already the pattern — add a test asserting it for the new tools.)
- **Cooperative cancel** checked between nodes (exists) — extend to `agent_dispatch` nodes via a Redis flag with a TTL (use the existing operator DB, not DB 1/2 — verify which DB cancel flags use before adding).

---

## 4. Agent roles (mapped to agents that already exist)

| Role | Who (existing) | Job | Can mutate? |
|---|---|---|---|
| **Conductor** | `mission-director` + `crew-orchestrator` | Turn goal → plan; dispatch nodes | No |
| **Scout** | `hypercode.inspect`, `agent-registry` | Read-only state + impact set | No |
| **Architect** | `system-architect` / `hyper-architect` | Design notes, interface choices | No |
| **Builder** | `coder-agent`, backend/frontend specialists | Write code on a branch | Branch + **draft PR only** |
| **Verifier** | `qa-engineer`, `test-agent` | Run tests (RAM-gated), report | No |
| **Guardian** | `safety-shepherd`, `security-engineer` | ALLOW/BLOCK/ESCALATE every node | No |
| **Gatekeeper** | `governor` | Capability tokens, kill-switch | Signs only |
| **Healer** | `healer-agent` via `hypercode.recover` | Propose restarts (DRY_RUN until 2b decided) | Not yet |
| **Quartermaster** | `throttle-agent` | Hands out RAM slots | No |
| **Focus Guide** | `hyper-split-agent`, `session-snapshot`, `goal-keeper` | Chunk work, protect focus, snapshot state | No |
| **Scribe** | `broski-coo`, `tips-tricks-writer` | Brief + handover drafts (as proposals) | Drafts only |
| **Banker** | `broski-economy-mcp` | Holds the ledger; only the Quest Settler may call it | Tokens only |

**Zero new containers required.** If `throttle-agent`'s unbuilt `MemStream` dependency (NEXT_TASKS #2b) blocks the slot gate, fall back to a static `CREW_MAX_AWAKE=3` cap in core and note it — don't build MemStream for this.

---

## 5. Workflows

### W1 — Build a feature (`hypercode.crew`, the headline flow)

```
plan(Conductor) → [GATE: human approves plan + plan_hash]
  → chunk(Focus Guide: ≤25-min chunks)
  → build(Builder) → verify(Verifier) → guard(Guardian)
      ↺ one automatic retry loop on verify fail (max 2), then escalate to human
  → [GATE: human reviews diff summary + evidence]
  → seal(evidence bundle + ledger row) → draft PR opened
  → scribe(handover draft) → settle(XP)
```

Same `plan_hash` pattern as `recover`: approve only with the exact hash shown.

### W2 — Fix it (exists)
`hypercode.recover` unchanged; joins squads later as a Healer node once 2b's grant decision is made.

### W3 — "Where was I?" (Morning Card)
`broski-coo /brief` + `session-snapshot` → one Calm Card: yesterday's wins, **one** next task, RAM/fleet status as a single traffic light.

### W4 — Focus Session
Bro starts a quest. Crew goes **quiet mode**: notifications batched to chunk boundaries, no new asks except Guardian BLOCKs. Panic Mode (one button/command) collapses everything to: current chunk + "pause everything" + "save my place" (session-snapshot).

### W5 — Skill upgrade loop (later)
`hypercode-self-improver` runs as a squad with a mandatory human gate. Out of scope for the 2 weeks.

---

## 6. Neurodivergent-first spec (acceptance criteria, testable)

| Rule | Test |
|---|---|
| **Calm Card**: ≤5 lines TL;DR, exactly 1 `next_action`, detail collapsed by default | Unit test on the formatter: reject output with 0 or >1 next actions, >5 TL;DR lines |
| Short sentences, plain words, no walls of text | Length caps on Baton + Card fields, enforced in schema |
| **Predictable**: plan shown and approved *before* any action; state always visible (running / waiting-on-you / paused) | Flow can't leave `plan` without the gate; status enum has no "unknown" |
| **No time-pressure UI**: no countdowns that force action, no streak loss | Streaks use auto-freeze; assert no code path decrements XP |
| **Interrupt-safe**: leave any time, resume exactly (restart recovery already proven) | Chaos test D10 |
| **Panic Mode** always available, never needs a confirmation dialog | E2E: from any state → one action → paused + snapshot written |
| Dyslexia-friendly output option (spacing, no dense tables in cards, TTS-ready plain text field) | Card has a `plain_text` field with no markdown |
| Wins are visible but quiet | Celebration is a single line + XP chip, dismissible, off in quiet mode |

---

## 7. Gamification (honest, un-farmable)

- **Quests** = flow templates ("Ship one small feature", "Green the tests", "Write a handover"). Each has a definition of done that is *machine-checkable evidence*, not a self-report.
- **Quest Settler:** one small server-side function in core. Triggered by a run reaching `COMPLETED` with a sealed evidence bundle. Calls `broski-economy-mcp award_tokens` with a **stable `source_id = run_id:quest_id`** (mirrors the Course repo's `award_tokens` dedup rule). Agents and MCP clients have **no path** to award.
- **Caps:** per-day XP ceiling; zero XP for runs the Guardian BLOCKed; reduced XP when a human had to rescue a run (still positive — no shaming).
- **Agent levels** (BROskiPets/consciousness layer) are *cosmetic + routing preference only*. **Safety review never relaxes with level.** Trust is not an XP reward.
- **Streaks:** gentle, auto-freeze on missed days. No loss aversion.
- **Achievements (first batch):** First Squad Run · Zero-Retry Run · Handover Written · Panic Used Well (used Panic Mode and resumed same day) · Green on First Verify.
- **Open decision:** XP numbers/caps. Propose small defaults; Bro tunes.

---

## 8. Two-week roadmap

Rules for every day: **one deliverable, one proof, commit + push before "done"** (CLAUDE.md). Before any build/recreate: ≥1.5 GB available, `up -d --no-deps <svc>`, never `--force-recreate`; post-check core healthy, `RestartCount 0`. Controller runs live ops, never an unattended subagent (2026-08-24 incident rule).

### Day 0 — Prep (before Day 1)
- Review/merge PR #539 (2b authorize, base `feature/broski-recover-2a`).
- Decide scope guard: **squads are non-mutating in this plan.** The Governor `container.restart` grant stays an open, separate decision.
- Confirm lean-mode baseline: record available RAM, container count, unhealthy = 0.

### Week 1 — Foundations (read-only squad, end-to-end)

| Day | Deliverable | Proof |
|---|---|---|
| **1** | Baton + Calm Card Pydantic models, caps, formatter. Spec test file first. | Unit tests: caps, 1-next-action rule, `plain_text` has no markdown |
| **2** | `hypercode.crew` flow skeleton: `plan` node (core → `mission-director` `/v1/plan`) + approval gate with `plan_hash`. Add `idempotency_key` to operator start if missing. | Tests: gate needs exact hash; duplicate start returns same `task_id` |
| **3** | `agent_dispatch` node via `crew-orchestrator`; wire dispatch-seam card (c)/N13 **record-only** (normalise agent names to hyphenated once at boundary, test both key styles). | Tests + one dispatch to a *running* specialist; Shepherd verdict recorded |
| **4** | Verify + Guard nodes, evidence bundle (sha256 refs), slot gate (`throttle-agent` or static cap 3), on-demand wake via `agent-factory` for sleeping members. | Test: 4th concurrent dispatch waits, doesn't start; Shepherd down → BLOCK |
| **5** | MCP tools `hypercode_crew_start` / `hypercode_crew_status`; `scripts/prove-crew.py` live proof. **Week 1 gate.** | Live, no mocks: handle returned instantly · survives `docker restart hypercode-core` parked at a gate · cancel works · agent key can't approve (403) · RAM ≥ 1.2 GB throughout |

### Week 2 — Neurodivergent-first + gamification + hardening

| Day | Deliverable | Proof |
|---|---|---|
| **6** | Dashboard **Crew Board** panel (one next action, traffic-light status). Rebuild `dashboard` *and* `hypercode-core` after merge (N20 habit). | Real UI screenshot via Playwright; Calm Card matches API |
| **7** | Focus Guide: `hyper-split-agent` chunking in flow; **Focus Session / quiet mode**; **Panic Mode** (pause + `session-snapshot`). | E2E: Panic from every status → paused + snapshot row |
| **8** | **Quest Settler** + first 5 achievements; caps; idempotent `source_id`. | Tests: replay settle → no double award; BLOCKed run → 0 XP; agent key can't reach award |
| **9** | **Scribe**: handover + `WHATS_DONE` draft generated as a *proposal* (opened as draft PR, never direct write); Morning Card (W3). | Handover matches the repo's format; human gate before PR opens |
| **10** | Chaos + hardening, docs, handover. **Week 2 gate.** | Chaos: core restart mid-run · specialist down · Shepherd down (fail-closed) · duplicate start · cancel mid-dispatch · Governor kill-switch trips run. Then `NEXT_SESSION_HANDOVER_*.md`, `WHATS_DONE.md`, `STATUS.md` |

**Stop rules (any day):** available RAM < 1.2 GB, core unhealthy past 5×30 s retries, unexpected restart → stop, no optional services, write it down. A day slipping is fine; skipping its proof is not.

---

## 9. Explicitly NOT doing

- `mcp_tasks` table, MCP Celery adapter, transactional outbox (HyperFlow already covers it).
- Autonomous mutation / deploy by squads (blocked on Governor grant decision + monitoring being back).
- Restoring the obs stack just for this (RAM). Crew events go to the Governance Ledger; Prometheus counters are emitted anyway so they light up when obs returns.
- New MCP spec work (stateless core / Tasks extension). Keep the `mcp` pins as-is; revisit as its own task after Week 2.
- Tying agent safety to XP/level. Ever.

## 10. Risks

| Risk | Mitigation |
|---|---|
| RAM (N22) takes the box down mid-demo | Cap 3 awake; slot gate; stop rules; lean mode baseline |
| `throttle-agent` MemStream gap | Static cap fallback; don't build MemStream here |
| In-core asyncio runner loads `hypercode-core` under fan-out | Fan-out nodes execute in *agents*, core only orchestrates; Celery for CPU-heavy tool nodes |
| GitHub Actions billing lock (N14) → CI unverified | Local green is the gate; re-run `workflow_dispatch` lanes when unlocked; say "CI-unverified" in entries |
| Free LLM models return `content: null` / chain-of-thought | Reuse the proven `reasoning: {exclude: true}` + fallback chain from broski-coo |
| Scope creep from the fun parts (gamification) | Day 8 is the only gamification day; Week 1 gate must pass first |

## 11. Decisions needed from Bro

1. **XP defaults and daily cap** — accept proposed small numbers, or tune?
2. **Governor `container.restart` grant** (2b's open question) — separate spec, not blocking this plan.
3. **Off-laptop path** (N22 / "Brainstorm HyperCode OFF Your Laptop") — if RAM keeps biting, a Railway-hosted squad runner is the real fix. Worth a later session.
4. **Name** — "HyperCrew" is a placeholder. Pick one that feels like yours.
