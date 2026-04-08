# 🚀 HyperCode V2.0 Startup & Dependency Documentation

**Date**: 2026-03-08
**Status**: Automated Startup Sequence Implemented

## 1. Startup Sequence (Dependency Order)

The system initializes in the following strict order to ensure stability:

### Phase 1: Infrastructure (The Foundation)
1.  **Redis** (`redis:7-alpine`): The nervous system. Must be up first for Pub/Sub.
2.  **PostgreSQL** (`postgres:15-alpine`): The long-term memory.
3.  **MinIO** (`minio`): Object storage for artifacts.
4.  **Observability Stack**: `prometheus`, `grafana`, `cadvisor`, `node-exporter`.

### Phase 2: Core Services (The Brain)
5.  **HyperCode Core** (`hypercode-core`): Connects to Redis/PG. The API Gateway.
6.  **Healer Agent** (`healer-agent`): Connects to Core/Redis. Monitors the fleet.
7.  **Crew Orchestrator** (`crew-orchestrator`): Manages agent lifecycles.

### Phase 3: Specialized Agents (The Crew)
8.  **Tips Architect** (`tips-tricks-writer`): Documentation specialist.
9.  **Project Strategist** (`project-strategist-v2`): Planning.
10. **BROski Bot** (`broski-bot`): Discord interface.
11. **Celery Worker**: Background task processing.

## 2. Health Check Dependencies

- **Healer Agent** depends on `redis` and `docker.sock`.
- **Core** depends on `redis` and `postgres`.
- **Agents** depend on `core` (for API) and `redis` (for Pub/Sub).

## 3. Automation Script (`scripts/start_hypercode_v2.ps1`)

This PowerShell script handles the entire lifecycle:
1.  **Daemon Check**: Verifies Docker Desktop is running.
2.  **Zombie Cleanup**: Removes stopped containers matching `hypercode*`.
3.  **Build & Up**: Runs `docker compose up -d --build --remove-orphans`.
4.  **Health Loop**: Polls `docker inspect` for `healthy` status on critical services (60s timeout).
5.  **Verification**: Checks network presence and prints access URLs.

## 4. Troubleshooting

If startup fails:
- **Core Exits**: Check `docker logs hypercode-core`. Usually a DB connection issue or missing env var.
- **Healer Unhealthy**: Check `docker logs healer-agent`. Likely a Redis connection failure.
- **Tips Architect Missing**: Ensure `docker-compose.yml` profiles includes `agents` or it's explicitly enabled.

## 5. Next Steps
- Verify `localhost:3001` for Grafana dashboards.
- Check `localhost:8088` for Mission Control.
- Run `python agents/healer/validator.py` for a deep sweep.
