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
48 Docker containers across ~22 compose files

## Key Ports
| Service | Port |
|---|---|
| FastAPI core | 8000 |
| Grafana | 3001 |
| Agent dashboard | 8088 |
| Prometheus | 9090 |
| Brain engine | 8100 |

## Active Profiles
`core` · `agents` · `pets` · `brain` · `discord` · `obs` · `health`

## Health Score
8.8/10 (last audit May 2026)

## Networks
`backend-net` · `data-net` · `agents-net` · `obs-net` · `frontend-net`

## Key Files
- `CLAUDE.md` — identity + sacred rules
- `WHATSDONE.md` — never rebuild anything here
- `CLAUDECONTEXT.md` — extended context

## Sacred Rules for This Repo
- Always `docker-ce-cli` never `docker.io`
- `git fetch` before ANY push — auto-commits are running
- `from app.X import Y` never `from backend.app.X`
- Never commit .env files
