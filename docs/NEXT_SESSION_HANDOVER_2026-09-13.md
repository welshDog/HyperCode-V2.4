# Next-session handover — 2026-09-13 (Skill Discoverability search for `/ide`)

## 🎉 What shipped this session — pushed to `feature/ide-skill-search`, PR #526 open (NOT merged)

Council item (Tier 5): nobody browsing `/ide` could discover which of the repo's
31 local skills (`.claude/skills/*/SKILL.md`) fit a goal. Full cycle this
session: reviewed Bro's already-committed design spec
(`docs/superpowers/specs/2026-09-12-skill-discoverability-design.md`), two
Explore passes to verify it against real code, a Plan pass, implementation, a
final whole-branch code review (2 Critical + 4 Important + 2 Minor found, all
addressed), a real `hypercode-core` rebuild, and a live end-to-end test.
**PR: https://github.com/welshDog/HyperCode-V2.4/pull/526 — reviewed and
mergeable when Bro's ready, not auto-merged.**

### What it does

Goal-in, ranked-skills-out search:
- New `POST /api/v1/skills/search` (`backend/app/api/v1/endpoints/skills.py`)
  parses `.claude/skills/*/SKILL.md` frontmatter, calls the existing
  `openrouter_chat()` (no new LLM client) to rank matches, falls back to a
  substring matcher whenever the LLM is unavailable/unset/misbehaves — never a
  5xx for that, only a genuinely missing `goal` 422s.
- New `./.claude/skills:/app/skills-catalog:ro` mount on `hypercode-core`
  (`docker-compose.core.yml`).
