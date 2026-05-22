# HS-031 — V2.4 Sacred Rules (22 Rules)

> **Extracted from:** `CLAUDE.md §3` · HyperCode-V2.4
> **Warning:** Break these = OOM crashes, security holes, or infra cascade failures.

---

| # | Rule | Why | Consequence if broken |
|---|---|---|---|
| 1 | **`docker-ce-cli` NEVER `docker.io`** for socket agents | Socket agent auth depends on it | Agent connectivity breaks |
| 2 | **`from app.X import Y` NEVER `from backend.app.X`** | Absolute import path is `app.*` | Import errors across all agents |
| 3 | **FastAPI public routes BEFORE auth-gated routes** | Route ordering matters in FastAPI | Auth-gated routes shadow public ones |
| 4 | **Stripe webhook ALWAYS rate-limit exempt** | Stripe retries have strict timing | Webhook drops, payments fail |
| 5 | **`data-net` + `obs-net` = `internal: true` always** | Security boundary | Data layer exposed publicly |
| 6 | **`.env` files NEVER committed to git** | Secrets via Docker `.txt` files only | Credential leak |
| 7 | **Commits: `feat:` `fix:` `docs:` `chore:` only** | Conventional commits, enforced by hooks | CI breaks, changelog corrupted |
| 8 | **Trivy target: 0 CRITICAL per image** | Security gate | Vulnerable images ship to prod |
| 9 | **Python indent: 4 spaces, NEVER 3, NEVER mixed** | Enforced by linter | Silent IndentationError crashes |
| 10 | **Redis: DB 1 = cache, DB 2 = rate limits — NEVER mix** | Rate limiter reads wrong DB | Rate limits silently disabled |
| 11 | **`hypercore` healthcheck uses `localhost` NOT `127.0.0.1`** | IPv6 resolution bug in container | Health check fails, restart loop |
| 12 | **Supabase ↔ V2.4 schemas NEVER merged** | Two separate DB concerns | Schema drift, migration conflicts |
| 13 | **Guardian moderation: ban/kick NEVER fully autonomous** | Phase 3c = veto-gated only | Innocent user banned without review |
| 14 | **NemoClaw/Guardian: bot detects, Core decides + persists, bot renders (One Door)** | Single source of truth | Duplicate actions, split state |
| 15 | **`monitoring/prometheus/prometheus.yml` = ACTIVE. Repo root = STALE** | Two files exist | Prometheus scrapes wrong targets |
| 16 | **`minio` on BOTH `data-net` AND `obs-net` — intentional, never "fix" it** | Serves both data + observability | Breaks minio connectivity |
| 17 | **Alembic: if `alembic_version` missing → `stamp <prev>` then `upgrade head`** | `create_all` built schema without Alembic state | Migration state corrupts |
| 18 | **Two socket proxies — NEVER merge** | Main = read-only · `healer` = CONTAINERS/POST/PING only | LLM gains write access to containers |
| 19 | **Memory limits on ALL services** | Agent X caused OOM crash Apr 17 | OOM cascade kills entire stack |
| 20 | **`make build` runs `pre-build-check.sh` first** | Aborts if <15GB free disk | OOM during build |
| 21 | **Use `docker compose -f docker-compose.yml` ALONE** — root already `include:`s everything | Passing extra `-f` files loads them twice | Double-load → silent no-op on `build`/`up` |
| 22 | **Dashboard healthcheck: `timeout ≥ 10s`, `start-period ≥ 90s`** | Next.js compiles on first request | Healthy app flagged `unhealthy` |

---

> 🔴 Sacred = non-negotiable. Surface violations immediately.
