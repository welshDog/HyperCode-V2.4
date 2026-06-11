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

## Agent Profile Services (--profile agents)

| Service | Port | Notes |
|---|---|---|
| mcp-gateway | 8090 | MCP server for Claude agent bridge |
| agent-dashboard | 8088 | Agent swarm overview |
| 15x agents | various | See docker-compose.agents.yml |

## Observability (--profile obs)

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
