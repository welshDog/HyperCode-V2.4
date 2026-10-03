# 🐳 HyperCrew — Docker runbook (do this in the terminal)

> Short steps. One thing at a time. **Run on Docker for the first time 2026-10-02/03 (Git Bash on Windows)** —
> steps 0–5 verified; corrections from that run are marked **[fixed 2026-10-03]**. Details: `WHATS_DONE.md`.
> If a command is wrong, fix it and write the fix into `WHATS_DONE.md` (a real finding, not a failure).
> **Git Bash tip:** it rewrites `/app/...` style args into `C:/Program Files/Git/app/...`. Prefix with `MSYS_NO_PATHCONV=1`.
> **Never** pipe `docker compose config` to the screen — it expands `.env` secrets. Use `-q` or name-only filters.
>
> Branch: `claude/focused-darwin-ljrs8k` · PR: <https://github.com/welshDog/HyperCode-V2.4/pull/547>
> Rules from `CLAUDE.md` still apply: `git fetch` before any push, `.env` never committed, say "done" only after
> it is committed + pushed.

---

## 0 · Pre-flight (2 min)

```bash
cd HyperCode-V2.4
git fetch origin && git checkout claude/focused-darwin-ljrs8k && git pull origin claude/focused-darwin-ljrs8k
wsl -e free -m   # [fixed 2026-10-03] plain `free -m` doesn't exist in Git Bash. Need >= 1500 MB "available".
docker ps --format '{{.Names}} {{.Status}}' | head -40
```

**[fixed 2026-10-03] If the observability stack is up, RAM will be under the floor** (first run: 853 MB). Stop it by name,
**not** `compose down` (that can take core with it): `docker stop grafana loki tempo pyroscope promtail node-exporter cadvisor
alertmanager celery-exporter prometheus prometheus-cloud grafana-agent`. Some may report "zombie, can not be killed" yet RAM still frees.
Core logs `Failed to export traces to tempo:4317` while Tempo is stopped — harmless.

**[2026-10-03] Run the guard first:** `python scripts/ram_guard.py --for build` (host + WSL + Docker in ~5 s; a build needs GREEN, exit 0/1/2). Add `--wait 120` to poll. It only measures. `wsl -e free -m` alone
cannot see the Windows **host** running out (1 MB free on 2026-10-03 while WSL showed 1.3 GB) — that thrash hung Docker and made every container read "unhealthy".

**Stop rule (any step):** available RAM < 1.2 GB, `hypercode-core` unhealthy past 5×30 s, or any unexpected
restart → stop, start no optional services, write down what you saw.

## 1 · Rebuild the two things that changed (5–10 min)

`hypercode-core` (backend + migration `023`) and `dashboard` (Calm Mode, Panic, Focus, Morning Card).
`up -d --no-deps`, **never** `--force-recreate`.

```bash
docker compose build hypercode-core      # one at a time keeps RAM down (~4 min)
docker compose build dashboard           # ~2 min
docker compose up -d --no-deps hypercode-core dashboard
# [fixed 2026-10-03] service names are right and NO profile is needed: docker-compose.yml include:s the others.
docker inspect -f '{{.State.Health.Status}} restarts={{.RestartCount}}' hypercode-core hypercode-dashboard
```

✅ Expect: both `healthy`, `restarts=0`. Core went healthy in < 30 s with RAM free (it runs `alembic upgrade head` before uvicorn,
so a failing migration = restart loop, not a log line).

## 2 · Confirm migration 023 applied (1 min)

Core runs `alembic upgrade head` on boot (see the database-architect bible).

```bash
docker exec hypercode-core alembic current            # expect: 023 (head)
docker exec hypercode-core python - <<'PY'
from sqlalchemy import inspect
from app.db.session import engine
print("quest_settlements" in inspect(engine).get_table_names())
PY
```

✅ Expect `023 (head)` and `True`. The migration is additive; `alembic downgrade 022` drops only that table.

## 3 · Is Safety Shepherd up? (1 min) — important new behaviour

Since Day 10 the crew **fails closed**: if Safety Shepherd cannot be reached, the builder, verifier and
publish steps are **blocked** (they say so, they do not quietly carry on). Core defaults to
`SAFETY_SHEPHERD_MODE=monitor`, and this block applies in `monitor` too. `off` skips the check entirely.

```bash
docker ps --format '{{.Names}} {{.Status}}' | grep -i shepherd     # want: safety-shepherd healthy
```

- Up → fine, go on.
- Not up → start it (`--profile agents`) **or** accept that crew runs will stop at `build` with
  "safety shepherd unreachable: blocked (fail closed)". That is correct behaviour, not a bug.
