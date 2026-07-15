# LOOP_CONTEXT.md — HyperCode-V2.4
> Claude reads this before every loop on this repo.

---

## Stack
- Docker (docker-ce-cli ONLY — never docker.io)
- FastAPI — main platform API
- Python 3.10 — 4 space indent, never 3
- Redis — DB1=cache, DB2=rate limits, NEVER mix
- PostgreSQL, Prometheus, Grafana, Celery, Ollama, Chroma

## Container Count
~30–40 containers running (profile-dependent); 80+ services defined across 20+ compose files

## Key Ports
| Service | Port |
|---|---|
| FastAPI core | 8000 |
| Grafana | 3001 |
| Agent dashboard | 8088 |
| Prometheus | 9090 |
| Brain engine | 8100 |
| Safety Shepherd | 8096 |
| Agent Registry | 8077 |
| Evolve relay (pets) | 8097 |

## Active Profiles
`core` · `agents` · `pets` · `brain` · `brain-agents` · `discord` · `safety` · `registry` · `observability` · `health` · `vault-sync`
> Canonical obs profile is `observability` (observability.yml), NOT `obs`/`monitoring.yml`.

## Health Score
🟢 Healthy (2026-06-22 live truth). AGENT-START roadmap P0-1 → P2-4 CLOSED; migrations advanced 015 → 018.

## Networks
`backend-net` · `data-net` · `agents-net` · `obs-net` · `frontend-net`

## Key Files
- `CLAUDE.md` — identity + sacred rules
- `WHATS_DONE.md` — never rebuild anything here
- `CLAUDE_CONTEXT.md` — extended context

## Sacred Rules for This Repo
- Always `docker-ce-cli` never `docker.io`
- `git fetch` before ANY push — auto-commits are running
- `from app.X import Y` never `from backend.app.X`
- Never commit .env files
