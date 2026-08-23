# 🏁 Session Handover — 2026-08-23 · "N7 Through N1, Closed Live — Then a Model Name From 2024 Almost Undid It Twice"

> Continues from `docs/NEXT_SESSION_HANDOVER_2026-08-22-afternoon.md`. That
> session closed `review_mission`'s BLOCK-approval gap and shipped
> `broski-coo` v1, leaving N1/N2 (`ANTHROPIC_API_KEY` invalid, `DATABASE_URL`/
> `DASHBOARD_SERVICE_JWT` needing rotation) and item 0a
> (`project-strategist`'s dead `plan()`/`delegate_tasks()`) as open items.
> This session closed all of them, live-verified — then, chasing item 0a's
> *real* happy path once N1 unblocked it, found the same "stale model name
> baked into a Dockerfile" bug twice more, the second time across 7 files at
> once. Session paused mid-rollout for a terminal restart (Claude Code
> update), not because anything is broken.

---

## ⚡ TL;DR

1. **N7 — 6 more agents had the `broski-coo` bug.** Fleet-wide sweep found
   `brain-agent`, `business-agent`, `throttle-agent`, `tips-tricks-writer`,
   `super-hyper-broski-agent`, `test-agent` all missing `HYPERCODE_API_KEY`
   (had a stray `API_KEY` var instead) — fixed, verified live. Commit
   `67c6460d`.
2. **N4 — #435 was never a `broski-bot` bug.** Root cause was
   `docker-compose.yml` already `include:`ing `docker-compose.core.yml`;
   double-passing `core.yml` via `-f` merges every service with itself,
   duplicating list fields like `security_opt`. Fixed the one place
   modeling the broken pattern (`cleanup-and-prepare.ps1`), added a guard
   comment. Commit `eceb9254`, closed #435.
3. **N2 — JWT re-minted, Postgres password rotated live, zero downtime.**
   Found two real gaps doing it: `hypercode-core`/`celery-worker` read
   `HYPERCODE_DB_URL` not `DATABASE_URL` (missed by the first sweep);
   HyperHealth's `postgres-db-health` check stores a **literal DSN as a DB
   row**, not reactive to `.env` — re-seeded it. **Real incident**:
   recreating ~12 containers on the already-running 69-container fleet blew
   past this box's 4GB WSL2 cap and took the whole VM unresponsive — Docker
   Desktop restart + staged relaunch recovered clean, zero data loss.
   Commit `4d058124`, closed #434.
4. **Item 0a — `project-strategist`'s dead code wired up, twice over.**
   First pass (with N1 still broken): fixed the actual wiring bugs — missing
   `process_task` override, missing `await`s, nonexistent `self.config.core_url`.
   Commit `459a205b`. Second pass (once N1's real key was live): found 3
   *more* bugs the first pass couldn't reach — a retired model baked into
   the Dockerfile, `json.loads()` never stripping Claude's ` ```json ` fence,
   and `SPECIALIST_AGENTS` pointing at 3 stale ports with no auth header on
   the delegate call. Fixed all 3, proved a real 9-task plan end-to-end.
   Commit `ef801cba`, closed #433 (same commit as N1 below).
5. **N1 — Lyndz rotated `ANTHROPIC_API_KEY` himself; verified live.** Direct
   Anthropic call succeeds; `mission-director`'s `POST /propose` now returns
   `200`/`previewed` with a real Shepherd `ESCALATE` instead of
   `preview_unavailable`.
6. **Hook fix, proven not theorized.** `scripts/pets/git_post_commit.py`'s
   `subprocess.run(text=True)` calls had no explicit encoding, crashing on
   this repo's own emoji-heavy diffs (fired on 3 commits in one night).
   Fixed, then ran clean on the very commit that contained the fix. Commit
   `b404b7f9`.
7. **Item 0b — in progress, paused for a terminal restart.** All 7
   specialist agents (`frontend-specialist` through `system-architect`) had
   **no `ANTHROPIC_API_KEY` at all**. Wired it in for all 7. Then found the
   *same* stale-model bug as item 0a's Dockerfile — except this time
   copy-pasted identically across **all 7** specialist Dockerfiles
   (`claude-3-5-sonnet-20241022`, retired). Fixed the source everywhere;
   only 2 of 7 containers actually rebuilt + recreated with the fix before
   the pause. See "What's Actually Left" below — this is the one real
   unfinished thread.

---

## 🔴 What's Actually Left (start here)

**Finish item 0b's rollout.** Source is 100% fixed and committed
(`docker-compose.agents.yml`, `docker-compose.agents-full.yml`, all 7
`agents/0N-*/Dockerfile`s). `frontend-specialist` and `backend-specialist`
are already rebuilt + recreated + confirmed live. Still need the identical
treatment for `database-architect`, `qa-engineer`, `devops-engineer`,
`security-engineer`, `system-architect`:

```bash
# per agent, one at a time - do NOT wrap in an inner `timeout` (see gotcha below)
docker build --no-cache -t hypercode-v24-<name>:latest ./agents/0N-<name>
docker compose --profile agents [--profile hyper for security/system-architect,
  using -f docker-compose.yml -f docker-compose.agents-full.yml] \
  up -d --no-deps --force-recreate <name>
```

Verify each with:
```bash
docker exec <name> python3 -c "import os; print(os.environ.get('AGENT_MODEL'))"
# should print None, not claude-3-5-sonnet-20241022
```

Then re-verify the end-to-end feature: hit `mission-director`'s
`POST /api/v1/missions/propose` (or `project-strategist`'s `/execute`
directly) with a real feature request and confirm the specialists it
delegates to now produce real LLM output instead of "Connection error."

**⚠️ Gotcha that cost real time tonight**: `docker build`/`docker compose
build` for these agents installs `gcc`/`docker-cli` from scratch on
`--no-cache` and genuinely takes 2-3+ minutes. Wrapping it in an inner
`timeout N` for N under ~200s **silently kills the build while the outer
shell still reports "completed, exit code 0"** — the image tag is left
pointing at old content with zero error surfaced. Burned real time chasing
this as a phantom Docker Desktop cache-corruption theory before realizing
it was self-inflicted. **Just let the harness's own 120s auto-backgrounding
handle it — don't add your own timeout wrapper.**

---

## 🟢 Also Found, Not Investigated

`:memory:.ses` — a stray file with that literal name appeared in
`frontend-specialist`'s and `backend-specialist`'s bind-mounted directories
after their first restart in a while. Looks like some session/cache-store
code defaults to the SQLite `:memory:` DSN string and then misuses it as a
real filename somewhere. Untracked, harmless, not chased — worth a look if
it recurs on the other 5 specialists once they're recreated.

---

## 🔑 Key Facts (don't re-derive)

| Fact | Detail |
|---|---|
| `ANTHROPIC_API_KEY` | Valid now (Lyndz rotated it 2026-08-23 midday). Confirmed live via direct call and `mission-director` propose. |
| `DASHBOARD_SERVICE_JWT` | Re-minted, 365-day, expires ~2027-08-22. |
| Postgres password | Rotated live via `ALTER ROLE`, `.env` updated (`POSTGRES_PASSWORD`, `DB_PASSWORD`, `DATABASE_URL`). HyperHealth's `postgres-db-health` check re-seeded to match — **remember to re-seed that check (`python agents/hyperhealth/seed_checks.py --force`) on any future Postgres password rotation**, it stores a literal DSN as a DB row, not reactive to `.env`. |
| Two different DB-URL env vars | `hypercode-core`/`celery-worker` read `HYPERCODE_DB_URL` (built from `${POSTGRES_PASSWORD}` in compose); everything else reads `DATABASE_URL`. Both point at the same Postgres, just named differently — check both when auditing DB credential wiring. |
| Base-agent template model default | `agents/base-agent/agent.py` (and its per-agent copies) default to `claude-sonnet-4-6` when `AGENT_MODEL` isn't set — confirmed live-valid. Don't hardcode a model name in a Dockerfile; let it fall through to this default. |
| Host memory ceiling | WSL2 capped at 4GB via `.wslconfig` (deliberate, documented, never raise it). Recreating ~10+ containers on top of an already-running fleet can push past it — stage container churn in small batches, checking `wsl -e free -m` between each, rather than one blanket command. |
| Full container recovery after a WSL crash | `wsl --shutdown` / Docker Desktop restart, then bring the fleet back in stages: core infra (`docker-compose.core.yml`) → base stack (`docker-compose.yml`) → `agents-full.yml` → registry/hyperhealth/discord/brain profiles. Postgres's data volume survives a restart untouched — "Skipping initialization" in its logs confirms no data loss. |

---

## 📌 Carried Forward, Unchanged

- N5 — `docs/STATUS.md`'s "Agent Fleet — 25 Total" table is still stale (wrong ports, predates the 08-19/08-20 reconciliation). Banner-only fix, still needs a real pass.
- `project-strategist`'s old `Exited (255)` (found 2026-08-22 afternoon, root cause never identified) has not recurred since the 2026-08-22 night full-fleet restart.
- The P1-P3 dashboard playtest backlog and "This Week" list in `docs/NEXT_TASKS.md` — untouched this session, not raised.

---

> 🐶♾️ Built by @welshDog · Llanelli, Wales