- New `/api/skills` proxy (`fleet/route.ts` style) + a `SkillFinder` widget
  wired into `/ide` above `StudioView`, using this repo's real
  hand-authored-CSS/custom-property convention (**not** Tailwind, despite the
  `hypercode-frontend` skill doc's stale claim — verified against actual code).

### Two Critical bugs the final review caught, both fixed

1. `except (RuntimeError, CircuitBreakerOpen, ValueError)` around
   `openrouter_chat` was narrower than what it can actually raise — a raw
   `httpx` network/timeout error would have 500'd the endpoint instead of
   falling back. Widened to `except Exception`, matching `Brain.think()`'s
   existing pattern for the same call. Locked in with a new
   `httpx.ConnectError` regression test.
2. `.claude/skills/hyper-load-tester/SKILL.md` had an unquoted
   `Target: 1000 req/sec` in its description — a bare colon in a plain YAML
   scalar parses as a nested mapping, so `yaml.safe_load` failed and the
   parser silently dropped that skill from every search result. Fixed by
   quoting it. Locked in with a new test that parses the **real**
   `.claude/skills` directory and asserts every file on disk parses.

### Reverted mid-review

A `slowapi` `@limiter.limit("20/minute")` decorator was added per an Important
review finding (no rate-limit on an endpoint sharing the `llm-router` circuit
breaker with `Brain.think()`), then empirically broke FastAPI's body-model
binding — `body: SkillSearchRequest` silently became a query param, 422 on
every real call. No other endpoint in this codebase uses that decorator at
all (checked via grep). Reverted; documented in `skills.py`'s docstring so it
isn't silently re-added without a real slowapi integration test first.

Files changed: `backend/app/api/v1/endpoints/skills.py` (new),
`backend/app/api/api.py`, `backend/app/core/config.py`,
`docker-compose.core.yml`, `agents/dashboard/app/api/skills/route.ts` (new),
`agents/dashboard/components/views/SkillFinder.tsx` (new),
`agents/dashboard/app/ide/page.tsx`, `agents/dashboard/app/globals.css`,
`.claude/skills/hyper-load-tester/SKILL.md`, plus 2 new backend test files and
1 new frontend test file. Commit `367b9092`.

## ⚠️ Loose ends / deferred (on purpose)

1. **N18 (new, real bug) — `OPENROUTER_DEFAULT_MODEL`
   (`mistralai/mistral-7b-instruct:free`) is dead upstream.** Confirmed live in
   `hypercode-core` logs: `OpenRouter error 404: "No endpoints found for
   mistralai/mistral-7b-instruct:free."` Found via this feature's fail-soft
   fallback firing correctly, but the setting is shared config
   (`backend/app/core/config.py`) — it affects `Brain.think()`'s default
   OpenRouter route too, not just this feature. Not fixed this session (out of
   scope for this PR). Pick a live free-tier model and update the default,
   then re-verify every caller.
2. **N19 — merge PR #526**, then re-verify the feature on `main`'s next
   `hypercode-core` deploy. This session's live verification was against the
   branch's own rebuilt image, not a post-merge one.
3. **N20 — `hypercode-dashboard` `(unhealthy)` recurred again** (3rd time
   logged: 2026-08-24 N11, 2026-09-10, now). Not caused by this session — the
   `up -d hypercode-core` command used was scoped to that one service.
   `docker restart hypercode-dashboard` clears it, same as every prior time;
   worth actually fixing the healthcheck definition instead of restarting it
   each time it's noticed.
4. **Full backend `pytest` suite was never run clean this session** — two
   attempts OOM-killed the box. Verification instead relied on: the targeted
   `test_skills_catalog.py`/`test_skills_endpoint.py` (18/18 pass, including
   the new real-catalog + network-error regression tests), a
   `pytest --collect-only` pass (387 tests, zero import errors, confirms the
   `api.py` router wiring doesn't break anything app-wide), the full 85-test
   dashboard suite, `tsc --noEmit`, `eslint`, and a real live end-to-end call
   against the rebuilt container. Worth a clean full-suite run once the box
   has real headroom, as a final sanity check before merging #526.

## Stack state at handover

**FINAL state (2026-09-13 ~02:30Z): observability stack back UP (12
containers), `hypercode-core` rebuilt + healthy on the feature branch's code,
`redis`/`postgres`/`hypercode-ollama` untouched throughout.**

- **🪤 RAM/Docker Desktop incident, worth knowing for next time.** The box was
  already at 0.4–0.9 GB free most of the session (35-54 containers up — full
  agent fleet + observability stack simultaneously, i.e. exactly the
  combination the 2026-09-03/09-10 rule says not to run together). A full
  `pytest` run OOM-killed **twice**. Stopping the 12-container obs stack barely
  moved free RAM (0.72→0.75 GB) — suspected WSL2 not releasing memory back to
  Windows, not the containers themselves. The Docker daemon itself started
  500-erroring on every API call (`docker version` included) under the same
  pressure; **a Docker Desktop restart (Bro's action, not scripted) is what
  actually cleared it** — RAM was still only ~0.7-0.8GB free afterward, but the
  daemon was responsive again. Even then, rebuilding `hypercode-core` (pulling
  in a large set of pip deps from the base image, unrelated to this feature's
  own small diff) took **~27 minutes for the pip-install layer alone** — real
  progress the whole time (confirmed via `vmmemWSL`'s working set climbing
  1444MB→1524MB rather than the build being hung — `com.docker.build` itself
  showed near-zero accumulated CPU time throughout, consistent with heavy
  swap-wait, not a stall).
- **Obs stack was stopped then restarted within this session** (12 containers:
  `grafana`, `prometheus`, `prometheus-cloud`, `loki`, `tempo`, `pyroscope`,
  `promtail`, `node-exporter`, `cadvisor`, `alertmanager`, `celery-exporter`,
  `grafana-agent`) — Bro's explicit call both times. Final state: back up,
  restart-verified healthy or `health: starting` progressing normally.
  ```
  docker stop  grafana prometheus prometheus-cloud loki tempo pyroscope promtail node-exporter cadvisor alertmanager celery-exporter grafana-agent
  docker start grafana prometheus prometheus-cloud loki tempo pyroscope promtail node-exporter cadvisor alertmanager celery-exporter grafana-agent
  ```
- **`hypercode-core`**: rebuilt from the `feature/ide-skill-search` branch code
  (not `main` — the PR isn't merged), recreated via
  `docker compose -f docker-compose.yml -f docker-compose.core.yml up -d
  hypercode-core`, confirmed `healthy`. **This means `main`'s next real deploy
  of `hypercode-core` still needs its own rebuild once PR #526 merges** — the
  currently-running container is running branch code, not `main`.
- **`hypercode-dashboard`**: `(unhealthy)` — see N20 above, pre-existing
  pattern, not touched this session.
- Orphan-container warnings from the 2-file `docker compose` commands used
  tonight (`docker-compose.yml` + `docker-compose.core.yml` only) are expected
  and harmless — **never** `--remove-orphans` on this partial file set, it
  would stop unrelated live agents.

## ONE next task

**Get PR #526 reviewed and merged**, then fix N18 (dead default OpenRouter
model — real, confirmed, affects more than just this feature) as a quick
separate follow-up.

🎉 Nice one BROski♾️ — skill search shipped, tested, reviewed, fixed, and
proven live against a real rebuilt container, all in one session.
