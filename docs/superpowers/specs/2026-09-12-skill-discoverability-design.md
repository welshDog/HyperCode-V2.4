# Skill Discoverability (`/ide` skill search) — Design Spec

Status: approved for planning
Owner: self-upgrade council Tier 5 track
Depends on: none (net-new feature, no existing partial implementation)

## 1. Problem

`docs/upgrades/HYPERCODE-SELF-UPGRADE-COUNCIL-VERIFIED-RERANK.md` (Tier 5)
confirmed there is no way for a human browsing `/ide` to discover which of
this repo's 31 local skills (`.claude/skills/*/SKILL.md`) fits a goal they
have — e.g. typing "deploy a Discord bot with moderation" and getting pointed
at `hypercode-broski-discord-bot`. `/ide` (`agents/dashboard/app/ide/page.tsx`)
is a 9-line file rendering `<StudioView />`, the coder-agent code-run studio —
not a skill browser of any kind. The separate HYPER-SILLs project has real
semantic search (MiniLM embeddings) but is wired into this repo only as a
static, non-searchable agent-boot loadout injection
(`agents/shared/loadout.py`), never exposed to a human.

## 2. Scope

**In scope**: a goal-in, ranked-skills-out search feature reachable from
`/ide`, backed by a new backend endpoint that reads the local skill catalog
and ranks matches using the existing free-model OpenRouter call.

**Out of scope** (deliberately, not oversight):
- **Onboarding tutorial.** The original council item bundled "discoverability
  + onboarding" together; they're unrelated deliverables (a guided
  first-skill walkthrough doesn't depend on which search approach is picked).
  Separate feature, separate spec if/when prioritized.
- **HYPER-SILLs' real semantic search.** Best long-term fit if HYPER-SILLs
  becomes the canonical cross-project skill index, but it isn't currently
  network-reachable from HyperCode-V2.4 (filesystem-mounted JSON only, no
  HTTP endpoint) — wiring that up is a separate, larger task gated on
  HYPER-SILLs exposing a real API first.
- **Consolidating the 14 duplicated `_build_llm_client()` copies** across
  `agents/*/base_agent.py` into one shared module. Irrelevant to this
  feature now that it doesn't need that pattern at all — see §4.
- **An Ollama fallback tier.** `openrouter_chat()` (§4) already targets a
  free model (`OPENROUTER_DEFAULT_MODEL`, defaults to
  `mistralai/mistral-7b-instruct:free`) — the "no cost" requirement is
  already met without a second tier. If `OPENROUTER_API_KEY` isn't
  configured, or the call fails for any reason (circuit breaker open,
  network error), fall straight to the substring matcher (§5) rather than
  adding Ollama as a second network dependency for a feature this small.
- **The "External Skill Pack"** referenced in `.claude/SKILLS.md`
  (`Hyperfocus-Global-Impact-Skills`, a separate GitHub repo) — those
  `SKILL.md` files don't exist on this filesystem, so there's nothing to
  parse. v1 catalog is local skills only.

## 3. Architecture

Matches this repo's own established patterns rather than inventing new ones:

```
Browser (/ide)
   │  POST goal text
   ▼
agents/dashboard/app/api/skills/route.ts   (new — Next.js proxy)
   │  fail-soft fetch, same style as fleet/route.ts
   ▼
hypercode-core: POST /api/v1/skills/search  (new FastAPI endpoint)
   │  1. parse .claude/skills/*/SKILL.md frontmatter (name + description)
   │  2. call existing model_routes.openrouter_chat() with
   │     settings.OPENROUTER_API_KEY / OPENROUTER_DEFAULT_MODEL (free)
   │  3. LLM ranks + returns top matches with one-line rationale each
   ▼
Ranked skill list back to browser
```

**Filesystem access gap (found during design, not assumed):** neither
`hypercode-core` (`backend/` build context) nor the dashboard
(`agents/dashboard/` build context) currently has `.claude/skills/` in their
build context or any volume mount — both contexts are deliberately narrow
(the crew-orchestrator's own compose comment explains why: a repo-root
context would ship ~3.85GB to buildkit). Fix: add a read-only mount to
`hypercode-core`'s compose block —
`./.claude/skills:/app/skills-catalog:ro` — same pattern already used for
the HYPER-SILLs loadout mount (`docker-compose.agents.yml`'s
`agent-loadouts.json`/`skills-registry.json` `:ro` mounts).

