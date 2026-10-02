# 🐳 HyperCrew — Docker runbook (do this in the terminal)

> Short steps. One thing at a time. **Nothing here has been run on Docker yet** — the sandbox that built
> HyperCrew had no Docker. Every command below is written from the repo's own files; if one is wrong, fix the
> command and write the fix into `WHATS_DONE.md` (that is a real finding, not a failure).
>
> Branch: `claude/focused-darwin-ljrs8k` · PR: <https://github.com/welshDog/HyperCode-V2.4/pull/547>
> Rules from `CLAUDE.md` still apply: `git fetch` before any push, `.env` never committed, say "done" only after
> it is committed + pushed.

---

## 0 · Pre-flight (2 min)

```bash
cd HyperCode-V2.4
git fetch origin && git checkout claude/focused-darwin-ljrs8k && git pull origin claude/focused-darwin-ljrs8k
free -m          # need >= 1500 MB "available". Under that: STOP (stop rule below).
docker ps --format '{{.Names}} {{.Status}}' | head -40
```

**Stop rule (any step):** available RAM < 1.2 GB, `hypercode-core` unhealthy past 5×30 s, or any unexpected
restart → stop, start no optional services, write down what you saw.

## 1 · Rebuild the two things that changed (5–10 min)

`hypercode-core` (backend + migration `023`) and `dashboard` (Calm Mode, Panic, Focus, Morning Card).
`up -d --no-deps`, **never** `--force-recreate`.

```bash
docker compose build hypercode-core dashboard
docker compose up -d --no-deps hypercode-core dashboard
# if compose says "no such service": add --profile agents (dashboard lives in docker-compose.agents.yml)
docker inspect -f '{{.State.Health.Status}} restarts={{.RestartCount}}' hypercode-core hypercode-dashboard
```

✅ Expect: both `healthy`, `restarts=0`. Wait up to ~2 min for core.

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
- **Unverified on the live stack:** what Shepherd actually answers for a crew `agent_dispatch` node (ALLOW /
  ESCALATE / BLOCK). If it ESCALATEs in `enforce` mode the run waits for a human. Write down what you see.

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

**Handover gate (new):** phase 2 meets the Scribe's gate after the guard. By default it **skips** it
(`reject`), so it can never open a real PR. To approve it instead: `PROVE_APPROVE_HANDOVER=1` in front of the
phase-2 command (`docker exec -e PROVE_APPROVE_HANDOVER=1 -i …`). With no `CREW_GITHUB_TOKEN` set, approving
still opens nothing; the draft stays in the run and the card says so.

If a PASS line fails: copy the exact line, `docker logs hypercode-core --tail 80`, and stop. Fix the smallest
thing, re-run that phase.

## 5 · Look at it in the browser (5 min)

Open the dashboard → **/ide**.

- [ ] **Where was I?** card: one light (green/amber/red), at most 5 lines, one "Next:" line.
- [ ] **Pause everything** button in the header → click → "Saved. …" → button becomes "Paused (n) · Resume".
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

## Rollback

```bash
git log --oneline -5                 # find the last good commit / image tag
docker compose up -d --no-deps hypercode-core dashboard   # after checking out the previous commit and rebuilding
```
Migration `023` is additive; leaving it applied is harmless to older code.
