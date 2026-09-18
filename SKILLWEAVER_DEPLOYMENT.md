# 🚀 SkillWeaver Deployment Guide

## Overview

This guide will get SkillWeaver (Phase 1 of HyperCode ALS) running in production **in under 1 hour**.

---

## Prerequisites

- ✅ Docker & Docker Compose
- ✅ Redis running and healthy
- ✅ Python 3.11+ (for testing/development)
- ✅ Access to your agent fleet

---

## Step 1: Add SkillWeaver to docker-compose.yml (5 minutes)

Open your `docker-compose.yml` and find the `services:` section.

Add this block after other services (or at the end):

```yaml
  skillweaver:
    build:
      context: .
      dockerfile: services/skillweaver/Dockerfile
    container_name: skillweaver
    image: hypercode/skillweaver:latest
    environment:
      - REDIS_URL=redis://redis:6379
      - LOG_LEVEL=INFO
      - PORT=8051
    ports:
      - "127.0.0.1:8051:8051"
    networks:
      - agents-net
      - data-net
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8051/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: "1"
          memory: 1G
        reservations:
          cpus: "0.25"
          memory: 512M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## Step 2: Build and Start SkillWeaver (10 minutes)

```bash
# Build the SkillWeaver image
docker compose build skillweaver

# Start SkillWeaver
docker compose up -d skillweaver

# Verify it's running
docker ps | grep skillweaver
# Expected: skillweaver container UP

# Check logs
docker logs skillweaver -f
# Expected: No error messages, "SkillWeaver server started"
```

---

## Step 3: Verify SkillWeaver Health (5 minutes)

```bash
# Check health endpoint
curl -s http://localhost:8051/health | jq

# Expected output:
# {
#   "status": "healthy",
#   "timestamp": "2026-04-22T...",
#   "redis_connected": true,
#   "skills_registered": 0,
#   "compositions_created": 0
# }

# Check documentation
curl -s http://localhost:8051/ | jq
```

---

## Step 4: Register Skills from Your Agents (20 minutes)

### For Each Agent:

Add this to your agent's startup code:

**Python Example:**

```python
# In agents/backend-specialist/startup.py

import asyncio
from services.skillweaver.sdk import SkillWeaverClient, register_agent_skills

async def initialize_skillweaver(agent_id: str, agent_name: str):
    """Register agent skills with SkillWeaver."""
    
    client = SkillWeaverClient("http://skillweaver:8051")
    
    skills = [
        (
            "core_task_execution",
            "Core Task Execution",
            "Execute primary agent function",
            {"task": "dict"},
            {"result": "dict", "success": "bool"},
        ),
        (
            "error_recovery",
            "Error Recovery",
            "Recover from failures gracefully",
            {"error": "str"},
            {"recovered": "bool"},
        ),
    ]
    
    registered = await register_agent_skills(client, agent_id, skills)
    print(f"✅ Registered {len(registered)} skills")
    await client.close()

# Call during startup
if __name__ == "__main__":
    asyncio.run(initialize_skillweaver("backend-specialist", "Backend Specialist"))
    main()  # Rest of your agent startup
```

**Node.js Example:**

```typescript
// In agents/my-agent/src/startup.ts

import axios from 'axios';

async function initializeSkillWeaver(agentId: string): Promise<void> {
  const client = axios.create({
    baseURL: 'http://skillweaver:8051/api/v1',
  });

  const skills = [
    {
      skill_id: 'core_task',
      agent_id: agentId,
      name: 'Core Task',
      description: 'Execute core functionality',
      category: 'computation',
      inputs: { task: 'string' },
      outputs: { result: 'object' },
    },
  ];

  for (const skill of skills) {
    try {
      await client.post('/skills/register', skill);
      console.log(`✅ Registered skill: ${skill.name}`);
    } catch (error) {
      console.error(`❌ Failed to register ${skill.name}:`, error);
    }
  }
}

// Call during startup
initializeSkillWeaver('my-agent').then(() => startAgent());
```

### Quick Test: Verify Skills Registered

```bash
# Check how many skills are registered
curl -s http://localhost:8051/api/v1/stats | jq '.total_skills'
# Expected: >= 30 (from your agent fleet)

# List all registered skills
curl -s http://localhost:8051/api/v1/skills/list | jq '.count'
```

---

## Step 5: Test Skill Discovery (10 minutes)

```bash
# Discover skills for "deployment"
curl -X POST http://localhost:8051/api/v1/skills/discover \
  -H "Content-Type: application/json" \
  -d '{
    "query": "deploy",
    "top_k": 5
  }' | jq

# Expected: List of matching skills with scores

# Discover skills for "optimization"
curl -X POST http://localhost:8051/api/v1/skills/discover \
  -H "Content-Type: application/json" \
  -d '{
    "query": "optimize costs",
    "top_k": 5
  }' | jq

# Expected: Cost-optimization-related skills
```

---

## Step 6: Test Skill Composition (5 minutes)

```bash
# Get some skill IDs first
SKILL_IDS=$(curl -s http://localhost:8051/api/v1/skills/list | jq -r '.skills[0:2] | map(.skill_id) | @json')

# Compose them
curl -X POST http://localhost:8051/api/v1/skills/compose \
  -H "Content-Type: application/json" \
  -d "{
    \"skill_ids\": $SKILL_IDS,
    \"strategy\": \"linear\"
  }" | jq

