# 🏁 Session Handover — 2026-08-20 (late night → 2026-08-21) · "The Fleet Actually Launched, Then Grew a Conscience"

> Continues directly from `NEXT_SESSION_HANDOVER_2026-08-20-evening.md` ("Verify,
> Don't Trust the Grep") — that session found item #0 (the 14/13-agent
> same-name-merge risk between `agents-full.yml` and `agents.yml`) and stopped
> there, on purpose, needing Bro's call before touching it. This session got that
> call, resolved item #0 for real, **launched the 25-agent fleet for the first
> time it has ever actually been composed up as one system**, fixed a real bug
> surfaced by the launch itself (`throttle-agent`'s missing Docker socket), then
> — at Bro's request — designed and shipped a brand-new safety-first agent,
> `fleet-controller`, Phase 0 of a much bigger planned architecture.

---

## ⚡ TL;DR

Four real pieces of work, each verified live, not just claimed:

1. **Item #0 resolved for real** (not just mitigated) — deleted 13 duplicate
   agent definitions from `agents-full.yml`, `agents.yml` stays canonical.
   Commit `8b474b8e`.
2. **The 25-agent fleet actually launched** — `docker compose up` for real,
   for the first time ever. Found + fixed 3 more bugs that only surface when
   containers try to start together, not while parsing YAML. Commit `83941a6f`.
3. **`throttle-agent`'s Docker socket fixed** — wired to an already-built proxy
   (`docker-socket-proxy-healer`) whose own comment said it was meant for
   exactly this, just never connected. Commit `5add0669`.
4. **`fleet-controller` Phase 0 built and smoke-tested against the real,
   live stack** — the first piece of a new mission-director architecture.
   Structurally incapable of executing anything; fails closed if Safety
   Shepherd is down. Commits `a85c4a84` (spec), `d6ec14b6` (code, auto-committed
   by the repo's own hook during an idle gap), `3692650c` (docs).

**Current state: 68 containers running, zero unhealthy.** Full fleet + Phase 0
fleet-controller both live and verified.

## ✅ What shipped this session

### 1. Item #0 — the agents-full.yml/agents.yml merge, resolved

Re-derived the actual overlap directly from each file's `services:` block
(the earlier "14" count included 2 spurious network names from a broader
sweep) — **13 real overlapping agent names**. Compared both files' actual
definitions per agent: `agents.yml`'s were the real, live, hardened ones
(volume-mounted code, HYPER-SILLs loadout, `security_opt`); `agents-full.yml`'s
copies were unused stubs, never composed up. **Decision: `agents.yml` stays
canonical for all 13 — deleted their duplicate blocks from `agents-full.yml`
for good.** It's now a clean 11-agent ghost-only overlay. Verified via
`docker compose config` with both files: zero collisions, the merged
`crew-orchestrator` confirmed to be the real hardened definition.

Found and fixed a second bug in the same pass: `agents.yml`'s
`project-strategist` pointed at a directory whose Dockerfile had been deleted
by an earlier business-agent fix — repointed to the real
`agents/08-project-strategist`, which was itself missing `base_agent.py`
entirely (fixed, verified via standalone `docker run` + `/health` 200).

### 2. The fleet actually launched

Ran `docker compose --profile agents --profile hyper -f docker-compose.yml
-f docker-compose.agents-full.yml up -d` for real. Hit and fixed 3 more bugs
that **no amount of `docker compose config` validation could have caught**,
because they only matter once containers try to start together:

- `agent-x`/`hyper-architect` needed the same `.dockerignore` carve-out
  `hyper-observer`/`hyper-worker` needed earlier the same night.
- `agents-full.yml`'s `test-agent` had too narrow a build context to reach
  the sibling `agents/shared/agent_utils.py` it directly imports.
- **The big one**: all 11 of `agents-full.yml`'s own ghost agents referenced
  networks `app-net`/`agent-net` that were never created *anywhere* in the
  real stack — only `agents-net`/`data-net` actually exist. Every one of
  those 11 could build a perfectly good image but could never start a
  container. Fixed via one `replace_all` across all 11 blocks.

Also hit mid-launch: one transient `hypercode-core` restart under the heavy
concurrent build/startup load (confirmed not OOM, just a blip) cascaded a
batch of "dependency failed to start" errors — re-ran `up -d` once it
stabilized. `project-strategist` came up crash-looping on a **stale cached
image** from before the item #0 context repoint — `up -d` doesn't rebuild
automatically on a changed `build.context`, needed an explicit
`docker compose build project-strategist` first.

**Verified, not claimed**: polled every previously-blocked agent until none
reported `health: starting` — all 16 came back healthy. Swept the entire box:
zero unhealthy containers across all 67 running (at that point).

### 3. throttle-agent's Docker socket

Found `docker-compose.agents.yml` already runs a dedicated
`docker-socket-proxy-healer` service whose own comment literally says
**"ONLY for healer + throttle-agent"** — the infrastructure existed,
`throttle-agent` was just never wired to it. Added
`DOCKER_HOST=tcp://docker-socket-proxy-healer:2375` + a `depends_on`,
mirroring `healer-agent`'s exact pattern. Never mounted `/var/run/docker.sock`
directly. Verified live: `curl /health` → `"docker":"ok"` (was `"error"`
before).

Found a second, separate issue while in there: `throttle-agent` also logs
`MemStream unreachable` — confirmed this is a real, planned dependency (also
depended on by `broski-bot`, at a *different* port/env-var convention), never
actually built anywhere. Logged as `NEXT_TASKS.md` item #2b, deliberately not
fixed — needs a decision (build it, or strip the polling code), not a wiring
fix.

### 4. fleet-controller — Phase 0 of a new architecture

Bro asked to brainstorm the most ambitious version of a 5-idea infra roadmap
(mission-director + HyperBrain-style skill routing). Because self-triggered
missions + real Docker control + LLM-driven decisions add up to a system that
can act on real infrastructure on its own initiative — close to what the
roadmap doc's own header explicitly disclaimed ("we wont AGI BROski") — went
through a full brainstorming pass (multiple `AskUserQuestion` rounds, three
detailed design docs Bro shared, each verified against the live codebase, not
taken on faith) and converged on **Approach C**: hard separation between a
planner that can think but never act, and a deterministic controller that can
act but never interprets natural language.

**Governing rule: no component may both interpret LLM output and possess
infrastructure mutation authority.**

Spec written (`docs/superpowers/specs/2026-08-20-fleet-controller-phase0-design.md`)
covering only Phase 0: prove the containment boundary exists before any
capability is added. Via `/plan` mode: an Explore pass confirmed the real test
pattern to mirror (`agents/crew-orchestrator/tests/test_safety_gate.py` — the
only real fail-closed-testing precedent in this repo) and a free port (8094);
a Plan pass caught a real conflict (CLAUDE.md's Sacred Rule says every agent
depends on `crew-orchestrator`'s health — `fleet-controller` deliberately
doesn't, confirmed explicitly with Bro before building).

Built `agents/fleet-controller/` — no Docker socket, no `DOCKER_HOST`, no
crew-orchestrator credential, no LLM client. 26 unit tests, all passing.
**Then actually launched it into the live stack and proved all three
API-contract scenarios against real Safety Shepherd**, not mocks:

1. Valid plan, Shepherd up → real `ESCALATE` from Shepherd's *unmodified*
   policy engine (category `"docker"` is already in its `DANGEROUS` set —
   zero Shepherd-side changes needed).
2. `docker stop safety-shepherd`, same plan → `BLOCK`, fail-closed.
3. Denied profile (`"prod"`) → `422`, confirmed via Shepherd's own container
   logs that it never received the call at all.

`execution.performed` was `false` in every case — there's no code path
anywhere in the service capable of setting it `true`.

Provisioned its Governance Ledger key carefully: the seed script regenerates
*all* 14 existing agents' keys in one batch (would have silently invalidated
every other live agent's ledger auth against the running DB) — scoped it down
to a single-row `INSERT ... ON CONFLICT` for just `fleet-controller` instead.

## 🧭 What's still open (for next session)

| # | Item | Where |
|---|---|---|
| 0a | `agents/08-project-strategist/agent.py`'s `plan()`/`delegate_tasks()` are dead code (never wired to `process_task`, plus missing `await`s) — container works fine via the generic fallback, real specialist-delegation logic doesn't run | `docs/NEXT_TASKS.md` item #0a |
| 2b | `throttle-agent`'s `MemStream` dependency was never built anywhere — real, planned (broski-bot depends on the same concept too), needs Bro's call | `docs/NEXT_TASKS.md` item #2b |
| — | **Mission-director** (the actual LLM planner) — nothing built yet. Phase 0's only job was proving the containment boundary; it's proven. | Phase 1+, not started |
| — | Capability tokens, human-approval UI, any live execution (`compose_profile.start`, crew dispatch) | Phase 2–5, not started, see the spec's phased build order |
| 5 | `docs/STATUS.md` + `AGENT-START.md`'s full per-agent port tables are still stale (wrong ports, "building" instead of "live") — both got banner updates tonight but not full rewrites, to avoid re-creating the exact duplication problem that caused several of tonight's bugs | `docs/NEXT_TASKS.md` item #5 |
| 6–8 | `ghost-agents-build.yml`'s broken build-matrix paths + broken port-collision regex; `health-check.yml`'s pre-existing port-parser bug (`str(p).split(':')[0].split('127.0.0.1:')[-1]` never extracts a real port) | `docs/NEXT_TASKS.md` items #6–#8, all pre-existing, untouched |

## 🔑 Key facts (don't re-derive)

| Thing | Value |
|---|---|
| Full-fleet launch command | `docker compose --profile agents --profile hyper -f docker-compose.yml -f docker-compose.agents-full.yml up -d` — proven, not just documented |
| `fleet-controller` launch | Same command **+ `--profile fleet`** — deliberately excluded from the standard command |
| Total containers right now | 68, zero unhealthy |
| `fleet-controller` port | `:8094` (container :8080) |
| Safety Shepherd auth quirk | `agents-full.yml` agents default `API_KEY=dev`, but `safety-shepherd` expects `HYPERCODE_API_KEY` with fallback `dev-master-key` — export `API_KEY=dev-master-key` before testing anything that calls Shepherd, or every `/evaluate` will 401 |
| `agent_api_keys` table | `fleet-controller` provisioned; 16 pre-existing rows deliberately untouched (don't run `scripts/seed_agent_api_keys.py`'s output against the live DB wholesale — it's a full-batch regenerate) |
| Spec for the new architecture | `docs/superpowers/specs/2026-08-20-fleet-controller-phase0-design.md` |
| This session's commits | `8b474b8e`, `83941a6f`, `5add0669`, `a85c4a84`, `d6ec14b6` (auto-committed by the repo's own hook), `3692650c` — all pushed, evo harness 26/26 throughout |

---

> 🐶♾️ *"Tonight the fleet went from 'compose file that's never been composed up' to
> 'live, 68 containers, zero unhealthy' — and then, because Bro asked for the most
> ambitious version of the next idea, gained its first piece of a system explicitly
> designed so the ambitious part can never touch anything real without a human
> saying so. No component may both interpret LLM output and possess infrastructure
> mutation authority. That's the whole thesis of what gets built next."*
