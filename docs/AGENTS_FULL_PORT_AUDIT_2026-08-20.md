# 🔌 agents-full.yml Container-Port Audit — 2026-08-20

> Full evidence for `docs/NEXT_TASKS.md` item #9. `docker-compose.agents-full.yml`
> maps every one of its 24 agents as `"127.0.0.1:<HOST>:8080"` — i.e. it assumes
> every agent's app listens on container port **8080**. This audit checked what
> port each agent's Dockerfile/base template actually binds to, by reading the
> Dockerfile's own `ENV`/`EXPOSE`/`HEALTHCHECK` (Docker's healthcheck runs *inside*
> the container against whatever port the app really uses — so a mismatched agent
> still reports "healthy" while being completely unreachable via its host-mapped port).
>
> Nothing in this file was fixed as part of this audit — see `NEXT_TASKS.md` item #9
> for status. `business-agent` was already fixed in an earlier pass the same day.

## Method

For each service: read its Dockerfile's `ENV AGENT_PORT=`/`ENV PORT=` (or the
app's own `os.getenv("AGENT_PORT", "<default>")` fallback when no `ENV` line
sets it), its `EXPOSE`, and its `HEALTHCHECK` target — these three should agree
with each other (they mostly do, per-agent) and with compose's expected `8080`
(they mostly don't). Confirmed `agents-full.yml` never overrides `AGENT_PORT`
via any service's own `environment:` block (`grep -n "AGENT_PORT"
docker-compose.agents-full.yml` → zero matches), so nothing at compose level
rescues a mismatched agent.

## ✅ Fine (4) — container port genuinely matches compose's `:8080`

| Agent | Evidence |
|---|---|
| `crew-orchestrator` | `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]` — hardcoded, `EXPOSE 8080`, healthcheck curls `8080` |
| `hyper-architect` | Node app, `ENV PORT=8080`, `EXPOSE 8080`, healthcheck curls `8080` |
| `test-agent` | Healthcheck already curls `8080` |
| `business-agent` | Fixed earlier the same day — `AGENT_PORT=8080` baked into the Dockerfile, verified live via `docker run` + `curl /health` |

## 🔴 Port-mismatched (17) — builds fine, but the app binds to its own old port, not 8080

Every one of these bakes its **pre-reconciliation host port** as its internal
bind port — strong evidence these Dockerfiles predate `agents-full.yml`
standardizing on `HOST:8080`, and were never updated when that convention landed.

| Agent | Actual bind port | Source |
|---|---|---|
| `project-strategist` | 8001 | `ENV AGENT_PORT=8001` |
| `coder-agent` | 8000 (default) | healthcheck: `${AGENT_PORT:-8000}`, no `ENV AGENT_PORT` set — also `FROM agent-base:latest`, a locally-built base image (`agents/agent-base.Dockerfile`); present locally already, but a build-order dependency worth knowing about |
| `frontend-specialist` | 8002 | `ENV AGENT_PORT=8002` |
| `backend-specialist` | 8003 | `ENV AGENT_PORT=8003` |
| `database-architect` | 8004 | `ENV AGENT_PORT=8004` |
| `qa-engineer` | 8005 | `ENV AGENT_PORT=8005` |
| `devops-engineer` | 8006 | `ENV AGENT_PORT=8006` |
| `security-engineer` | 8007 | `ENV AGENT_PORT=8007` |
| `system-architect` | 8008 | `ENV AGENT_PORT=8008` (found in the original port-collision pass) |
| `agent-x` | 8000 | `ENV AGENT_PORT=8000` |
| `throttle-agent` | 8014 | healthcheck curls `8014` |
| `super-hyper-broski-agent` | 8015 | healthcheck curls `8015` |
| `tips-tricks-writer` | 8000 (default) | `base_agent.py`'s own default, no `ENV AGENT_PORT` set — Dockerfile healthchecks `8009` (a *fourth*, separate value — three-way disagreement, not just two) |
| `hyper-split-agent` | 8096 | healthcheck curls `8096` |
| `session-snapshot` | 8097 | healthcheck curls `8097` |
| `goal-keeper` | 8050 (default) | `main.py`: `os.getenv("AGENT_PORT", "8050")`, no `ENV AGENT_PORT` set in the Dockerfile |
| `coderabbit-webhook` | 8000 | `ENV PORT=8000`, healthcheck curls `8000` |

## 🔴 Can't even build (3) — build-context path bug, same class as the `hypercode-mcp-server` phantom fixed earlier tonight

| Agent | Problem |
|---|---|
| `brain-agent` | `context: ./agents/brain` — this directory does not exist at all. `docker compose build` would fail immediately with no such context. |
| `hyper-observer` | `context: ./agents/hyper-agents`, `dockerfile: Dockerfile.observer` — no such file at that path. The real Dockerfile exists one level deeper: `agents/hyper-agents/observer/Dockerfile`. Once (if) the path is fixed, it *also* has a port mismatch: `ENV AGENT_PORT=8092`. |
| `hyper-worker` | Same shape as `hyper-observer`: real file at `agents/hyper-agents/worker/Dockerfile`, and once reachable, `ENV AGENT_PORT=8093` — also mismatched. |

## Tally

24 total — 4 fine, 17 port-mismatched, 3 can't build. Only `business-agent`
(1 of the 24) has been fixed. This is independent of `NEXT_TASKS.md` item #0
(the 14-name same-name-merge decision) — fixing item #0 alone would still leave
20 of 24 agents either failing to build or unreachable via their host port.
