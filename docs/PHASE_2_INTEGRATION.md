# Phase 2 Integration Guide

## Quick Start: Get Phase 2 Running in 15 Minutes

### Step 1: Update Healer Agent (2 min)

Add to `agents/healer/main.py` (top level):

```python
# Add imports
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from life_plans import LifePlansLoader
from ai_diagnostics import AIDiagnostics
from intelligence_endpoints import add_intelligence_endpoints

# In the startup function, add:
@app.on_event("startup")
async def startup():
    # ... existing code ...
    
    # Load life-plans
    global life_plans_loader, ai_diagnostics
    life_plans_loader = LifePlansLoader("/app/../life-plans")
    life_plans_loader.load_all()
    logger.info(f"Loaded {len(life_plans_loader.plans)} life-plans")
    
    # Initialize AI diagnostics
    ai_diagnostics = AIDiagnostics(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        perplexity_api_key=os.getenv("PERPLEXITY_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Add intelligence endpoints
    add_intelligence_endpoints(app, life_plans_loader, ai_diagnostics)
    logger.info("Intelligence endpoints loaded")
```

### Step 2: Update Crew Orchestrator (2 min)

Add to `agents/crew-orchestrator/main.py`:

```python
# Add import
from workflow_engine import add_workflow_endpoints

# In startup (after Redis connected):
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing startup code ...
    
    # Add workflow endpoints
    add_workflow_endpoints(app, redis_client, settings)
    logger.info("Workflow engine initialized")
    
    yield
    # ... shutdown code ...
```

### Step 3: Build & Deploy CodeRabbit Agent (3 min)

```bash
cd ./HyperCode-V2.0/agents/coderabbit-webhook

# Build
docker build -t coderabbit-webhook:latest .

# Add to docker-compose.yml:
cat >> docker-compose.yml << 'EOF'

  coderabbit-webhook:
    build: ./agents/coderabbit-webhook
    container_name: coderabbit-webhook
    ports:
      - "8089:8000"
    environment:
      - ORCHESTRATOR_URL=http://crew-orchestrator:8080
      - CORE_URL=http://hypercode-core:8000
      - CODERABBIT_WEBHOOK_SECRET=${CODERABBIT_WEBHOOK_SECRET:-}
    depends_on:
      - crew-orchestrator
    networks:
      - backend-net
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
EOF

# Start
docker compose up coderabbit-webhook -d
```

### Step 4: Rebuild Healer (5 min)

```bash
cd ./HyperCode-V2.0

# Rebuild with updated requirements
docker compose build healer-agent --no-cache
docker compose up healer-agent -d

# Wait for health check
sleep 10
docker compose logs healer-agent | tail -20
```

### Step 5: Verify Phase 2 (3 min)

```bash
# 1. Check healer intelligence
curl http://127.0.0.1:8010/health
curl http://127.0.0.1:8010/all-metrics

# 2. Test diagnostics
curl -X POST http://127.0.0.1:8010/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "hypercode-core",
    "symptoms": ["Connection refused"]
  }'

# 3. Check workflow engine
curl http://127.0.0.1:8081/

# 4. Check CodeRabbit webhook
curl http://127.0.0.1:8089/health
```

---

## Testing Phase 2 Features

### Test 1: Failure Mode Matching

```bash
curl http://127.0.0.1:8010/failure-modes/healer-agent | jq .
```

**Expected:** Returns all 3+ failure modes for healer-agent with recovery steps.

### Test 2: AI Diagnostics

```bash
curl -X POST http://127.0.0.1:8010/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "test-agent",
    "symptoms": ["Service failed to start", "Error binding to port 8080"]
  }' | jq .
```

**Expected:** Returns diagnosis with confidence score + recommended fixes.

### Test 3: SLO Lookup

```bash
curl http://127.0.0.1:8010/slos/hypercode-core | jq .
```

**Expected:** Returns performance SLOs (latency, availability, MTTR targets).

### Test 4: Life-Plan Overview

```bash
curl http://127.0.0.1:8010/life-plan/backend-specialist | jq .
```

**Expected:** Complete life-plan with purpose, dependencies, metrics, failure modes.

### Test 5: Multi-Agent Workflow

