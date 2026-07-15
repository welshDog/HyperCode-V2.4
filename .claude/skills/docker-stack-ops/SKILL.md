---
name: docker-stack-ops
description: Running, rebuilding, debugging, and inspecting the HyperCode V2.4 29-container Docker stack — compose ops, network topology (frontend-net/backend-net/agents-net/data-net/obs-net), agent ports (127.0.0.1:), health checks, log tailing, and the network-migrate script. Use when the user says "containers down", "compose up", "rebuild agents", "agent X not healthy", "redis/postgres connection", "network isolation", or hits any Docker stack issue.
---

# docker-stack-ops

The 29-container HyperCode V2.4 production stack. Five networks, strict isolation, all internal services bound to `127.0.0.1:`.

## Network Topology (Phase 10B — LIVE, never re-debate)

| Network | Type | Members |
|---|---|---|
| `frontend-net` | bridge, internet | dashboard, mission-ui, mcp-server |
| `backend-net` | bridge, internet | hypercode-core ONLY (bridges all layers) |
| `agents-net` | bridge, internet | all 25+ AI agents, LLM API calls |
| `data-net` | bridge, **internal: true** | redis, postgres, minio, chroma |
| `obs-net` | bridge, **internal: true** | prometheus, grafana, loki, tempo, promtail, alertmanager |

**Iron rule:** `data-net` + `obs-net` are NEVER exposed to internet. They are `internal: true`. Never change this.

## The Stack (29 containers)

```powershell
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"

# Bring it all up
docker compose up -d

# See everything (alphabetical)
docker compose ps

# Healthy check
docker compose ps --format "table {{.Name}}\t{{.Status}}"
```

Expected: 29 containers, all `Up (healthy)`. If any are `unhealthy` or `restarting`, that container's healthcheck is failing — read its logs.

## Common Ops

```powershell
# Restart one service (keeps others up)
docker compose restart <service-name>

# Rebuild ONE agent without cache (after Dockerfile change)
docker compose build --no-cache <service-name>
docker compose up -d <service-name>

# Rebuild ALL (Phase 9 security pattern: --no-cache --pull)
docker compose build --no-cache --pull
docker compose up -d

# Tail logs from one service
docker compose logs -f --tail 100 <service-name>

# Tail logs from ALL (use sparingly — noisy)
docker compose logs -f --tail 50

# Exec into a running container
docker compose exec <service-name> bash

# Run a one-off (e.g. Alembic migration)
docker compose exec api alembic upgrade head
```

## Network Migration (when topology changes)

`scripts/network-migrate.sh` recreates the networks safely. **Always dry-run first.**

```bash
# Preview only
bash scripts/network-migrate.sh --dry-run

# Apply
bash scripts/network-migrate.sh
```

Use it when: adding a new network, moving a service between networks, or recovering from a broken external network state.

## Agent Port Convention (127.0.0.1: bound — NEVER 0.0.0.0)

```
3100-3199 → Writing agents
3200-3299 → Code agents
3300-3399 → Data agents
3400-3499 → Discord agents
3500-3599 → Automation agents
```

Internal agent ports MUST be `127.0.0.1:<port>:<port>` in `docker-compose.yml` — never `0.0.0.0`. If an agent needs external exposure, route through `hypercode-core` or the MCP gateway.

## Health Check Patterns

Every service should have:

```yaml
healthcheck:
  test: ["CMD", "curl", "-fsS", "http://localhost:<port>/health"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 30s
```

If a service is `unhealthy`:
1. Check the service's `/health` endpoint manually (`docker compose exec <svc> curl -i http://localhost:<port>/health`)
2. Check service logs (`docker compose logs <svc>`)
3. Check dependencies — many services depend on redis/postgres being healthy first
4. Check env vars are wired (especially `.env` mounted into the container)

## Common Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `Cannot connect to Docker daemon` | Docker Desktop paused | Unpause via the whale menu (Windows tray) |
| `network <name> declared as external, but is not` | First-time stack startup | Run `docker network create app-net agents-net` then retry |
| Redis auth errors in agent logs | `REDIS_PASSWORD` not in container env | Confirm `env_file: .env` in compose, not just on host |
| Postgres "connection refused" | Postgres not yet healthy when agent started | Add `depends_on: postgres: condition: service_healthy` |
| `docker compose ps` shows agent on wrong network | Manually moved network, compose state drifted | `docker compose down && bash scripts/network-migrate.sh && docker compose up -d` |
| Logs empty on fresh boot | Normal — Redis `hypercode:logs` populates as agents do work | Trigger an agent action then re-tail |
| `docker socket` permission errors in healer/coder/05-devops | Wrong docker package | Use `docker-ce-cli` not `docker.io` (Phase 9 fix) |

## Bring It All Down (clean shutdown)

```powershell
# Stops + removes containers, keeps volumes (data persists)
docker compose down

# Nuclear: stops + removes containers AND volumes (DATA LOSS)
# Only use when wiping a dev environment intentionally
docker compose down -v
```

**Never `docker compose down -v` on prod or shared dev** without explicit confirmation. Volumes hold Postgres data, Redis state, Grafana dashboards, MinIO objects.

## Inspect Without Touching

```powershell
# Validate compose syntax
docker compose config

# See what an env var resolves to (after .env interpolation)
docker compose config | Select-String "<VAR_NAME>"

# Inspect a network
docker network inspect <network-name>

# See what a service exposes
docker compose port <service-name> <internal-port>
```

## Companion Skills

- `phase-10-tracker` — which phase wired what
- `cve-trivy-scan` — image vulnerability scanning
- `otlp-tempo-tracing` — distributed tracing across the stack
- `stripe-webhook-handler` — `/api/stripe/webhook` route specifics

## Hard Rules

- **NEVER expose `data-net` or `obs-net` to internet** — they are `internal: true` (Phase 10B)
- **NEVER bind agent ports to `0.0.0.0`** — always `127.0.0.1:<port>:<port>`
- **NEVER `docker compose down -v`** on shared environments without confirmation
- **NEVER skip `--no-cache --pull`** in security-critical builds (Phase 9)
- **NEVER mix `docker.io` and `docker-ce-cli`** in docker-socket agents — use `docker-ce-cli` only
