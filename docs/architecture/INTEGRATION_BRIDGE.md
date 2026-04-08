# HyperCode Integration Bridge

## Overview
Unified platform co-running HyperCode Core and the 8-agent Crew with shared Redis and PostgreSQL, automatic agent registration, mission lifecycle tracking, and monitoring via Prometheus/Grafana/Jaeger.

## Topology
- Core API: http://localhost:8000
- Crew Orchestrator: http://localhost:8080
- Dashboard: http://localhost:8090
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Jaeger: http://localhost:16686

## Environment Variables
- Core:
  - HYPERCODE_REDIS_URL=redis://redis:6379/0
  - HYPERCODE_DB_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/hypercode
  - ENVIRONMENT=staging
  - OTLP_EXPORTER_DISABLED=false
  - OTLP_ENDPOINT=http://jaeger:4318/v1/traces
- Agents:
  - REDIS_URL=redis://redis:6379
  - CORE_URL=http://hypercode-core:8000
  - AGENT_HEALTH_URL=http://<agent-name>:<port>/health

## Auto-Registration & Heartbeat
Agents register with Core at startup and send heartbeat every 30s to `/agents/heartbeat`.

## Strategy → Mission Bridge
Project Strategist maps plan outputs to Core mission submissions at `/orchestrator/mission` with requirements inferred from assigned specialists.

## Deployment
```bash
./scripts/start-platform.sh  # Linux/Mac
.\u005Cscripts\start-platform.bat  # Windows
```

## Monitoring
- Grafana loads dashboards from `HyperCode-V2.0/monitoring/grafana/dashboards`.
- Prometheus uses rules under `HyperCode-V2.0/monitoring/prometheus`.

## Zero-Downtime & Scalability
- Services use restart policies and health checks.
- Horizontal scaling supported via `docker compose up --scale <service>=N`.

