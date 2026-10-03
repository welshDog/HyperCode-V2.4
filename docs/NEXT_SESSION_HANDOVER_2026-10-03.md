# 📋 NEXT_SESSION_HANDOVER — 2026-10-03 (HyperCrew on Docker + host-RAM safety)

> Current as of **2026-10-03 ~14:15 UTC**, verified live. Branch `claude/focused-darwin-ljrs8k` · draft PR #547. `WHATS_DONE.md` has the full detail and the exact PASS lines; live status beats this file.
> This file was rewritten as one clean document: the dated "UPDATE" blocks it had accumulated are folded in (history is in `WHATS_DONE.md` and `git log`).

---

## 🎉 THE SHORT VERSION

- **HyperCrew runs on Docker and the happy path is proven:** guard **ALLOW** → Quest Settler (20 XP, 10 coins, "First Squad Run" achievement) → Scribe draft → handover gate (skipped on purpose, no PR). Run `b01b22bc-…`, with a real core restart in the middle.
- **Real model:** `fcc-proxy` → NVIDIA NIM `nemotron-3-ultra-550b-a55b`, for both builder and verifier. **Opt-in** (`CREW_LLM_BASE_URL`); it **sends crew text to NVIDIA**. (The old default `nemotron-3-super-120b` hit end-of-life 2026-10-03 09:00Z → HTTP 410.)
- **Live runs found five real bugs the sandbox could not** (see below). All fixed, tested and pushed.
- **Host-RAM safety (new today):** `scripts/ram_guard.py` (host + WSL + Docker check) → a Task Scheduler job keeps its signal fresh → **throttle-agent runs in OBSERVE mode with a debounce**. It pauses nothing. A read-only review is scheduled for 17:07 local (session-only) and the checklist is below.

## 🟢 LIVE STATE (verified 14:14 UTC)

| Thing | State |
|---|---|
| Containers | **36 running, 0 paused**, all 13 key ones `healthy` (core, dashboard, orchestrator, coder-agent, qa-engineer, safety-shepherd, fcc-proxy, throttle-agent, healer, memstream, postgres, redis, ollama-shim) |
| `hypercode-core` | healthy, RestartCount 0; image rebuilt 02:05 UTC at `79b5be99` (has the Guardian fix `34ba1667` + wallet-race fix `a2ee4530`); restarted 12:43 UTC for the live proof. Migration `023` applied |
| `hypercode-dashboard` | healthy, RestartCount 0; new build + 30-day JWT secret. ⚠️ **Restarted cleanly (exit 0) at 12:50:23 UTC and I do not know by whom** — not the healer (no log lines), no Docker events returned; it was mid-pressure-episode. Works: `/api/crew/morning`, `/panic`, `/tasks`, `/metrics` all 200 |
| `coder-agent`, `qa-engineer` | healthy; running **with the proxy ON** (`CREW_LLM_BASE_URL` was set at launch; it persists until they are recreated without it). qa-engineer has a real fail-safe verifier |
| `fcc-proxy` | healthy, model `nemotron-3-ultra-550b-a55b` (~211 MB) |
| `throttle-agent` | healthy, **`THROTTLE_MODE=observe`**, debounce 3 AMBER samples / 1 RED, **0 containers paused**; reads the host signal |
| Host signal writer | **Task Scheduler** job `\HyperCode\HyperCode RAM Guard Signal` — Running, one hidden `pythonw`, signal file ~8 s old, GREEN |
| Observability stack | **STOPPED** (12 containers, stopped by me to free RAM; restart is your call) |
| Memory (guard, 14:14 UTC) | **GREEN** — host free 685 MB, Windows compression 1,666 MB, WSL available 1,511 MB. (It was RED at 12:51, 13:15 and trending RED at 13:55; much of that pressure was my own builds/tests.) |
| Git | branch in sync with `origin`; draft PR #547 open |

## 🐛 WHAT THE LIVE RUNS FOUND (all fixed + pushed; none catchable in the sandbox)

