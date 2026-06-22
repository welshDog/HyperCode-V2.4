# LOOP_SERVICES.md — HyperCode-V2.4 Service Map
> Claude uses this to verify services after every container loop.

---

## Always-On Services (core profile)

| Service | Port | Healthcheck URL | Depends On |
|---|---|---|---|
| hypercode-core | 8000 | http://localhost:8000/health | postgres, redis |
| redis | 6379 | docker exec redis redis-cli ping | — |
| postgres | 5432 | docker exec postgres pg_isready | — |
| ollama | 11434 | http://localhost:11434/api/tags | — |
| celery-worker | — | celery inspect ping | redis |
> ⚠️ celery-worker has been caught sitting in `Created` (never started). If a loop needs it, verify it's `Up`, not just present: `docker start celery-worker`.

## Agent Profile Services (--profile agents)

| Service | Port | Notes |
|---|---|---|
| mcp-gateway | 8090 | MCP server for Claude agent bridge |
| agent-dashboard | 8088 | Agent swarm overview |
| 15x agents | various | See docker-compose.agents.yml |

## Safety / Governance / Registry

| Service | Port | Profile | Notes |
|---|---|---|---|
| safety-shepherd | 8096 | safety | ALLOW/BLOCK/ESCALATE policy brain (agents-net + data-net) |
| agent-registry | 8077 | registry | auto-restart + circuit breaker |
| evolve-relay | 8097 | pets | dNFT evolve mint relay (Base Sepolia) |

## Observability (--profile observability)
> Canonical compose is `observability.yml`, NOT `monitoring.yml`/`obs`.

| Service | Port |
|---|---|
| prometheus | 9090 |
| grafana | 3001 |
| loki | 3100 |

## Smoke Test Command
```bash
curl http://localhost:8000/health
curl http://localhost:8100/health  # Brain engine
curl http://localhost:9090/-/ready # Prometheus
```
