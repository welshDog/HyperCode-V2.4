# 📋 NEXT_SESSION_HANDOVER — 2026-10-02 (HyperCrew, Days 1–10)

> Bro, this handover is the truth. Everything below is **built, tested in a sandbox, committed and pushed** to
> `claude/focused-darwin-ljrs8k` ([PR #547](https://github.com/welshDog/HyperCode-V2.4/pull/547), draft).
> **Nothing is deployed and nothing has run on Docker** — the sandbox had no Docker. Your first job is the
> runbook: `docs/HYPERCREW_DOCKER_RUNBOOK.md`. Live status beats this file; `WHATS_DONE.md` beats everything.

---

## 🟢 LIVE STATE RIGHT NOW

- **Deployed:** nothing from this work. `hypercode-core` and `dashboard` still run the old builds.
- **Code:** all on the branch above. Draft PR open, CI = same **4 failures that already exist on `main`**
  (`test_agent_pulse` ×3, `test_core_rag` ×1) and nothing else.
- **Needs applying on deploy:** Alembic migration `023` (table `quest_settlements`). Additive; core applies it on boot.

## 🧱 WHAT HYPERCREW IS (one paragraph)

`hypercode.crew` is a HyperFlow flow (v5) in core: `plan → [you approve, plan hash] → seal → build → verify →
guard → settle → scribe → [you approve, draft hash] → publish`. Agents (`coder-agent`, `qa-engineer`) only
**propose text**. The Guardian decides ALLOW/BLOCK from deterministic checks. Everything is replayable after a
restart. Everything a person sees is a **Calm Card** (≤5 lines, exactly one next action, no shaming).

## ✅ WHAT WAS BUILT (by day)

| Day | What | Where |
|---|---|---|
| 1 | Baton + Calm Card models | `backend/app/crew/baton.py`, `calm_card.py` |
| 2 | Plan gate with `plan_hash`, seal, `idempotency_key` on operator start | `crew/plan.py`, `crew/tools.py`, `operator_tasks.py` |
| 3 | `agent_dispatch` node (strict, slot-gated), verify + guard, evidence bundle, RAM slot gate (cap 3, floor 1.2 GB), redaction | `crew/dispatch.py`, `slots.py`, `evidence.py`, `redaction.py` |
| AG-UI edge | `GET /operator/tasks/{id}/events` (replay-exact) + Calm Card endpoint | `crew/agui.py`, `crew/cards.py` |
| 4 | Calm Mode + Sensory Settings (`/sensory`, presets, Calm default) | `agents/dashboard/lib/sensory`, `components/sensory` |
| 5 | MCP tools `hypercode_crew_start/status`; proofs | `services/hypercode-mcp-server/server.py`, `scripts/prove-crew*.py` |
| 6 | **Panic** (durable pause, one click, no dialog) + **Focus session** (quiet mode) | `runs.py`, `hyperflow_runner.py`, `components/crew/PanicControl.tsx`, `lib/focus` |
| 8 | **Quest Settler**: 20 XP (10 if retried), 100/day cap, UNIQUE `run_id:quest`, 5 achievements | `crew/quests.py`, migration `023` |
| 9 | **Scribe** (handover as a proposal, hash-gated), docs-only **draft-PR** opener, **Morning Card** | `crew/scribe.py`, `github_pr.py`, `morning.py` |
| 10 | **Chaos + hardening** (below) | `crew/killswitch.py`, `tests/test_crew_chaos.py` |

(Day 7 in the original plan = Focus/Panic, built as Day 6. `hyper-split-agent` chunking is **deferred**.)

## 🛡️ DAY 10 — WHAT CHAOS FOUND AND FIXED

| Scenario | Result |
|---|---|
| **Safety Shepherd down** | **REAL GAP FOUND:** the runner failed **open** (it carried on if Shepherd was unreachable), but the design says fail closed. **Fixed:** crew `build`, `verify`, `publish` carry `safety_unreachable: block` → blocked, with a plain reason. Applies in `monitor` mode too; `off` still skips. |
| **Kill-switch trips a run** | **REAL GAP FOUND:** nothing in core looked at it. **Fixed (opt-in):** `CREW_KILL_FILE` sentinel checked before every step; same semantics as the Governor's file. Unset = off. Core does not read the Governor's Redis flag. |
| Specialist dies mid-run / junk replies | Already safe. Proved end to end: run fails, no guard, no XP, no PR, slot handed back. |
| Duplicate + 8 concurrent starts | One run. Different args with the same key → 409. |
| Cancel mid-dispatch | In-flight call cancelled, verify never starts, slot released, approvals refused after. |
| Core restart at the handover gate / decision made while core is down | Same draft re-parks; decision honoured; published once; paid once. |
| Burst of 6 runs vs 3-slot cap | Never more than 3 agents awake; all 6 finish; 6 settlements, none doubled. |

## ✅ PROOF (what was actually run)

| Proof | Result |
|---|---|
| Backend `pytest` | **1091 pass**, 4 fail (the 4 pre-existing). `tests/test_crew_chaos.py` = 25 stable over repeat runs |
| Dashboard | 251 tests pass, `tsc` clean, eslint 0 errors, `next build` OK |
| `scripts/prove-crew-local.py` | **ALL PASS** — real processes, real SIGTERM restart of core, real MCP client, Panic, Scribe gate hash rules, no-token publish, achievements, ledger row, Morning Card, **Shepherd-down and kill-switch on a live core process** |
| `mypy app/crew` | clean except 2 old errors in `db/session.py` |
| **`scripts/prove-crew.py` (Docker)** | ❌ **NOT RUN** |
| **Real GitHub** | ❌ **NEVER TOUCHED** (publisher tested only against a fake) |

## ⚠️ NOT DONE / NOT PROVEN (be honest about these)

- **No Docker run.** Rebuild of `hypercode-core` + `dashboard`, migration `023`, `prove-crew.py` — all still to do.
- **Safety Shepherd's real answer** to a crew `agent_dispatch` node is unverified (ALLOW? ESCALATE?). With Shepherd
  down the crew now stops by design; make sure `safety-shepherd` is up before you judge a failed run.
- **Draft-PR publisher never ran against real GitHub.** No token is configured anywhere; nothing is wired in compose.
- **Kill-switch is not wired in compose** (needs the `/governance` mount + `CREW_KILL_FILE`).
- **Dashboard can't approve** a plan or a handover yet (still API/CLI). Panic/resume works in the UI.
- Morning Card does **not** call `broski-coo` / `session-snapshot` (contract unverified; useful without them).
- `hyper-split-agent` "Make it smaller?" chunking deferred (needs an LLM agent). Streaks not built.
- A replayed `publish` after a crash writes a second Governance Ledger row (an attempt log). PR + XP are idempotent.
- **Your decisions D1–D12 are still open.** XP numbers are small defaults (D1) in `backend/app/crew/quests.py`.

## 🧠 GOTCHAS FOR THE NEXT SESSION

- **A crew run is no longer "completed" until the handover gate is answered** (approve with the *draft's own*
  hash, or skip). Anything waiting for `completed` after the guard will wait at `approve_scribe`.
- The handover gate's `plan_hash` field is the hash of the **draft** (reused API field). The plan's hash is refused.
- Core's default `SAFETY_SHEPHERD_MODE=monitor` — crew nodes still fail closed on an unreachable Shepherd.
- `WHATS_DONE.md` is edited by parallel sessions: the Scribe writes **new files** (`docs/crew-proposals/…`), never it.
- Sandbox notes: venv at `/tmp/claude-0/venv`; run backend tests with
  `cd backend && PYTHONPATH=.:.. python -m pytest … -p no:cacheprovider -o addopts=""`. `pkill -f` kills your own
  shell; use `fuser -k <port>/tcp`.

## 📦 COMMITS (on the branch)

| SHA | What |
|---|---|
| `1469de3` | Day 1 — Baton + Calm Card |
| `c3ee0ed` | Day 2 — plan gate + idempotency key |
| `4c3adcf` | Day 3 — dispatch, verify/guard, evidence, slot gate |
| `c10c11f`, `5ce21bc` | AG-UI events + dashboard Calm Card panel |
| `096207e` | Day 4 — Calm Mode + Sensory Settings |
| `8ffba7f` | Day 5 — MCP tools + proofs |
| `301ceee` | Day 6 — Panic + Focus |
| `00f090f` | Day 8 — Quest Settler |
| `c500c6c` | Day 9 — Scribe + Morning Card |
| (this commit) | Day 10 — chaos + hardening + runbook + this handover |
| plus small CodeQL tidy-ups | e.g. `7fa915b`, `60629c5`, `c0b350b` |

Open CodeQL alerts on the PR: three "file data in outbound request" on the dashboard proxy routes (Panic, Panic
resume, Morning) are **false positives** (a service JWT from a Docker secret → a fixed core URL). Dismiss them.

## ▶️ NEXT TASK (one sentence)

On your machine, run `docs/HYPERCREW_DOCKER_RUNBOOK.md` steps 0–4 (rebuild core + dashboard, check migration `023`,
confirm Safety Shepherd is up, run `prove-crew.py` phases 0–2) and paste the output back.

---

> 🐶♾️ Built by @welshDog · Llanelli, Wales
> *"Stop apologising for your brain. Start building."*
