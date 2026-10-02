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

## Rollback

```bash
git log --oneline -5                 # find the last good commit / image tag
docker compose up -d --no-deps hypercode-core dashboard   # after checking out the previous commit and rebuilding
```
Migration `023` is additive; leaving it applied is harmless to older code.
