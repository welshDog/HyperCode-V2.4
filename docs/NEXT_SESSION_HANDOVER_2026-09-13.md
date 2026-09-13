# Next-session handover — 2026-09-13 (full day: Skill Discoverability → merge → dashboard playtest → BROski Pulse fix)

## 🎉 What shipped this session — all merged to `main`

One continuous arc: reviewed Bro's design spec → planned → built → final
review → fixed 2 Critical bugs → **rebuilt and live-verified against the
real container** → **merged PR #526 to `main`** (`91359687`) → branch
deleted → **fixed a real bug found while investigating a dead OpenRouter
model** → **full live dashboard playtest** (every nav page, real browser) →
**found + fixed a second real bug** (BROski Pulse route collision) → docs
updated.

### 1. Skill Discoverability search for `/ide` — merged, live-verified

Goal-in, ranked-skills-out search over the 31 local `.claude/skills`, reusing
the existing free-tier OpenRouter call with a substring-match fallback.
New `POST /api/v1/skills/search` + `.claude/skills` read-only mount on
`hypercode-core`; new `/api/skills` proxy + `SkillFinder` widget on `/ide`.

Full write-up: `WHATS_DONE.md`'s two 2026-09-13 entries. Commits:
`367b9092` (feature), `82d92d7d`/`06ce0640` (docs), `b28c26b8` (N18 fix,
below), `ba94735e` (mypy fixes) → squash-merged as `91359687`.

### 2. N18 — dead OpenRouter default model + a bigger reasoning-tokens bug

`mistralai/mistral-7b-instruct:free` was pulled from OpenRouter entirely
(404). Investigating the replacement found most current OpenRouter free
models default to reasoning mode and return `content: null` after burning
`max_tokens` on hidden chain-of-thought — same failure class `broski-coo`
already had to work around for its own client, but this shared
`model_routes.py:openrouter_chat()` (used by **both** `Brain.think()` and
skills-search) never excluded it. Fixed: default model →
`nvidia/nemotron-3-super-120b-a12b:free`, `openrouter_chat()` now always
sends `reasoning: {"exclude": true}`. **Live-verified through the real
dashboard UI** (not just `curl`): a real search returned genuine
LLM-ranked results, `usedFallback: false`.

### 3. Full live dashboard playtest — `docs/dashboard-playtest-2026-09-13.md`

Every sidebar page clicked through in a real browser (Claude in Chrome)
against the real running stack. 9/10 pages clean, zero console errors,
accurate real data throughout (fleet counts, health status, Docker state
all independently matched `docker ps`).

**Headline finding:** `hypercode-dashboard` was running a build from
**2026-09-09** — 4 days stale, silently missing `SkillFinder` and every
other frontend change merged since (no errors, no broken pages — just
absent code, easy to miss). Rebuilt:
```
docker compose -f docker-compose.yml -f docker-compose.agents.yml build dashboard
docker compose -f docker-compose.yml -f docker-compose.agents.yml up -d --no-deps dashboard
```
**Note the compose service name is `dashboard`** — `hypercode-dashboard` is
only the `container_name`, defined in `docker-compose.agents.yml`. After
rebuild, `SkillFinder` confirmed working end-to-end through the real UI:
genuine LLM results, copy-to-clipboard, empty-input guard, and
dyslexia-mode theming all correct.

**New habit to adopt**: rebuilding `hypercode-core` after a backend merge
does **not** rebuild `dashboard` — they're independent, and nothing
currently reminds you the two can drift. Check both after any frontend
merge.

### 4. BROski Pulse route-collision bug — found via the playtest, fixed (`876ceda7`)

`backend/app/api/v1/endpoints/broski.py` had **two** `@router.get("/pulse")`
handlers registered on the same router:
```python
@router.get("/pulse")
def broski_pulse() -> Any:
    return {"status": "ok"}          # ← dead stub, registered first

...

@router.get("/pulse")
def get_broski_pulse(db: Session = Depends(get_db)) -> Any:
    """Public system-wide BROski$ pulse — no auth needed. Used by dashboard."""
    # ← real handler: Redis-cached, real coins/xp/level/agentsOnline data
```
FastAPI/Starlette silently keeps only the first exact path+method match, so
the real handler was **permanently dead code** — the dashboard's BROski
Pulse panel had been fed a bare `{"status":"ok"}` for who knows how long,
not a crash, just always-wrong data. Found this while chasing a reported
`/api/broski` → 503 during the playtest (that literal 503 was never
reproduced again and is separately attributed to the RAM situation below —
but investigating it surfaced this much more real, permanent bug).