```bash
# Submit workflow
WORKFLOW=$(cat <<'EOF'
{
  "id": "test-workflow-1",
  "name": "Test Multi-Agent Workflow",
  "parallel": false,
  "steps": [
    {
      "id": "step-1",
      "agent_type": "test-agent",
      "task_description": "Verify system health",
      "timeout_seconds": 60
    }
  ]
}
EOF
)

curl -X POST http://127.0.0.1:8081/workflow/execute \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $(grep API_KEY ./HyperCode-V2.0/.env | cut -d= -f2)" \
  -d "$WORKFLOW" | jq .

# Check status (replace workflow-id)
curl http://127.0.0.1:8081/workflow/test-workflow-1 \
  -H "X-API-Key: $(grep API_KEY ./HyperCode-V2.0/.env | cut -d= -f2)" | jq .
```

**Expected:** Workflow queued → running → completed with results.

### Test 6: CodeRabbit Webhook

```bash
curl -X POST http://127.0.0.1:8089/webhook/coderabbit \
  -H "Content-Type: application/json" \
  -d '{
    "event": "review_completed",
    "pr": {
      "number": 42,
      "repo": "myorg/myrepo",
      "branch": "feature/new-api",
      "html_url": "https://github.com/myorg/myrepo/pull/42"
    },
    "review": {
      "summary": "Found 5 issues",
      "critical_issues": [
        {
          "type": "backend",
          "description": "Missing error handling in API endpoint"
        },
        {
          "type": "security",
          "description": "SQL injection vulnerability in user search"
        }
      ],
      "suggestions": [
        {
          "category": "performance",
          "description": "Add database index"
        }
      ]
    }
  }' | jq .
```

**Expected:** Returns task IDs generated and submitted to orchestrator.

---

## Troubleshooting

### Healer fails to start

```bash
docker compose logs healer-agent -f

# Check if YAML files exist
ls -la ./HyperCode-V2.0/agents/life-plans/*.yaml

# Rebuild without cache
docker compose build healer-agent --no-cache --progress=plain
```

### Diagnostics returns errors

```bash
# Check API keys in .env
grep -E "ANTHROPIC|PERPLEXITY|OPENAI" ./HyperCode-V2.0/.env

# If empty, AI diagnostics will fall back to manual instructions (still works)
curl -X POST http://127.0.0.1:8010/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "test-agent",
    "symptoms": ["Port already in use"]
  }' | jq '.escalate_to_human'
# Should return: false (falls back to heuristics)
```

### Workflow doesn't execute

```bash
# Check orchestrator health
curl http://127.0.0.1:8081/health

# Check Redis connection
redis-cli ping

# Check API key
echo $API_KEY

# Try without API key requirement (dev mode)
curl -X POST http://127.0.0.1:8081/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{"name":"test","steps":[]}'
```

### CodeRabbit webhook not triggering tasks

```bash
# Check if agent is running
docker compose ps coderabbit-webhook

# Check logs
docker compose logs coderabbit-webhook -f

# Verify orchestrator URL is reachable from webhook
docker exec coderabbit-webhook curl http://crew-orchestrator:8080/health

# Test webhook directly (no GitHub required)
curl -X POST http://127.0.0.1:8089/webhook/coderabbit \
  -H "Content-Type: application/json" \
  -d '{"event":"review_completed","pr":{"number":1,"repo":"test","branch":"main"},"review":{"critical_issues":[]}}'
```

---

## Monitoring Phase 2

### Watch Workflow Execution

```bash
# In terminal 1: Monitor workflows
watch -n 1 'curl -s http://127.0.0.1:8081/workflows | jq "."'

# In terminal 2: Check Redis directly
redis-cli MONITOR | grep workflow
```

### Check Life-Plans Loaded

```bash
redis-cli KEYS "workflow:*" | wc -l
docker compose logs healer-agent | grep "life-plans"
```

### View Diagnostics in Action

```bash
# Simulate unhealthy service and diagnose
docker compose pause test-agent

# Healer should detect via watchdog
curl -X POST http://127.0.0.1:8010/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "test-agent",
    "symptoms": ["Health check timeout", "Container not responding"]
  }' | jq .

# Resume
docker compose unpause test-agent
```

---

## Next Steps

1. **Integrate with GitHub Actions:**
   - Set webhook secret: `CODERABBIT_WEBHOOK_SECRET=<secret>`
   - GitHub → Settings → Webhooks → Add webhook to CodeRabbit endpoint

2. **Set up Prometheus queries:**
   - Use `/all-metrics` response to add metrics to prometheus.yml
   - Create Grafana dashboards from those metrics

3. **Configure on-call notifications:**
   - Connect `/diagnose` output to Slack/PagerDuty
   - Use `/playbook` endpoint to auto-execute recovery

4. **Test end-to-end:**
   - CodeRabbit review → Webhook → Auto-fix → PR updated → Auto-merge ✅

---

**Phase 2 is now live! 🚀**

