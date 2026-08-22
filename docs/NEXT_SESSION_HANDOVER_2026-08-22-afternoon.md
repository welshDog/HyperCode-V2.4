# 🏁 Session Handover — 2026-08-22 (afternoon) · "A Safety Fix, a New Observer, and a Preset That Lied About Its Own Guarantees"

> Continues directly from `docs/NEXT_SESSION_HANDOVER_2026-08-21-late-night.md`
> ("Truth Registry → Mission Director → Mission Evaluator, All Live"), which
> ended with `review_mission`'s BLOCK-approval gap as the top open item —
> "known, deliberately not fixed yet... Phase 3 territory." This session
> closed it, then built a new agent whose entire design was shaped by two
> live-caught failures: an AI hallucinating specifics, and an OpenRouter
> dashboard feature silently not enforcing the safety net it claimed to.

---

## ⚡ TL;DR

1. **`review_mission` BLOCK-approval gap closed** — the exact item last
   session's handover flagged as open. `BLOCK` now hard-rejects approval
   (`409`), `ESCALATE` requires an explicit `escalation_reason` (`422`
   without one), audited in the Governance Ledger. 13/13 tests pass.
   Commit `378b336d`.
2. **`broski-coo` v1 built and shipped** — a new, strictly read-only
   COO/observer agent (`agents/broski-coo/`, `:8025`). `POST /brief`
   turns real fleet health + doc excerpts into a plain-English status
   brief, checkable against raw numbers returned alongside the prose.
   Commits `bd8cde99`, `89a092ed`.
3. **OpenRouter preset tried, live-tested, reverted** — routed the LLM
   fallback chain's free tier through Lyndz's dashboard-configured
   `free-router` preset (meant to enforce cost cap + training-data deny
   server-side). Live testing proved the preset mechanism doesn't
   reliably enforce its own policy — an explicit `model` field silently
   overrides both model selection AND the safety net, proven by
   successfully routing to a paid model through a preset configured to
   deny exactly that. Reverted; replaced with a client-side
   `_DENIED_PROVIDERS` filter that can't be bypassed the same way.
   Commits `9f50170f` (tried) → `5a84053a` (reverted) → `854f0f8d`
   (denylist + docs).
4. **Two real reasoning-model bugs caught by live testing, not mocks**:
   `stealth/ox-alpha` can return `content: null` (fixed, rotates to next
   model); `nemotron-3.5-lightning` can return non-null content that's
   entirely raw chain-of-thought, cut off mid-sentence (fixed,
   `reasoning: {exclude: true}`). Commits `89a092ed`, `d7398ff9`.
5. **Two `.env`-location mistakes, same class, twice** — `OPENROUTER_API_KEY`
   then `HYPERCODE_API_KEY` were both dropped into the parent
   `HperCore/.env` instead of `HyperCode-V2.4/.env`, the one Docker Compose
   actually reads for this repo. Both caught and fixed live.

**Current state**: 69 containers (68 + `broski-coo`), zero unhealthy.
`broski-coo`'s full pipeline proven end-to-end through the real authed
`/brief` endpoint — first genuinely useful output, not just a diagnostic.
`main` is pushed and clean.

## ✅ What shipped this session

### 1. `review_mission` BLOCK-approval fix

`backend/app/api/v1/endpoints/missions.py` previously wrote whatever
decision a human sent straight to `approved`/`rejected`, never reading
`plan_response.safety.decision` — confirmed in code, not just docs, before
fixing (`review_mission:123-153` had zero reference to `plan_response`).
Now: `BLOCK` → `409`, no override path exists anywhere. `ESCALATE` → `422`
unless the reviewer supplies a non-empty `escalation_reason`, which then
gets written into the Governance Ledger payload — a deliberate, audited
override, never a silent downgrade to `ALLOW`. `ALLOW`/missing verdict and
`reject` are unchanged. 4 new tests, 9 pre-existing untouched, 13/13 pass.

### 2. `broski-coo` v1 — build, key-wiring, and two rounds of live-bug-fixing

Full design reasoning in `agents/broski-coo/HYPER-AGENT-BIBLE.md` (§6 has
the complete gotcha writeup) and `WHATS_DONE.md`'s 2026-08-22 entry — the
short version:

- **Scope**: HyperCode-V2.4 only, strictly read-only, no Docker socket, no
  `DOCKER_HOST`, never calls `agent-registry`'s adjacent unauthenticated
  `POST /agents/{name}/restart`/`/reset` mutation routes. Deliberately not
  supervisory — this session had *just* found and fixed the exact kind of
  gap (`review_mission`, above) that makes handing a new agent write power
  premature.
- **Reads**: `agent-registry`'s already-live `GET /agents/status` (no new
  infra needed), plus `WHATS_DONE.md`/`docs/NEXT_TASKS.md`/newest
  `NEXT_SESSION_HANDOVER_*.md` via a read-only repo bind mount, mirroring
  `mission-director`'s own `truth_snapshot.py` precedent.
