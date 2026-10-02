# 📋 NEXT_SESSION_HANDOVER — 2026-10-03 (HyperCrew: first Docker run)

> Bro, short version: **HyperCrew is deployed and proven on Docker.** Two real bugs found and fixed. The **happy path has not
> run yet** because the crew agents aren't running. Live status beats this file; `WHATS_DONE.md` beats everything.
> Branch `claude/focused-darwin-ljrs8k` · draft PR #547 · HEAD at wrap-up is the docs commit after `9f8b06b7`.

---

## 🟢 LIVE STATE RIGHT NOW

| Thing | State |
|---|---|
| `hypercode-core` | new HyperCrew build, healthy, RestartCount 0 (restarted once on purpose for the proof, 22:17 UTC) |
| `hypercode-dashboard` | new build + JWT secret, healthy, RestartCount 0 |
| `crew-orchestrator` | healthy, RestartCount 0, fixed import (restarted 22:26 UTC) |
| `safety-shepherd` | healthy; ALLOW for crew build/verify/publish |
| Migration `023` | applied (`alembic current` = 023 head; `quest_settlements` exists) |
| `coder-agent`, `qa-engineer` | **RUNNING since 2026-10-03 00:17 UTC** (healthy, RestartCount 0) — started on request after the first handover |
| Observability stack (12 containers) | **STOPPED** by me to free RAM (was 853 MB free → ~1.9 GB). Restart = your call |
| RAM | ~1917 MB available (WSL cap 4 GB — never raise it) |

## ✅ WHAT RAN (exact lines in `WHATS_DONE.md`)

Step 0 pre-flight (stop rule hit, fixed by stopping obs) · Step 1 rebuild + swap · Step 2 `alembic current` = `023 (head)`, table
`True` · Step 3 Shepherd ALLOW ×3 · Step 4 `PHASE0 PASS` (29/29), phase1 (3/3), real `docker restart hypercode-core`, **`PHASE2 PASS`**
(9/9, FAILED CLOSED branch) · Step 5 dashboard `/ide` **5/5**.

## 🐛 TWO REAL BUGS (fixed + pushed)

1. `b44c2505` — `crew-orchestrator/main.py` relative import → **every `/execute` was HTTP 500**. Pre-existing since 2026-09-01, on `main` too.
2. `9f8b06b7` — dashboard sent the master API key; core's `/operator/*` needs a human JWT → Morning Card / Pause / Calm Card all 502.
   Now a 30-day JWT in `secrets/dashboard_service_jwt.txt` (gitignored). **Expires ~2026-11-01 — rotate (runbook §8).**

## ⚠️ OPEN — NEEDS A DECISION FROM YOU

- **Exposed 10-year admin JWT.** `.env` line 214 `DASHBOARD_SERVICE_JWT` (user 9, superuser, exp 2036) was printed into the
  session transcript by my mistake. Also injected into `hypercode-core` and `postgres` containers (accidental?). Fix = rotate
  `JWT_SECRET` (kills every token incl. the 30-day one → re-mint) and delete that `.env` line. **Not done.**
- **Earlier leak in git history:** commit `f1edc13e` says `.claude/settings.local.json` "contained a gateway token". Untracking does not
  remove it from history on the pushed branch. Rotate that token if it was ever real.
- **Permission rule you added** (`/permissions`) for the mint command `Bash(cd … && docker exec -i hypercode-core python - < * > secrets/dashboard_service_jwt.txt)`.
  Remove it when you're done minting.
- Obs stack: restart it, or leave it off? (Needs ~1+ GB; the 4 GB ceiling is tight.)
- D1–D12 decisions, kill-switch compose wiring, real GitHub token for the Scribe: all still open, untouched.

## 🔁 UPDATE (00:30 UTC) — agents started, phase 2 re-run

`PHASE2 PASS` (9/9) again, still **FAILED CLOSED**, now "agent returned an empty result". Cause: the proof goal contains the word **"health"**, which
`coder-agent`'s keyword router turns into a **hard-coded mock** (`analyze_system_health()`); core refused it only because the mock's keys aren't text keys.
Fix prepared (agent flags `mocked: true`, core refuses it; tests pass) — **awaiting your go to commit + rebuild `hypercode-core` and `coder-agent`**.
To reach COMPLETED you also need a real LLM answer: pick a goal without trigger words (health/metrics/deploy/docker/todo list) and give `coder-agent` a model that
fits RAM (`tinyllama` ≈ 640 MB vs `qwen2.5:3b` ≈ 2 GB; the 4 GB WSL cap + ~1.9 GB free is tight — check RAM first, stop rule 1.2 GB). See `WHATS_DONE.md` 2026-10-03.

## ❌ NOT PROVEN

- **Happy path**: `build → verify → guard ALLOW → settle/XP → Scribe`. Agents are up now, but the proof goal is hijacked by a mock and no LLM fits RAM yet.
- Second Shepherd path `safety_client.check_dispatch` (strict, mutation agents like `coder-agent` are unregistered → deny-first MUTATION) — never run live; could fail.
- Pause everything with a *running* run ("Saved… / Paused (n) · Resume") — only the "nothing running" text seen.
- Real GitHub PR publisher (never touched). `tests/test_safety_contract.py` (crew-orchestrator) won't collect — not investigated.

## 🧠 GOTCHAS LEARNED

- `!` in this Claude Code prompt runs **Git Bash**, not PowerShell. `free -m` → `wsl -e free -m`. Git Bash mangles `/app` → use `MSYS_NO_PATHCONV=1`.
- **Never** show `docker compose config` output — it expands `.env` secrets. Use `-q`.
- `docker stop` on obs containers can say "zombie, can not be killed" yet free the RAM. Don't use `compose down` (can take core).
- Core runs `alembic upgrade head` before uvicorn: a bad migration = restart loop. First boot after the old stack can take minutes under RAM pressure.
- `crew-orchestrator` source is bind-mounted: edit + `docker restart crew-orchestrator`, no rebuild.
- The auto-mode classifier blocks writing to `secrets/`; the user runs it or adds a narrow permission rule.
- `serviceAuthHeader()` reads `DASHBOARD_SERVICE_JWT` **before** `DASHBOARD_SERVICE_JWT_FILE`.

## ▶️ NEXT TASK (one sentence)

Commit + deploy the `mocked` fix, then re-run `prove-crew.py` phase0→phase2 with a goal that avoids the mock trigger words and a RAM-safe model for `coder-agent`, to see whether the crew COMPLETES (guard verdict, XP, handover draft) — the happy path that has never run.

---

> 🐶♾️ Built by @welshDog · Llanelli, Wales
> *"Stop apologising for your brain. Start building."*