- **[verified 2026-10-03]** Shepherd answers **ALLOW** (`rule: default_allow`) for crew `build`, `verify`, `publish`
  (`category: generic`, as sent by `hyperflow_runner._safety_request`). Thin default — nothing crew-specific is checked.
  **[FIXED 2026-10-03 14:05 UTC, `f83c8321`]** the crew tools are now granted to the hyphenated names the orchestrator sends (`coder-agent`: `crew_build`, `qa-engineer`: `crew_verify`; live-verified ALLOW). Root cause: `_agent_caps` was an exact-key lookup, manifest keys are underscored, so hyphenated agents ran on the `*` wildcard. **[GENERALISED 2026-10-03 14:20 UTC, `55aea70a`]** the lookup now resolves exact name -> hyphen/underscore variant -> `*` (exact wins; `coder_studio` is `exact_name_only`), so backend-/frontend-specialist, devops-engineer and database-architect also get their real grants; live-verified 0 mismatches.
  **[CORRECTED 2026-10-03 14:40]** that is ONLY the flow runner's check. The orchestrator's *dispatch* check sends tool `crew_build` / `crew_verify`, which are NOT in `agents/safety-shepherd/capabilities.json` for `coder_agent` / `qa_engineer` → Shepherd **ESCALATEs** ("tool … not granted"); it is hidden because core + orchestrator run `SAFETY_SHEPHERD_MODE=monitor`. Switching to `enforce` would stall every crew build/verify. See `docs/IDE_HEALTH_REPORT_2026-10-03.md`.

## 4 · The live proof (10–20 min)

`scripts/prove-crew.py` runs **inside** `hypercode-core` so no token leaves it. It only reads, starts runs and
asks agents to *propose text*. Nothing is built, written or deployed.

```bash
docker exec -i hypercode-core python - phase0 < scripts/prove-crew.py
docker exec -i hypercode-core python - phase1 < scripts/prove-crew.py
#   ^ prints PARKED_TASK=…  PARKED_KEY=…  PARKED_NEXT_AFTER=…   (copy them)
docker restart hypercode-core                       # a REAL container restart, run parked at the plan gate
docker inspect -f '{{.State.Health.Status}}' hypercode-core     # wait for: healthy
docker exec -i hypercode-core python - phase2 <PARKED_TASK> <PARKED_KEY> <PARKED_NEXT_AFTER> < scripts/prove-crew.py
```

✅ Expect: every line `PASS`, ending `PHASE2 PASS`. Phase 2 may end **COMPLETED** (agents up, guard verdict) **or**
**FAILED CLOSED** (agents or Shepherd down). Both are valid; each is checked.
**[2026-10-03]** These commands work as written in Git Bash (phase0 29/29, phase1 3/3, phase2 9/9). In PowerShell use
`Get-Content scripts\prove-crew.py -Raw | docker exec -i hypercode-core python - phase0`.
**FAILED CLOSED is the weaker proof.** To reach COMPLETED the crew agents must be running (`coder-agent`, `qa-engineer`) and
`crew-orchestrator` must be healthy; with them down the orchestrator logs `HEALTH ALERT: N agents down`. First run ended FAILED
CLOSED with `orchestrator returned HTTP 500` — that was a real bug (relative-import in `crew-orchestrator/main.py`), fixed in `b44c2505`.
**[2026-10-03] COMPLETED reached** after 4 more fixes (see `WHATS_DONE.md`): phase 2 prints `COMPLETED: RUN_FINISHED with a guard verdict` + `guard decided BLOCK …`.
BLOCK is expected today: `qa-engineer` is an echo stub (no model) → verdict UNKNOWN. It takes ~2–10 min (the real model call is ~60 s); run long commands in the background.
Start the agents with `docker compose --profile agents up -d --no-deps coder-agent qa-engineer` (build each first). `PROVE_GOAL="…"` optionally overrides the goal in **both** phase1 and phase2
(`docker exec -e PROVE_GOAL=… -i hypercode-core python - phase1 < scripts/prove-crew.py`).

**[2026-10-03 12:50 UTC] Reaching guard ALLOW needs a capable model (opt-in).** `smollm2` (the host model) cannot write a diff. Steps — **check `wsl -e free -m` ≥ 1500 MB AND Windows free memory first** (a host at ~0 MB free thrashes Docker):
1. Start the proxy: `docker compose -f docker-compose.yml -f docker-compose.fcc.yml up -d --no-deps --no-build fcc-proxy` (healthy in ~1–2 min; ~300 MB). Its default model `nemotron-3-super-120b` is **dead** (EOL 2026-10-03); the file now defaults to `nemotron-3-ultra-550b-a55b`.
2. Point the agents at it for this launch: `CREW_LLM_BASE_URL=http://fcc-proxy:8083 docker compose --profile agents up -d --no-deps coder-agent qa-engineer` (**this sends crew text to NVIDIA NIM**; empty = local smollm2, the default).
3. Run phase1 → real core restart → phase2 as above. Expect `guard decided ALLOW`, one `quest_settlements` row (20 XP, 10 coins, real data on the owner account), the Scribe draft held, handover skipped.
To switch it OFF: recreate the two agents without the variable, then `docker stop fcc-proxy`.

**Handover gate (new):** phase 2 meets the Scribe's gate after the guard. By default it **skips** it
(`reject`), so it can never open a real PR. To approve it instead: `PROVE_APPROVE_HANDOVER=1` in front of the
phase-2 command (`docker exec -e PROVE_APPROVE_HANDOVER=1 -i …`). With no `CREW_GITHUB_TOKEN` set, approving
still opens nothing; the draft stays in the run and the card says so.