- **Anti-hallucination design, directly motivated**: two separate messages
  pasted into this conversation from a different AI assistant contained
  fabricated specifics — a "free OpenRouter models" table where 7 of 8
  entries were wrong when checked live, and a claimed "~30 containers" +
  a nonexistent `NEXT_SESSION_HANDOVER_LATEST.md` file (real count: 68
  containers; no such file exists, handovers are dated). Every `/brief`
  response tags each source `ok`/`degraded`/`unavailable` and returns raw
  numbers alongside the LLM's prose, so it's checkable, not just trusted.
- **Key-wiring gotcha, twice**: both `OPENROUTER_API_KEY` and
  `HYPERCODE_API_KEY` were initially set in the wrong `.env` file (parent
  `HperCore/.env`, not `HyperCode-V2.4/.env`) — silently had zero effect
  until copied across. See N6 in `docs/NEXT_TASKS.md`.
- **Bug 1, live-caught**: `stealth/ox-alpha` (a reasoning-capable free
  model) returned `200 OK` with `message.content == null`,
  `finish_reason: "length"` — spent its token budget on internal
  reasoning before emitting output. Fixed: null/empty content now treated
  as a failed attempt, rotates to the next discovered free model.
- **Bug 2, live-caught, one round later**: `nvidia/nemotron-3.5-lightning:free`
  returned non-null content that was entirely raw chain-of-thought, cut
  off mid-sentence — same root cause, didn't trip the null check since
  content wasn't null. Fixed via OpenRouter's own documented
  `reasoning: {exclude: true}` parameter (verified against
  `openrouter.ai/docs/use-cases/reasoning-tokens` before implementing, not
  assumed) — keeps reasoning internal to the model, full `max_tokens`
  budget goes to the actual answer.