## 4. LLM call — genuinely reused, no new client code

Initial design assumed `backend/app/` had no LLM-calling code at all and
proposed writing a new client. **Corrected after closer inspection**:
`backend/app/core/model_routes.py` already has a generic, circuit-breaker-
wrapped `openrouter_chat()` function (privacy-mode-aware, proper error
handling — raises `RuntimeError` on bad responses rather than leaking a raw
`KeyError`), plus a standalone `OPENROUTER_API_KEY` /
`OPENROUTER_DEFAULT_MODEL` config pair in `config.py` (defaults to the free
`mistralai/mistral-7b-instruct:free`) that's independent of the two
specialized routes (`hunter_alpha`/`healer_alpha`, which are for unrelated
incident/architecture-routing decisions via `select_model_route()` — not
used by this feature).

The new endpoint calls `openrouter_chat()` directly:

```python
from app.core.model_routes import openrouter_chat

response_text = await openrouter_chat(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
    model=settings.OPENROUTER_DEFAULT_MODEL,
    messages=[{"role": "user", "content": prompt}],
    max_tokens=500,
    privacy_mode="none",  # skill names/descriptions aren't sensitive
)
```

No new file, no new LLM-client abstraction. If `settings.OPENROUTER_API_KEY`
is unset, or `openrouter_chat()` raises for any reason (circuit breaker
open, network error, bad response), fall straight to the substring matcher
(§5) — no Ollama tier, no retry loop, per the scope decision in §2.

## 5. API contract

`POST /api/v1/skills/search`

Request:
```json
{ "goal": "deploy a discord bot with moderation" }
```

Response (200, even on partial failure — fail-soft, matches `fleet/route.ts`
house style):
```json
{
  "matches": [
    { "name": "hypercode-broski-discord-bot", "rationale": "Builds and maintains the BROski Discord bot including moderation commands." }
  ],
  "usedFallback": false,
  "error": null
}
```

If `OPENROUTER_API_KEY` isn't configured or `openrouter_chat()` raises,
`matches` falls back to a plain substring match against skill
name+description (never an empty result just because the LLM is down),
`usedFallback: true`, `error` carries a short reason. Never a 5xx to the
browser for an LLM-availability problem — only for a genuinely broken
request (e.g. missing `goal`).

## 6. Prompt design

Single non-streaming call: system prompt lists the skill catalog (name +
description, ~31 entries, small enough to inline directly — no embedding
index needed for a corpus this size) and asks for the top 3-5 matches ranked
by relevance with a one-line rationale each, returned as strict JSON (parsed
with a graceful fallback to the substring matcher on any parse failure, same
fail-soft rule as an unreachable LLM).

## 7. Frontend

Small addition to the existing `/ide` page (not a new route — keeps it
discoverable where people already are): a goal input + a "Find a skill"
button above or beside the existing `StudioView`, rendering ranked result
cards (name, rationale, and — since these are real local skills — a
copy-paste-ready `/skill-name` invocation hint).

## 8. Testing plan

- Backend: unit tests for the frontmatter parser (valid/missing
  description, malformed YAML) and for the substring-fallback matcher in
  isolation from the LLM call.
- Backend: a test that mocks `openrouter_chat` to verify the endpoint's
  fail-soft behavior when it raises or when `OPENROUTER_API_KEY` is unset —
  never a 5xx, always `usedFallback: true`.
- Frontend: the new route's fail-soft behavior (mirrors `fleet/route.ts`'s
  existing test pattern if one exists, or a smoke test if not).
- Manual: verify a few real goals against the real 31-skill catalog return
  sensible matches (e.g. "deploy a discord bot" → `hypercode-broski-discord-bot`,
  "check for CVEs" → `cve-trivy-scan`).

## 9. Rollout

No profile gating needed — this is a read-only, additive endpoint + UI
element with no effect on the existing fleet. Ships as part of the standard
`hypercode-core` + `dashboard` rebuild, no new container, no new compose
service.