If a PASS line fails: copy the exact line, `docker logs hypercode-core --tail 80`, and stop. Fix the smallest
thing, re-run that phase.

## 5 · Look at it in the browser (5 min)

Open the dashboard → **/ide**.

- [ ] **Where was I?** card: one light (green/amber/red), at most 5 lines, one "Next:" line.
- [ ] **Pause everything** button in the header → click → with nothing running: "Nothing was running. You are all clear."
  (verified). With runs open: "Saved. …" → button becomes "Paused (n) · Resume" (**not yet seen live**).
- **Needs the dashboard JWT secret (§8).** Without it Where was I? says "Can't reach the crew right now" (502) — first run's bug.
- [ ] **Start focus** → pick 10/25/45 → the XP/gamify bits hide, extra tools fold away.
- [ ] **/sensory** → Calm/Focus/Energise presets; the Calm toggle in the header.
- [ ] Paste a crew task id into **Crew run** → the Calm Card follows it.

## 6 · Optional wiring (NOT done — each needs a decision)

| Want | Do | Notes |
|---|---|---|
| Kill-switch honoured by core | mount `./governance-control:/governance:ro` on `hypercode-core`, set `CREW_KILL_FILE=/governance/KILL`, restart core | Same sentinel the Governor uses. Unset = off. If the directory is unreadable the runs stop (an unknowable state counts as killed). Core does **not** read the Governor's Redis flag. |
| Real draft PR from the Scribe | create a fine-scoped GitHub token (contents + pull-requests, **this repo only**) as a Docker secret; set `CREW_GITHUB_TOKEN_FILE`; restart core | Only ever opens a **draft**, docs-only, new branch `crew/…`, never merges, never overwrites. **Never tested against real GitHub** — try it on a throwaway repo first (`CREW_GITHUB_REPO=you/throwaway`). |
| Tune XP | edit constants in `backend/app/crew/quests.py` | 20 XP, 10 if retried, 100/day ceiling. Decision D1. |

## 7 · Report back (so the next session starts clean)

Add to `WHATS_DONE.md`: what ran, the exact PASS/FAIL lines, anything that differed from this runbook, RAM
before/after, `RestartCount`. Then write `docs/NEXT_SESSION_HANDOVER_<date>.md`. Nice one BROski♾️.

## 8 · Dashboard credential (the dashboard's auth to core's `/operator/*`) — [added 2026-10-03]

Core's operator endpoints accept only a **human JWT (Bearer)** or a **registered agent key (X-Agent-Key)**. The master
`HYPERCODE_API_KEY` is neither. The dashboard reads a JWT from `secrets/dashboard_service_jwt.txt` (gitignored) via
`DASHBOARD_SERVICE_JWT_FILE`; the env var `DASHBOARD_SERVICE_JWT` must stay **unset** (code reads env before file).
Mint/rotate **inside core** (token never printed; owner superuser; 30 days) — current one **expires ~2026-11-01**:

```bash
# mint_dashboard_jwt.py (no secret in it) — run INSIDE core, stdout straight into the secret file:
#   from datetime import timedelta; from sqlalchemy import text
#   from app.core.security import create_access_token; from app.db.session import engine
#   with engine.connect() as c: uid = c.execute(text("select id from users where is_superuser and is_active order by id limit 1")).scalar()
#   print(create_access_token(uid, expires_delta=timedelta(days=30)))
docker exec -i hypercode-core python - < mint_dashboard_jwt.py > secrets/dashboard_service_jwt.txt
docker compose up -d --no-deps dashboard       # recreate to remount the secret
```
Check it works: `/api/crew/morning` and `/api/crew/panic` on the dashboard (`:8088`) return 200. **Never `cat` the file or
print `docker compose config`.** Rotating `JWT_SECRET` invalidates this token too — re-mint after.

## 9 · Host RAM safety — [added 2026-10-03]

The Windows **host** can run out of RAM while WSL looks fine (1 MB free on 2026-10-03), which hangs Docker and makes every container read "unhealthy".
- **Before any build/start/restart:** `python scripts/ram_guard.py --for build` (GREEN required; `--wait 120` polls). Chain heavy steps on its exit code: `python scripts/ram_guard.py --for build && <heavy step>`.
- **Signal for the throttle-agent:** Task Scheduler job `\HyperCode\HyperCode RAM Guard Signal` (manage with `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ram-guard-task.ps1 -Action status|start|stop|uninstall`).
- **throttle-agent** runs `THROTTLE_MODE=observe` (logs what it WOULD pause, never touches Docker; debounce 3 AMBER samples / 1 RED). Review checklist: `docs/NEXT_SESSION_HANDOVER_2026-10-03.md`. Do not set `enforce` yet.

## Rollback

```bash
git log --oneline -5                 # find the last good commit / image tag
docker compose up -d --no-deps hypercode-core dashboard   # after checking out the previous commit and rebuilding
```
Migration `023` is additive; leaving it applied is harmless to older code.
