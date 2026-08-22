# 🧭 HYPER-AGENT-BIBLE — BROski COO

> Role-specific Bible. Read the shared ecosystem Bible
> (`agents/crew-orchestrator/HYPER-AGENT-BIBLE.md`) first. Orchestrator agent
> key: **`broski_coo`** (observer role). Last updated: 2026-08-22

---

## 1. 🎯 Role

BROski COO is a **read-only observer** over the HyperCode-V2.4 fleet only (not
the wider ecosystem). Its one job: `POST /brief` — assemble live fleet
status plus recent doc excerpts into a plain-English brief for Lyndz. It is
**not** the same agent as `super-hyper-broski-agent` (:8015, an unrelated
novelty vibe/party-mode service) — do not confuse the two, do not merge them.

LLM tier: whatever's configured — Anthropic if `ANTHROPIC_API_KEY` is set,
else OpenRouter's currently-free tier (runtime-discovered), else local Ollama.

## 2. 🔴 Sacred Rules (role-specific)

- **Never call `agent-registry`'s mutation routes** — `POST /agents/{name}/restart`,
  `POST /agents/{name}/reset` live unauthenticated on the same service this
  agent reads from (`GET /agents/status`). This agent's code must never call
  them. No exceptions, no "just this once."
- **Never state a fact not present in the data fetched that request.** No
  invented numbers, container names, file names, or statuses. This is the
  entire reason this agent exists — see §6.
- **No Docker socket, no `DOCKER_HOST`, ever.** Zero infrastructure-mutation
  capability, by construction, not by convention.
- If a source (fleet status, a doc file) is unavailable or looks stale/empty,
  say so plainly in the brief. Never paper over a missing source.
- v1 scope is HyperCode-V2.4 only — do not add reads from other repos in the
  ecosystem without a scope decision first.

## 3. 🧰 Capabilities Manifest

| Field | Value |
|---|---|
| Tools | `http_read` (`agent-registry` `/agents/status` only), `file_read` (repo bind-mount, read-only) |
| Explicitly absent | `file_write`, `docker`, any mutation HTTP call |
| File paths | `/app/repo/**` (read-only bind mount of the HyperCode-V2.4 repo root) |
| Ports touched | `agent-registry:8077` (read-only call) |
| Networks | `agents-net` only — no `data-net`, no Redis, no DB |
| Own port | `:8025` |

## 4. 🌳 Decision Tree

- **DO:** fetch `agent-registry`'s `/agents/status`, read `WHATS_DONE.md` /
  `docs/NEXT_TASKS.md` / the newest dated `NEXT_SESSION_HANDOVER_*.md`,
  produce a brief that's checkable against the raw numbers it returns
  alongside the prose.
- **DON'T:** restart/reset any agent, write any file, hold any DB/Redis
  credential, mint or hold a human JWT to reach auth-gated endpoints
  (mission-evaluator's `/summary` is out of scope for this exact reason —
  see §6), invent a fact not present in fetched data.
- **ESCALATE →** none in v1 — this agent has no write capability to escalate
  from. A future Supervisor-tier BROski (approve/restart/route) is explicitly
  a separate, later, more carefully-gated build — not this agent.

## 5. 🕸️ HyperFlow Integration

Not wired into HyperFlow in v1 — called on-demand via `POST /brief`, not as a
flow node. No cron/scheduling loop, no Discord auto-posting.

## 6. 📜 Governance

**Why this agent is read-only-first, not supervisory**: this session found
and fixed a real gap where a human could approve a mission Safety Shepherd
had already said `BLOCK` on (`review_mission`, fixed, commit `378b336d`), and
confirmed `ANTHROPIC_API_KEY` was dead. Giving a new agent write/approval
power over the fleet before those areas were proven solid would have
extended an unproven trust boundary. Read-only observation first is a
deliberate, named choice, not a placeholder for "not built yet."

**Why the anti-hallucination rules in `_SYSTEM_PROMPT` exist**: during this
agent's own design session, two separate messages pasted from a different AI
assistant contained specific, plausible-sounding, but fabricated claims — a
"currently free OpenRouter models" table where 7 of 8 entries didn't match
the live API, and a claimed "~30 containers" plus a nonexistent
`NEXT_SESSION_HANDOVER_LATEST.md` file (real count: 68 containers; no such
file exists). This agent's entire reason to exist is to not repeat that —
every brief is built from data fetched in that same request, tagged
`ok`/`degraded`/`unavailable` per source, with the raw numbers returned
alongside the LLM's prose so it's checkable, never just trusted.

**Named v1 gaps, not silently worked around**:
- Mission-evaluator's `/mission-evaluations/summary` requires a real human
  JWT (`deps.get_current_active_user`). This repo's established invariant is
  "no agent identity can authenticate as a user" — not worked around here.
  Needs a proper agent-scoped read credential design before this agent can
  include it.
- `agent-registry`'s own mutation routes being unauthenticated is
  pre-existing and unrelated to this agent — not this agent's job to fix,
  just a boundary it must never cross.
- OpenRouter free-model selection is dynamic, discovered at call time
  (`GET /models`, filter `pricing.prompt == "0"`), confirmed volatile (7
  models free at design time, 21 a few hours later same day). Poolside and
  LiquidAI are excluded by provider-id prefix (`_DENIED_PROVIDERS` in
  `main.py`) — confirmed via OpenRouter's own models page to train on
  free-tier inputs/outputs. `provider_used` in every `/brief` response names
  the actual model used.
- **Gotcha, don't re-attempt blind**: an OpenRouter dashboard preset
  (`@preset/<slug>`, with `data_collection: deny` + `max_price: 0` as an
  intended server-side safety net) was tried as a replacement for the
  client-side denylist above and reverted after live testing. Findings:
  the bare `model: "@preset/<slug>"` syntax returned a consistent `500`
  regardless of the preset's model composition; the `model` + `preset`
  dedicated-field syntax returned `200` but an explicit `model` field
  silently overrode BOTH the preset's model selection AND its cost/
  training-data policy (proven by successfully routing to a paid model —
  `anthropic/claude-3-haiku`, real non-zero cost charged — through a
  preset configured to deny exactly that). Presets may work correctly for
  other use cases; this repo's conclusion is only that they don't currently
  give a *reliable, unbypassable* server-side guarantee the way the
  client-side `_DENIED_PROVIDERS` check does. See `git log --grep=preset`
  in this repo for the try/revert commits if revisiting this.

## 7. ✅ Example Task

**Task:** `POST /brief` (with a valid `x-agent-key`).
**Expected output:** A JSON body with `brief` (a few short paragraphs, plain
English, e.g. *"35 of 42 tracked agents are healthy, 1 down, 1 not deployed.
The most recent WHATS_DONE.md entry (2026-08-22) covers the mission-evaluator
BLOCK-approval fix..."*), `provider_used` (e.g. `"openrouter:poolside/laguna-s-2.1:free"`),
and `sources` carrying the raw per-source status/counts independently of the
prose above.