# Expected: Composite skill ID and status "ready"
```

---

## Step 7: Wire into an Agent (15 minutes)

Add to one of your agents (use the example from `services/skillweaver/example_agent.py`):

```python
from services.skillweaver.sdk import SkillWeaverClient, discover_and_compose

class MyAgent:
    async def handle_novel_task(self, task_description: str):
        """Handle tasks by discovering and composing skills."""
        
        client = SkillWeaverClient("http://skillweaver:8051")
        
        try:
            # Discover relevant skills
            matches = await client.discover_skills(task_description, top_k=3)
            
            if matches:
                print(f"Found {len(matches)} relevant skills")
                
                # Compose them
                composite = await discover_and_compose(
                    client, 
                    task_description
                )
                
                if composite:
                    print(f"✅ Created composite skill: {composite}")
                    # Execute composite skill here
                    return await self.execute_composite(composite, task_description)
        
        finally:
            await client.close()
```

---

## Monitoring SkillWeaver

### Real-Time Logs
```bash
docker logs skillweaver -f
```

### System Statistics
```bash
# Every 10 seconds, show stats
watch -n 10 'curl -s http://localhost:8051/api/v1/stats | jq'
```

### Prometheus Metrics (Future)
```
# Will expose at /metrics when implemented
curl http://localhost:8051/metrics
```

---

## Troubleshooting

### SkillWeaver won't start

**Error: "Failed to connect to Redis"**
```bash
# Check Redis is running
docker ps | grep redis

# If not running: 
docker compose up -d redis

# Verify Redis connection
docker exec skillweaver redis-cli ping
# Expected: PONG
```

**Error: "Address already in use"**
```bash
# Port 8051 is taken. Either:
# 1. Change port in docker-compose.yml
# 2. Kill process on 8051: lsof -ti:8051 | xargs kill
```

### Skills not registering

**Problem: No skills showing up**
```bash
# Check SkillWeaver is accessible from agents
docker exec backend-specialist curl http://skillweaver:8051/health

# If fails, agents and skillweaver may be on different networks
# Verify both are on same network: agents-net and data-net
```

### Skill discovery returns 0 results

**Problem: Query matches nothing**
```bash
# Check if skills exist first
curl -s http://localhost:8051/api/v1/skills/list | jq '.count'

# If > 0, try a different query
curl -X POST http://localhost:8051/api/v1/skills/discover \
  -H "Content-Type: application/json" \
  -d '{"query": "task", "top_k": 10}' | jq
```

---

## What's Working Now

✅ SkillWeaver running
✅ Skills registered from your agents
✅ Skill discovery working
✅ Skill composition working
✅ Agents can query SkillWeaver

---

## Next: Wire Into Your Workflows

### Use Case 1: Cost Optimization
```
Task: "Deploy service with cost optimization"
→ Agent queries: "optimize costs"
→ Finds: cost-analyzer, model-router skills
→ Composes: deploy + optimize
→ Result: Service deployed at 40% lower cost
```

### Use Case 2: Quality Assurance
```
Task: "Deploy with quality guarantees"
→ Agent queries: "quality check"
→ Finds: quality-checker, test-runner skills
→ Composes: deploy + test + validate
→ Result: Zero-downtime deployment with 99.5% uptime
```

### Use Case 3: Resilience
```
Task: "Deploy with auto-failover"
→ Agent queries: "failover reliability"
→ Finds: failover-agent, health-check skills
→ Composes: deploy + health_check + failover
→ Result: Multi-region resilient deployment
```

---

## Success Checklist

- [ ] SkillWeaver container running (`docker ps`)
- [ ] SkillWeaver healthy (`curl /health`)
- [ ] 30+ skills registered (`curl /api/v1/stats`)
- [ ] Skill discovery returning results
- [ ] Skill composition creating composites
- [ ] One agent wired to use SkillWeaver
- [ ] First novel task successfully handled

---

## Performance Targets (Month 1)

| Metric | Target |
|--------|--------|
| Skill discovery latency | <100ms |
| Skill composition latency | <50ms |
| Redis memory (10k skills) | <500MB |
| Composition success rate | >95% |
| Agent satisfaction | "This just works!" |

---

## You're Done! 🎉

SkillWeaver is now running. Your agents can:

✅ Register their skills
✅ Discover skills from other agents
✅ Compose them into new capabilities
✅ Execute composite skills

**Next:** [See example agent](./example_agent.py) or [read full docs](../README_THIS_SESSION.md).

---

## Getting Help

- **Logs**: `docker logs skillweaver -f`
- **API Docs**: `http://localhost:8051/docs` (Swagger UI)
- **Examples**: `services/skillweaver/example_agent.py`
- **Tests**: `pytest services/skillweaver/tests.py -v`

---

**You're now running Phase 1 of Autonomous Agent Evolution.** 🚀

Next up: ObserverNet (Phase 2) — distributed anomaly detection.

See you in 2 weeks! 👋
