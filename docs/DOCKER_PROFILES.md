# Docker Compose Profiles — Which File Does What

> TL;DR: Use `docker-compose.yml` + `docker-compose.secrets.yml` for everything production-grade.
> Add extra files with `-f` when you need a specific mode.

---

## The Main Files

| File | Purpose | When to use |
|---|---|---|
| `docker-compose.yml` | Full production stack — all 29 core services | Default. Always use this as the base. |
| `docker-compose.secrets.yml` | Injects Docker secrets from `secrets/*.txt` | Always pair with the main file in production |

```bash
# Standard production start (always this):
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
```

---

## Dev & Local Modes

| File | Purpose | When to use |
|---|---|---|
| `docker-compose.dev.yml` | Local dev overrides — hot-reload, dev ports, relaxed auth | Day-to-day local development |
| `docker-compose.agents-lite.yml` | Minimal agents subset | Quick agent test without full stack |

```bash
# Local dev:
docker compose -f docker-compose.dev.yml up -d

# Dev + secrets:
docker compose -f docker-compose.yml -f docker-compose.secrets.yml -f docker-compose.dev.yml up -d
```

---

## Agents Stacks

| File | Purpose | When to use |
|---|---|---|
| `docker-compose.agents.yml` | Full agents stack (all 25+ agents) | Run all specialist agents |
| `docker-compose.hyper-agents.yml` | Hyper-agent stack with orchestrator | Full autonomous agent crew |

```bash
# Full hyper-agents stack:
docker compose -f docker-compose.hyper-agents.yml up -d

# Or via Makefile:
make agents
```

---

## Observability & Monitoring

| File | Purpose | When to use |
|---|---|---|
| `docker-compose.monitoring.yml` | Prometheus + Grafana + Loki + Tempo | Standalone observability stack |
| `docker-compose.grafana-cloud.yml` | Remote Grafana Cloud push mode | When pushing metrics to Grafana Cloud |
| `docker-compose.hyperhealth.yml` | HyperHealth API + health monitoring services | Dedicated health monitoring layer |

```bash
# Standalone monitoring:
docker compose -f docker-compose.monitoring.yml up -d
```

---

## Experimental / Minimal

| File | Purpose | When to use |
|---|---|---|
| `docker-compose.nano.yml` | Minimal lightweight stack | Low-resource / quick demo |
| `docker-compose.nim.yml` | NVIDIA NIM / GPU inference mode | GPU-accelerated LLM (experimental) |
| `docker-compose.demo.yml` | Demo-safe stack | Public demos / screenshots |
| `docker-compose.mcp-gateway.yml` | MCP gateway standalone | MCP IDE integration testing |
| `docker-compose.external-net.yml` | External network bridge | Connect to external Docker networks |
| `docker-compose.windows.yml` | Windows-specific overrides | Windows Docker Desktop quirks |

---

## Config Notes

- **Active Prometheus config:** `monitoring/prometheus/prometheus.yml` — ALWAYS edit this one
- **Root `prometheus.yml`:** STALE/UNUSED — do not edit
- **Secrets folder:** `secrets/*.txt` — gitignored, never committed
- **`.env.example`:** Copy to `.env` and fill in API keys before first run

---

## Quick Reference

```bash
# Everything on (standard):
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d

# Optional AI backend (separate image with AI dependencies):
docker compose --profile ai up -d

# Check all containers:
docker ps --format "table {{.Names}}\t{{.Status}}"

# Stop everything:
docker compose down

# Rebuild one service:
docker compose -f docker-compose.yml build --no-cache <service-name>
docker compose -f docker-compose.yml up -d --no-deps <service-name>
```
