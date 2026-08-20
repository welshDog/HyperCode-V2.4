# 🔌 agents-full.yml Container-Port Audit — 2026-08-20

> Full evidence for `docs/NEXT_TASKS.md` item #9. `docker-compose.agents-full.yml`
> maps every one of its 24 agents as `"127.0.0.1:<HOST>:8080"` — i.e. it assumes
> every agent's app listens on container port **8080**. This audit checked what
> port each agent's Dockerfile/base template actually binds to, by reading the
> Dockerfile's own `ENV`/`EXPOSE`/`HEALTHCHECK` (Docker's healthcheck runs *inside*
> the container against whatever port the app really uses — so a mismatched agent
> still reports "healthy" while being completely unreachable via its host-mapped port).
>
> **Update, later the same evening: the 17 port-mismatched agents below are now
> fixed** — each Dockerfile's baked port (and, for `tips-tricks-writer`, a
> hardcoded override in `agent.py` itself) changed to `8080` to match compose's
> uniform healthcheck. `business-agent` was already fixed in an earlier pass the
> same day. The 3 agents that can't even build are still open — this was a build-
> context path bug, not a port bug, and needs a path decision, not a port bake.

## Method

For each service: read its Dockerfile's `ENV AGENT_PORT=`/`ENV PORT=` (or the
app's own `os.getenv("AGENT_PORT", "<default>")` fallback when no `ENV` line
sets it), its `EXPOSE`, and its `HEALTHCHECK` target — these three should agree
with each other (they mostly do, per-agent) and with compose's expected `8080`
(they mostly don't). Confirmed `agents-full.yml` never overrides `AGENT_PORT`
via any service's own `environment:` block (`grep -n "AGENT_PORT"
docker-compose.agents-full.yml` → zero matches), so nothing at compose level
rescues a mismatched agent.

## ✅ Fine (21, was 4) — container port genuinely matches compose's `:8080`

| Agent | Evidence |
|---|---|
| `crew-orchestrator` | `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]` — hardcoded, `EXPOSE 8080`, healthcheck curls `8080` |
| `hyper-architect` | Node app, `ENV PORT=8080`, `EXPOSE 8080`, healthcheck curls `8080` |
| `test-agent` | Healthcheck already curls `8080` |
| `business-agent` | Fixed in an earlier pass the same day — `AGENT_PORT=8080` baked into the Dockerfile, verified live via `docker run` + `curl /health` |
| `project-strategist` | **Fixed this pass** — `ENV AGENT_PORT=8080` (was `8001`) |
| `coder-agent` | **Fixed this pass** — added `ENV AGENT_PORT=8080` (was defaulting to `8000` via `${AGENT_PORT:-8000}`, nothing set it); added `EXPOSE 8080` for consistency. `FROM agent-base:latest` confirmed present locally already (built from `agents/agent-base.Dockerfile`) — a build-order dependency, not currently broken. |
| `frontend-specialist` | **Fixed this pass** — `ENV AGENT_PORT=8080` (was `8002`) |
| `backend-specialist` | **Fixed this pass** — `ENV AGENT_PORT=8080` (was `8003`) |
| `database-architect` | **Fixed this pass** — `ENV AGENT_PORT=8080` (was `8004`) |
| `qa-engineer` | **Fixed this pass** — `ENV AGENT_PORT=8080` (was `8005`) |
| `devops-engineer` | **Fixed this pass** — `ENV AGENT_PORT=8080` (was `8006`) |
| `security-engineer` | **Fixed this pass** — `ENV AGENT_PORT=8080` (was `8007`) |
| `system-architect` | **Fixed this pass** — `ENV AGENT_PORT=8080` (was `8008`). Verified: `docker build` succeeded. |
| `agent-x` | **Fixed this pass** — `ENV AGENT_PORT=8080` (was `8000`) |
| `throttle-agent` | **Fixed this pass** — `CMD`'s hardcoded `--port` flag, `EXPOSE`, and healthcheck all changed to `8080` (was `8014`) |
| `super-hyper-broski-agent` | **Fixed this pass** — added `ENV PORT=8080` (was defaulting to `8015` via `main.py`'s `os.getenv("PORT", 8015)`, nothing set it); `EXPOSE`/healthcheck also fixed |
| `tips-tricks-writer` | **Fixed this pass** — `ENV AGENT_PORT=8080` added to the Dockerfile, **and** a hardcoded `config.port = 8009` override removed from `agent.py`'s `__main__` block (the Dockerfile fix alone would not have been enough — the Python code was overriding it back to `8009` regardless of the env var). Verified: `docker build` succeeded. |
| `hyper-split-agent` | **Fixed this pass** — `ENV PORT=8080` (was `8096`), `CMD`'s hardcoded `--port` flag also changed. Verified: `docker build` succeeded. |
| `session-snapshot` | **Fixed this pass** — `ENV PORT=8080` (was `8097`), `CMD`'s hardcoded `--port` flag also changed |
| `goal-keeper` | **Fixed this pass** — added `ENV AGENT_PORT=8080` (was defaulting to `8050` via `main.py`'s `os.getenv("AGENT_PORT", "8050")`, nothing set it); `EXPOSE`/healthcheck also added/fixed. Verified: `docker build` succeeded. |
| `coderabbit-webhook` | **Fixed this pass** — `ENV PORT=8080` (was `8000`); also fixed a stale `logger.info("...started on port 8000")` log message to report the real port dynamically |

Repo-wide grep across all 17 for any remaining non-`8080` `AGENT_PORT=`/`PORT=`/
`EXPOSE`/healthcheck/CMD-port reference came back empty after the fix.

## 🔴 Can't even build (3) — build-context path bug, same class as the `hypercode-mcp-server` phantom fixed earlier tonight

| Agent | Problem |
|---|---|
| `brain-agent` | `context: ./agents/brain` — this directory does not exist at all. `docker compose build` would fail immediately with no such context. |
| `hyper-observer` | `context: ./agents/hyper-agents`, `dockerfile: Dockerfile.observer` — no such file at that path. The real Dockerfile exists one level deeper: `agents/hyper-agents/observer/Dockerfile`. Once (if) the path is fixed, it *also* has a port mismatch: `ENV AGENT_PORT=8092`. |
| `hyper-worker` | Same shape as `hyper-observer`: real file at `agents/hyper-agents/worker/Dockerfile`, and once reachable, `ENV AGENT_PORT=8093` — also mismatched. |

## Tally

24 total — **21 fine (was 4), 3 still can't build.** 18 of the 24 have now been
fixed (`business-agent` earlier, 17 more this pass). This is independent of
`NEXT_TASKS.md` item #0 (the 14-name same-name-merge decision) — item #0 is
still the other open blocker, but the fleet is no longer double-blocked: only
`brain-agent`/`hyper-observer`/`hyper-worker` (build-context path bug) and
item #0 remain before a real launch is possible.
