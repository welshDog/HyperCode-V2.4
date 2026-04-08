# ⚡ HyperCode Quick Reference

## Port Map

```
Core Services:
  8000  → hypercode-core (API)
  5432  → postgres (database)
  6379  → redis (cache)
  11434 → hypercode-ollama (LLM)

Agents:
  8001  → project-strategist
  8002  → coder-agent
  8003  → backend-specialist
  8004  → database-architect
  8005  → qa-engineer
  8006  → devops-engineer
  8007  → security-engineer
  8008  → system-architect
  8009  → tips-tricks-writer (mapped to 8011)
  8010  → healer-agent ← Intelligence layer
  8012  → frontend-specialist
  8013  → test-agent
  8014  → throttle-agent
  8015  → super-hyper-broski-agent
  8081  → crew-orchestrator (workflows)
  8089  → coderabbit-webhook (Phase 2)

Observability:
  3001  → grafana (dashboards)
  9090  → prometheus (metrics)
  3100  → loki (logs)
  8090  → cadvisor (container metrics)
  9100  → node-exporter (system metrics)
  8009  → chroma (vector DB)
  9001  → minio (storage UI)
  9000  → minio (API)
```

## Health Checks

```bash
# All services
docker compose ps

# Specific checks
curl http://127.0.0.1:8000/health       # Core
curl http://127.0.0.1:8010/health       # Healer (Intelligence!)
curl http://127.0.0.1:8081/health       # Orchestrator (Workflows!)
curl http://127.0.0.1:3001/api/health   # Grafana
curl http://127.0.0.1:9090/-/healthy    # Prometheus

# Database
docker exec postgres pg_isready -U postgres

# Cache
redis-cli ping
```

## Common Commands

```bash
# Start/stop everything
docker compose up -d
docker compose down

# View logs
docker compose logs SERVICE_NAME --tail 50 -f

# Rebuild service
docker compose build SERVICE_NAME --no-cache
docker compose up SERVICE_NAME -d

# Enter container
docker exec -it SERVICE_NAME /bin/bash

# Scale service
docker compose up -d --scale SERVICE_NAME=3

# Health check
docker compose ps | grep healthy
```

## Phase 1 Features

```bash
# Metrics
curl http://127.0.0.1:8010/metrics   # Healer
curl http://127.0.0.1:8013/metrics   # Test-agent

# Rate limiting
for i in {1..150}; do curl http://127.0.0.1:8013/; done
# After 100 requests: 429 (Too Many Requests)

# Caching
curl http://127.0.0.1:8013/test/cached-endpoint?query=test  # First: slow
curl http://127.0.0.1:8013/test/cached-endpoint?query=test  # Second: cached (fast)

# Circuit breaker
docker compose stop test-agent
curl http://127.0.0.1:8013/test/circuit-breaker  # Fast fail (open circuit)
sleep 60
docker compose start test-agent
curl http://127.0.0.1:8013/test/circuit-breaker  # Recovers
```

## Phase 2 Intelligence

```bash
# Load life-plans
curl http://127.0.0.1:8010/life-plan/healer-agent | jq .

# Get failure modes
curl http://127.0.0.1:8010/failure-modes/hypercode-core | jq .

# Get SLOs
curl http://127.0.0.1:8010/slos/hypercode-core | jq .

# AI Diagnosis
curl -X POST http://127.0.0.1:8010/diagnose \
  -H "Content-Type: application/json" \
  -d '{"agent_name":"test-agent","symptoms":["Connection refused","Port unreachable"]}'

# Get playbook
curl http://127.0.0.1:8010/playbook/healer-agent/alert_service_unhealthy | jq .

# All metrics to monitor
curl http://127.0.0.1:8010/all-metrics | jq .
```

## Workflow Execution

```bash
# Submit workflow
curl -X POST http://127.0.0.1:8081/workflow/execute \
  -H "X-API-Key: $(grep API_KEY .env | cut -d= -f2)" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Workflow",
    "parallel": false,
    "steps": [
      {
        "id": "step-1",
        "agent_type": "test-agent",
        "task_description": "Run health check",
        "timeout_seconds": 60
      }
    ]
  }'

# Check status
curl http://127.0.0.1:8081/workflow/test-workflow-1 \
  -H "X-API-Key: $(grep API_KEY .env | cut -d= -f2)"

# List workflows
curl http://127.0.0.1:8081/workflows \
  -H "X-API-Key: $(grep API_KEY .env | cut -d= -f2)"
```

## CodeRabbit Integration