Fixed: deleted the stub. Added `test_broski_pulse_returns_real_data_not_stub`
asserting the real response shape, so this exact shadowing can't silently
regress. Confirmed live after rebuilding `hypercode-core`:
```
{"coins":0,"xp":6655,"level":7,"level_name":"BROski Legend ♾️","agentsOnline":2,"userCount":1}
```
That XP is genuinely earned — from this session's own git-commit XP hooks
firing on every commit made tonight.

## 🪤 N22 (new) — this box's RAM ceiling needs its own session, not another restart

This is the big structural loose end. Across the **entire session** (spec
review through the final bug fix), free RAM sat at **0.4–0.9 GB** nearly
continuously, with the full agent fleet + observability stack + this
session's own Docker builds all contending for it at once. This wasn't one
incident — the same class of symptom recurred **repeatedly** across many
hours:

- Two full `pytest` runs OOM-killed by the system.
- The **Docker daemon itself** started 500-erroring on every API call —
  including a bare `docker version` — twice. Only fixed by a full **Docker
  Desktop restart** (Bro's action), not anything at the container level.
- `hypercode-core` fully booted, served real traffic for an extended
  stretch (real `/health` 200s, real WebSocket connections, a real economy
  webhook), then **silently stopped accepting connections** —
  `RestartCount` stayed `0` the whole time, so it wasn't crashing, it was
  hanging.
- `hypercode-dashboard` intermittently returned `Recv failure: Connection
  was reset` specifically on routes that make a live cross-container fetch
  (`/api/broski`) — reproduced this exact symptom **twice**, both times
  correlated with RAM in the 0.5–0.7 GB range, both times self-resolving
  within a few retries once RAM ticked back up. Pure page loads (`/`,
  `/ide`) stayed stable even when the proxy route didn't — the extra
  network hop is where the remaining margin bites first.
- Stopping the 12-container observability stack reliably freed only
  **~0.2–0.3 GB** each time — a real help, but not enough on its own to
  fully stabilize things. Toggled off/on multiple times this session at
  Bro's direction.

None of this was "fixed" — it was worked around live, repeatedly: wait,
retry, stop obs, restart Docker Desktop, rebuild when the moment allowed.
**Worth a session actually dedicated to the ceiling itself**: what's really
consuming the RAM right now (a fresh `docker stats` sweep would tell you
fast), whether `docker-compose.memory-limits.yml` is actually applied to
everything that's currently up, and whether running the full agent fleet +
observability stack together is sustainable on this box **at all** — this
session re-confirmed the 2026-09-03 rule the hard way, repeatedly, rather
than proving it wrong.

## Stack state at handover

**FINAL state (2026-09-13 ~16:23 GMT+1): observability stack UP (restarted
at Bro's request after this session's RAM investigation), `hypercode-core`
and `hypercode-dashboard` both `healthy` and confirmed serving real traffic,
both this session's bug fixes live-verified.**

- Obs stack stop/start commands (used multiple times this session):
  ```
  docker stop  grafana prometheus prometheus-cloud loki tempo pyroscope promtail node-exporter cadvisor alertmanager celery-exporter grafana-agent
  docker start grafana prometheus prometheus-cloud loki tempo pyroscope promtail node-exporter cadvisor alertmanager celery-exporter grafana-agent
  ```
- `hypercode-core`: built + recreated from `main` multiple times this
  session (last time for the BROski Pulse fix). Healthy, RAM permitting —
  see N22.
- `hypercode-dashboard`: rebuilt from `main` mid-session (was 4 days stale —
  see finding #3 above). Healthy, but the most RAM-sensitive container
  observed this session for connection resets on its `/api/broski` proxy
  route specifically.
- `redis`/`postgres`/`hypercode-ollama`: untouched all session, restarts=0
  throughout.
- Orphan-container warnings from the 2-3-file `docker compose` commands used
  tonight are expected and harmless — **never** `--remove-orphans`.

## ONE next task

**N22** — give this box's RAM ceiling a real session: a `docker stats`
sweep to see what's actually consuming it right now, confirm
`docker-compose.memory-limits.yml` coverage, and decide (not re-litigate)
whether full-fleet + obs is ever meant to coexist on this hardware.
Everything else from tonight (N18–N21) is resolved and live-verified.

🎉 Nice one BROski♾️ — feature shipped, merged, live-verified, and the
playtest paid for itself twice over by catching a real dead-code bug most
casual testing would never have found.