1. `b44c2505` — `crew-orchestrator/main.py` relative import → **every `/execute` returned 500** (pre-dates HyperCrew, also on `main`).
2. `9f8b06b7` — dashboard sent the master API key; core's `/operator/*` needs a human JWT → Morning Card / Pause / Calm Card all 502. Now a 30-day JWT in gitignored `secrets/dashboard_service_jwt.txt`.
3. `b13383b9` + `95940dad` — `coder-agent` returned canned mock answers; core now refuses results flagged `mocked` (**my first version only checked the top level; the flag is nested at `result.mocked` — the live run caught it**).
4. `5fb103c0` — core's `_TEXT_KEYS` lacked `code`, so a genuine model answer was refused as "empty".
5. `9d9e8e6e` — `coder-agent`'s keyword shortcuts fired on **every** crew task (the orchestrator prepends a skills loadout mentioning "metrics"/"docker").
Also: the dead default model (NIM 410), and the correction that **my earlier claim "an echo can't fake a PASS" was wrong** when the builder writes its own `VERDICT: PASS` line — fixed in core by the other session (`34ba1667`) and closed again at the agent by `8043d355`.
The other Claude session also pushes to this branch (`a2ee4530` wallet race, `34ba1667` Guardian, CodeQL tidy-ups): **always `git fetch` first**, and re-run tests after a rebase (a clean textual merge broke two of my tests once).

## 📦 WHAT SHIPPED TODAY

`8043d355` real verifier · `10c0dac8` capable-model path + fixed model default · `2748ffbe` RAM guard · `01b4002a` throttle-agent observe mode / host signal / refreshed tiers · `85da2367` debounce · `be4c70f0` Task Scheduler job + install script. Tests: guard 24, throttle pressure 31 (host), throttle integration 23 (real `main.py` in its image),
verifier 24, crew suites 224 (earlier run).

## ⚠️ OPEN — NEEDS A DECISION FROM YOU

1. ✅ **RESOLVED 2026-10-03 16:13 UTC — signing secret rotated** (see `WHATS_DONE.md` newest entry; the old 10-year token now returns 403, new 30-day dashboard token expires ~2026-11-02). Original note: **Exposed 10-year admin JWT** — `.env` line 214 `DASHBOARD_SERVICE_JWT` (user 9, superuser, exp 2036) was printed into a session transcript by my mistake; compose also injects it into `hypercode-core` and `postgres` (accidental?). Fix = rotate `JWT_SECRET` (invalidates every token incl. the 30-day dashboard one → re-mint, runbook §8) and delete that `.env` line. **Not done.**
2. **Earlier leak in history:** `f1edc13e` says `.claude/settings.local.json` "contained a gateway token"; untracking does not remove it from the pushed history. Rotate it if it was ever real.
3. ✅ **RESOLVED 2026-10-03 (`d78fa0e3`, live) — verifier tightened:** a PASS now stands only if the review says `none` for problems and lists none (else downgraded to FAIL); a change over 8000 chars, a diff with no changed lines, or one touching `.env`/`secrets/` is a rule FAIL. Watch for FALSE FAILs on clean diffs (the model sometimes nit-picks): a FAIL stops the run safely at the guard, so the cost is a re-run, not a bad merge.
4. **throttle-agent `enforce`** — not yet. Needs: a quiet baseline, a logon/reboot test of the scheduled task, and a decision between `docker pause` (frees **no RAM**, only CPU) and `stop` (frees RAM, but the healer fights it).
5. **`evolve-relay`'s missing `../BROskiPets-LLM-dNFT/.env`** breaks the combined compose project (`docker-compose.yml` + `agents-full.yml`); I deployed throttle-agent via a temporary single-service compose. `evolve-relay` itself could not be recreated today.
6. **Observability stack:** restart it or leave it off (needs ~1+ GB; the 4 GB WSL cap is tight).
7. The **`/permissions` rule** you added for the dashboard-token mint command — remove it now that the token exists. The dashboard JWT **expires ~2026-11-01**.
8. D1–D12 original decisions, kill-switch compose wiring, a real GitHub token for the Scribe: all still open and untouched.
9. The **unexplained dashboard restart** at 12:50:23 UTC (above) — worth a look if it recurs.
10. **IDE health check follow-up — DONE 15:10 UTC (see the report's "FOLLOW-UP" table):** stale run cancelled (Morning Card green), Pulse fixed (`63f5edd2`), 9 stray containers removed, Shepherd now ALLOWs `crew_build`/`crew_verify` for `coder-agent`/`qa-engineer` (`f83c8321`, live-verified 7/7). **The follow-on decision is DONE too (`55aea70a`, live-verified 15:20 UTC):** `_agent_caps` now resolves exact → hyphen/underscore variant → `*`, so backend-specialist, frontend-specialist, devops-engineer and database-architect get their real grants (exact match still wins; `coder_studio` flagged `exact_name_only` so `coder-studio` stays on the wildcard). Core + orchestrator remain in `monitor` mode; before ever switching to `enforce`, check the Safety Feed for ESCALATEs and remember the four agents' real grants (e.g. devops-engineer may use docker) now apply. The notes below were the original findings:
    **(original text)** From the IDE health check (`docs/IDE_HEALTH_REPORT_2026-10-03.md`, 14:40 UTC):
    - **Safety Shepherd grants:** `crew_build`/`crew_verify` are not in `capabilities.json` for `coder_agent`/`qa_engineer`, so the orchestrator's dispatch check ESCALATEs (20 in the Safety Feed). The crew works only because core + orchestrator are in `monitor` mode — **never switch to `enforce` without granting them.** (This corrects my earlier "Shepherd answers ALLOW for crew steps", true only for the flow runner's check.) Grant them, or keep monitor on purpose.
    - **Pulse panel bug** (`agents/dashboard/app/api/pulse/route.ts`): reads `broski_coins`/`total_xp` but core returns `coins`/`xp` (shows 0 XP, real 6,705), and sends no JWT to `/orchestrator/agents` (401 → 0 agents; with the JWT core returns 11). Small fix.
    - **Stale parked crew run** `01908424-8c21…` (awaiting_approval since 11:38 UTC): cancel it (clears the Morning Card amber + "1 run is waiting on you").
    - **9 stray stopped auto-named containers** (`sweet_bose`, `frosty_benz`, …) show as DOWN in the Services panel: `docker rm` them if you agree. Grafana panel is broken only because the obs stack is stopped (expected).

