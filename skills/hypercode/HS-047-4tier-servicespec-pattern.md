# HS-047 — 4-Tier ServiceSpec Launch Pattern

> **Extracted from:** `hyperlaunch.py` · HyperCode-V2.4
> **What it is:** The architecture pattern for declaring + ordering services in a multi-tier stack

---

## The 4 Tiers

| Tier | Name | What Goes Here | Must Be Healthy Before... |
|---|---|---|---|
| **INFRA** | Infrastructure | Redis, Postgres | Everything else |
| **CORE** | Core Platform | hypercode-core, crew-orchestrator, healer-agent | Agents + UI |
| **AGENTS** | AI Agents | agent-x, hyper-architect, hyper-worker, devops-engineer | UI |
| **UI** | Dashboards | hypercode-dashboard, broski-bot, grafana | Nothing (non-critical) |

## ServiceSpec Dataclass

```python
@dataclass
class ServiceSpec:
    name: str           # Docker Compose service name
    container: str      # Docker container name
    tier: Tier          # INFRA / CORE / AGENTS / UI
    port: Optional[int] # Primary HTTP port (None = no HTTP)
    health_path: str    # Health check endpoint (default: "/health")
    critical: bool      # If True, abort launch on failure
    depends_on: list    # Service names this depends on
    startup_timeout: int # Seconds to wait for healthy
    description: str
```

## Current Service Map

### TIER 1 — INFRA
```
redis       → port 6379  (TCP only)  • state sync + pub/sub backbone
postgres    → port 5432  (TCP only)  • persistent agent state + logs
```

### TIER 2 — CORE
```
crew-orchestrator  → port 8081  • agent lifecycle manager
healer-agent       → port 8008  • self-healing + auto-recovery
hypercode-core     → port 8000  • FastAPI backbone + integrations hub
```

### TIER 3 — AGENTS
```
agent-x            → port 8080  • Meta-Architect, spawns + evolves all agents
hyper-architect    → port 8091  • system design agent
hyper-observer     → port 8092  • real-time metrics + alerting
hyper-worker       → port 8093  • background task execution
devops-engineer    → port 8085  • CI/CD + autonomous evolution
```

### TIER 4 — UI (non-critical)
```
hypercode-dashboard → port 8088  • Mission Control — Next.js real-time UI
broski-bot          → port 3000  • BROski Terminal — CLI + web UI
grafana             → port 3001  • observability dashboards
```

## Critical vs Non-Critical

- **`critical: True`** — failure aborts the entire tier and all subsequent tiers
- **`critical: False`** — failure logged but launch continues (UI tier is all non-critical)

---

> 🏛️ Layer the stack like a building — foundations before floors before furniture.
