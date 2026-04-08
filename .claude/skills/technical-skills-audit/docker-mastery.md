# 🐳 Docker & Compose Mastery — HyperCode V2.0

## Compose File Strategy

HyperCode uses a **multi-file overlay strategy**:

```bash
# Full production stack
docker compose up -d

# Dev with hot reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Agents only (fast boot)
docker compose -f docker-compose.agents.yml up -d

# Lightweight (Raspberry Pi / low RAM)
docker compose -f docker-compose.agents-lite.yml up -d

# With full observability
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# MCP gateway enabled
docker compose -f docker-compose.yml -f docker-compose.mcp-gateway.yml up -d

# Windows (path adjustments)
docker compose -f docker-compose.windows.yml up -d
```

## Core Dockerfiles

| File | Purpose |
|---|---|
| `Dockerfile.production` | Optimised multi-stage prod build |
| `Dockerfile.builder` | CI/CD build stage image |
| `Dockerfile.agents-test` | Agent integration test runner |

## Service Boot Order

Critical: services must start in this order:
1. `redis` → 2. `postgres` → 3. `hypercode-core` → 4. agents → 5. dashboard

Health checks enforce this via `depends_on` with `condition: service_healthy`.

## Common Debug Commands

```bash
# Check all running containers
docker ps

# Tail logs for a service
docker compose logs -f hypercode-core

# Restart a single service
docker restart hypercode-core

# Exec into a container
docker exec -it hypercode-core bash

# Check network connectivity
docker network ls
docker network inspect hypercode_default
```

## Port Reference

| Port | Service |
|---|---|
| 3000 | BROski Terminal |
| 3001 | Grafana |
| 5432 | PostgreSQL |
| 6379 | Redis |
| 8000 | HyperCode Core API |
| 8008 | Healer Agent |
| 8080 | Agent X |
| 8081 | Crew Orchestrator |
| 8088 | Mission Control Dashboard |
| 9090 | Prometheus |