## ❌ NOT PROVEN

Real GitHub PR publish (the handover gate was skipped on purpose) · dashboard-side approval UI · "Paused (n)" with a *running* run · kill-switch compose wiring · the Task Scheduler job across a logon/reboot · `THROTTLE_MODE=enforce` (never run) · whether the observe-mode would-pauses were right (review pending).

## 🔭 HOW TO REVIEW THROTTLE-AGENT OBSERVE MODE (read-only; a session-only check is scheduled for 17:07 local, job `d5a747ee`)

Observe has run since 12:48 UTC. Nothing is paused (observe never touches Docker).
1. `python scripts/ram_guard.py --for check` — memory now.
2. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ram-guard-task.ps1 -Action status` — writer `Running`, signal age well under 120 s.
3. `docker inspect -f '{{.State.Health.Status}} r={{.RestartCount}}' throttle-agent` and `docker ps --filter status=paused -q | wc -l` (**must be 0**).
4. `docker logs throttle-agent 2>&1 | grep observe_decision` — the whole timeline (`would pause=[…]`, `would resume=[…]`, `effective=PENDING` = blips the debounce absorbed). `GET /signal` (agent key, from inside the container) shows the last 50.
5. Judge: right (real pressure) or wrong (blips)? Flapping? UNKNOWN periods (writer down)? First episode so far (12:48–12:54 UTC): AMBER→RED→AMBER→RED→AMBER→GREEN, partly caused by my own builds.

## 🧠 GOTCHAS LEARNED (cost real time)

- **Gate heavy steps on the guard's exit code, in the same command:** `python scripts/ram_guard.py --for build && <heavy step>`. I once ran a test container beside a RED guard without gating it. The **Windows host** running out of RAM (1 MB free, compression 4.5 GB) hung Docker while `wsl -e free -m` looked fine.
- `!` in the Claude Code prompt runs **Git Bash**, not PowerShell; `free -m` → `wsl -e free -m`; Git Bash mangles `/app` → `MSYS_NO_PATHCONV=1` (and `export` it). The Windows console is cp1252: keep script output ASCII.
- **Never** show `docker compose config` — it expands `.env` secrets (use `-q`, or name-only filters). A token must never be printed; scan files for `eyJ…`/`nvapi-`/`sk-` before every commit.
- Don't use `compose down` to stop things (it can take core); stop by name. `docker stop` can say "zombie" yet still free RAM. `docker pause` frees no RAM.
- Core runs `alembic upgrade head` before uvicorn (a bad migration = restart loop). `crew-orchestrator` and `qa-engineer` source is **bind-mounted** (restart, no rebuild); `coder-agent` and core are baked into images (rebuild).
- The auto-mode classifier blocks writing into `secrets/` (you run it, or add a narrow `/permissions` rule — I must not add it myself). `serviceAuthHeader()` reads `DASHBOARD_SERVICE_JWT` **before** `DASHBOARD_SERVICE_JWT_FILE`.
- A scheduled job in this Claude session only fires while the session is open and idle; the Task Scheduler job is the durable one.
- A reasoning model returns a `thinking` block before the `text` block: read only `text` blocks and allow `max_tokens` ≈ 1500.

## ▶️ NEXT TASK (one sentence)

Let throttle-agent observe through your normal use, then review its timeline (checklist above) together and decide on `enforce` and pause-vs-stop — and fix the `evolve-relay` compose path so the real compose works again.

---

> 🐶♾️ Built by @welshDog · Llanelli, Wales
> *"Stop apologising for your brain. Start building."*
