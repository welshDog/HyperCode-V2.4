# HS-035 — AI Behaviour Rules + Tool Matrix

> **Extracted from:** `CLAUDE.md §9` · HyperCode-V2.4
> **For:** Any AI working in the HyperFocus z0ne ecosystem

---

## Tools To Use — Don't Improvise

| Task | Correct Tool |
|---|---|
| DB changes (course) | Supabase MCP `apply_migration` — NEVER `db push` |
| DB queries / safe prod testing | Supabase MCP `execute_sql` — wrap in `BEGIN / ROLLBACK` |
| V2.4 DB changes | `docker compose exec hypercode-core alembic upgrade head` |
| Auth + browser testing | **Playwright** — `npm run test:e2e`, badges have `data-auth-status` |
| Deploy verification (course) | **Vercel MCP `get_deployment`/`list_deployments`** (team `team_Uy6hGYD4AZqclHqUeEsmZuDP`) ⚠️ NEVER curl-poll prod |
| Perf claims | `npm run build` chunk sizes = real evidence |
| Before claiming done (course) | `npx tsc --noEmit` + `npx eslint` + `npm run build` — all three green |
| Before `docker compose up` | `python scripts/env_check.py --core --secrets --profile discord` |

## Human-Only Gates

AI MUST NOT pretend to complete these:
- MetaMask / wallet popups (browser extension)
- Real Core Web Vitals (needs Vercel Speed Insights dashboard)
- Visual QA on physical devices
- Discord server manual smoke tests (P3c veto-ban)

## General Behaviour Rules

- **NEVER suggest anything in `WHATS_DONE.md`** — check it before every suggestion
- Surface contradictions — correct the doc, don't silently proceed
- **Lyndz runs a PARALLEL git workflow** — ALWAYS `git fetch` + check `origin/main` before pushing; NEVER force-push
- Quick wins first — momentum > perfection
- Nothing is done until committed and pushed
- Update the session report at end of every session

---

> ⚡ Tool hygiene = no silent failures. Follow the matrix.