- **Fully proven live, first time, this session**: real auth
  (`HYPERCODE_API_KEY`), real `agent-registry` numbers matching a direct
  `curl` side-by-side, real doc reads (correctly picked
  `NEXT_SESSION_HANDOVER_2026-08-21-late-night.md` as newest), real
  OpenRouter response — a genuinely well-written brief that correctly
  reported a source discrepancy (42 tracked agents vs. a handover's "68
  containers") *without inventing a reconciliation*, exactly the behavior
  the design set out to get.

### 3. The OpenRouter preset detour — tried, disproven live, reverted

Lyndz built a dashboard preset (`free-router`) intended to enforce
`data_collection: deny` (blocking Poolside/LiquidAI, confirmed to train on
free-tier inputs/outputs) and `max_price: 0` server-side. Switched
`broski-coo`'s OpenRouter tier to route through it (`model:
"@preset/free-router"`) — simpler code, and in principle a stronger
guarantee than a client-side check.

**Live testing found it doesn't work as advertised**, in three stages:

1. Bare `model: "@preset/<slug>"` → consistent `500 Internal Server Error`,
   reproducible regardless of the preset's model composition (tested
   before *and* after Lyndz edited the preset's model list — same error
   both times, ruling out "bad model choice" as the cause).
2. Combined syntax `model: "<real>@preset/<slug>"` → `404`, a data-policy
   rejection (the policy engine was at least active here).
3. Dedicated-field syntax `model: "<real>", preset: "<slug>"` → `200`, but
   an explicit `model` field **silently overrides both the preset's model
   selection AND its cost/training-data policy** — proven by deliberately
   requesting a paid model (`anthropic/claude-3-haiku`) against the
   free-only preset and watching it succeed with a real non-zero charge
   (`cost: 8.75e-06`).

None of the three syntaxes deliver "OpenRouter enforces this server-side,
unconditionally" — the one thing the whole switch was for. Reverted
(`git revert 9f50170f` → `5a84053a`), replaced with a client-side
`_DENIED_PROVIDERS = {"poolside", "liquid"}` filter applied at model
discovery time — a hard, code-level check that can't be silently bypassed
by a request-time field, unlike the preset. Documented as a "don't
re-attempt blind" gotcha in `agents/broski-coo/HYPER-AGENT-BIBLE.md` §6,
since presets *might* work for other use cases — this repo's conclusion is
narrowly that they don't currently give a reliable *unbypassable*
guarantee, which is the specific property this use case needed.

## 🧭 What's still open (for next session)

| # | Item | Where |
|---|---|---|
| 1 | **`ANTHROPIC_API_KEY` in `.env` is still invalid** — re-confirmed live `401` today, unchanged from last session (same key, checked prefix/suffix). Blocks `mission-director`'s Anthropic tier AND now `broski-coo`'s best-quality tier (both fall through to lower tiers). | [Issue #433](https://github.com/welshDog/HyperCode-V2.4/issues/433) |
| 2 | **Rotate `DATABASE_URL` + `DASHBOARD_SERVICE_JWT`** — unchanged from last session, still precautionary, not urgent. | [Issue #434](https://github.com/welshDog/HyperCode-V2.4/issues/434) |
| 3 | **Sweep for other agents silently 503ing** — `HYPERCODE_API_KEY`/`AGENT_API_KEY` were completely absent from `.env` fleet-wide until today. Every agent using the standard `_agent_auth_middleware` pattern (`base_agent.py`, `super-hyper-broski-agent`, now `broski-coo`) was returning `503` on every non-`/health` route. Now set and confirmed working for `broski-coo` — not yet checked whether this also silently unblocks `super-hyper-broski-agent` or others. | `docs/NEXT_TASKS.md` N7 |
| 4 | **`docs/STATUS.md`'s fleet-ports table is still stale** — deliberately not rewritten again this session (same reasoning as the last two: a rushed rewrite risks re-creating duplication bugs). Banner + top metrics table updated instead. | `docs/NEXT_TASKS.md` N5, unchanged |
| 5 | **Pre-existing `broski-bot` duplicate-`security_opt` YAML merge error** — unchanged from last session, still blocks the standard full multi-file compose build for any service. | [Issue #435](https://github.com/welshDog/HyperCode-V2.4/issues/435) |
| 6 | **`OPENROUTER_PRESET` env var reference is fully gone from code** (removed by the revert) but the `.env` files still have an `OPENROUTER_PRESET=free-router` line from the detour — harmless (nothing reads it), Lyndz's call whether to clean it up. | `.env` (both copies) |
| — | **`broski-coo`'s next natural step, if wanted**: mission-evaluator integration is explicitly deferred (needs an agent-scoped read credential — "no agent identity can authenticate as a user" is this repo's standing invariant, not worked around). Also unbuilt: any scheduling/cron loop or Discord auto-posting — v1 is on-demand only, by design. | `agents/broski-coo/HYPER-AGENT-BIBLE.md` §4/§6 |

## 🔑 Key facts (don't re-derive)

| Thing | Value |
|---|---|
| `broski-coo` port | `:8025` (confirmed free via a live grep of every `docker-compose*.yml` before assigning) |
| `broski-coo` launch | `docker compose -f docker-compose.yml -f docker-compose.registry.yml --profile agents up -d broski-coo` — same file as `agent-registry`/`agent-factory`/`hyper-auto-assistant`, NOT `agents-full.yml` |
| `broski-coo` is NOT `super-hyper-broski-agent` | The latter (`:8015`) is a pre-existing, unrelated novelty vibe/party-mode service wired into `hyper-auto-assistant`'s routing — untouched this session. Two different agents, don't conflate. |
| `.env` location | `HyperCode-V2.4/.env` is what Docker Compose reads for this repo — NOT `HperCore/.env` (the parent workspace file). Bit this session twice. |
| OpenRouter free model catalog | Confirmed volatile within a single session: 7 free models at one live check, 21 a few hours later same day. Never hardcode a model list — `broski-coo` discovers at call time. |
| LLM fallback chain (broski-coo) | Anthropic (if `ANTHROPIC_API_KEY` set) → OpenRouter free-tier, denylist-filtered (if `OPENROUTER_API_KEY` set) → local Ollama (true floor, always attempted) → final degrade string. Never raises past `_call_llm()`. |
| How to test `/brief` live | `KEY=$(grep "^HYPERCODE_API_KEY=" .env \| cut -d= -f2-); curl -s -X POST -H "x-agent-key: $KEY" http://127.0.0.1:8025/brief` |
| How to test the LLM chain directly (bypasses auth) | `docker exec broski-coo python -c "import asyncio, main; print(asyncio.run(main._call_llm('sys','user',max_tokens=900)))"` — used repeatedly this session to isolate LLM-layer bugs from auth-layer state |
| Total containers right now | 69 (68 + `broski-coo`), zero unhealthy |
| This session's commits (chronological) | `378b336d` (review_mission fix) → `bd8cde99` (broski-coo v1) → `89a092ed` (null-content fix) → `9f50170f` (preset routing, tried) → `5a84053a` (preset reverted) → `854f0f8d` (denylist + docs) → `d7398ff9` (reasoning-exclusion fix) — all pushed, evo harness 26/26 throughout |

---

> 🐶♾️ *"The preset was supposed to be the safer, simpler choice — let the
> platform enforce the policy instead of us. It took three different
> request syntaxes and a deliberately-mismatched test call to find out it
> doesn't, and the one that looked like it worked (`200`, real content)
> was the one quietly letting a paid model through a free-only gate. The
> client-side check we replaced it with is less elegant and impossible to
> bypass with a stray field. Verify the guarantee, not just the response
> code — that's the whole session in one sentence, really."*