```bash
# Simulate webhook
curl -X POST http://127.0.0.1:8089/webhook/coderabbit \
  -H "Content-Type: application/json" \
  -d '{
    "event": "review_completed",
    "pr": {
      "number": 42,
      "repo": "owner/repo",
      "branch": "feature/new-api"
    },
    "review": {
      "critical_issues": [
        {"type": "backend", "description": "Missing error handling"},
        {"type": "security", "description": "SQL injection risk"}
      ]
    }
  }'

# Check webhook status
curl http://127.0.0.1:8089/health
```

## Monitoring

```bash
# Prometheus queries
curl 'http://127.0.0.1:9090/api/v1/query?query=up'
curl 'http://127.0.0.1:9090/api/v1/query?query=rate(requests_total[5m])'

# Grafana
# UI: http://127.0.0.1:3001 (admin/admin)

# Loki logs
curl 'http://127.0.0.1:3100/loki/api/v1/query?query={job="healer-agent"}'

# Check Redis cache
redis-cli
> info stats
> keys *
> get key_name
```

## Troubleshooting

```bash
# If Postgres unhealthy
docker compose restart postgres
sleep 10
docker compose restart celery-worker celery-exporter hyper-mission-api dashboard

# If test-agent keeps restarting
docker compose logs test-agent --tail 100
docker compose build test-agent --no-cache
docker compose up test-agent -d

# If metrics not showing
docker compose ps | grep healthy  # Check all are healthy
curl http://127.0.0.1:8010/metrics  # Verify endpoint works
# Update prometheus.yml scrape targets
curl -X POST http://127.0.0.1:9090/-/reload  # Reload config

# If workflow doesn't execute
curl http://127.0.0.1:8081/health  # Check orchestrator
redis-cli ping  # Check Redis
docker compose logs crew-orchestrator --tail 100
```

## Files to Know

```
HyperCode-V2.0/
├── .env                           # Secrets & config
├── docker-compose.yml             # Main definition
├── docker-compose.agents-lite.yml # Minimal profile
├── STATUS_REPORT.md               # Current status
├── PHASE_2_COMPLETE.md            # Phase 2 reference
├── PHASE_2_INTEGRATION.md         # Integration guide
├── VISION_AND_METRICS.md          # Strategy & KPIs
├── BLOCKERS_FIXED.md              # What was fixed
├── agents/
│   ├── healer/
│   │   ├── life_plans.py          # Load YAML life-plans
│   │   ├── ai_diagnostics.py      # Claude/Perplexity integration
│   │   ├── intelligence_endpoints.py  # API endpoints
│   │   └── life-plans/            # Agent YAML plans
│   ├── crew-orchestrator/
│   │   ├── workflow_engine.py     # Multi-agent workflows
│   │   └── main.py                # Orchestration logic
│   ├── coderabbit-webhook/        # Agent #11 (new)
│   │   ├── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── test-agent/
│   │   ├── main.py                # Phase 1 features demo
│   │   ├── requirements.txt       # Redis, Prometheus, Anthropic
│   │   └── Dockerfile
│   └── shared/
│       └── agent_utils.py         # Phase 1: Metrics, cache, limiter, breaker
├── life-plans/                    # YAML knowledge base
│   ├── healer-agent.yaml
│   ├── hypercode-core.yaml
│   ├── backend-specialist.yaml
│   └── ...13 total
└── monitoring/
    ├── prometheus/prometheus.yml
    └── grafana/provisioning/
```

## Environment Variables to Set

```bash
# .env file
API_KEY=sk_live_...
HYPERCODE_JWT_SECRET=...
POSTGRES_PASSWORD=...
PERPLEXITY_API_KEY=...  # For AI diagnostics
OPENAI_API_KEY=...      # For fallback
ANTHROPIC_API_KEY=...   # For Claude (preferred)
CODERABBIT_WEBHOOK_SECRET=...  # For webhook auth
```

## One-Liner Health Check

```bash
docker compose ps | grep -c "healthy"  # Should be ≥ 12
```

## Emergency Restart (Everything)

```bash
docker compose down -v
docker compose up -d
sleep 30
docker compose ps
```

## Next Steps

1. **Week 1:** Enable Phase 1 metrics (30 min)
2. **Week 2:** Test CodeRabbit integration (2 hours)
3. **Week 3:** Build Grafana dashboards (1 hour)
4. **Week 4:** Deploy to Kubernetes (Phase 3)

---

**Quick Tip:** Always check `docker compose ps` first. 90% of issues are simply unhealthy services needing restart.

