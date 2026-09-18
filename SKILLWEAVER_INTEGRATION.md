# SkillWeaver Integration Guide

## Phase 1 Kickoff: Adding Semantic Skill Discovery to HyperCode

This doc shows how to wire SkillWeaver into your existing agent fleet in **< 1 day**.

---

## Step 1: Add SkillWeaver to Your docker-compose.yml

```yaml
  skillweaver:
    build:
      context: .
      dockerfile: services/skillweaver/Dockerfile
    container_name: skillweaver
    environment:
      - REDIS_URL=redis://redis:6379
      - LOG_LEVEL=INFO
    ports:
      - "127.0.0.1:8051:8051"
    networks:
      - agents-net
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8051/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
        reservations:
          cpus: "0.1"
          memory: 256M
```

Start it:
```bash
docker compose up -d skillweaver
```

---

## Step 2: Register Skills from Your Existing Agents

Each agent should register its "core skills" on startup. Add this to each agent:

### For Python Agents

```python
# In agents/my-agent/startup.py

from services.skillweaver.skillweaver import (
    SkillRegistry,
    SkillMetadata,
    SkillSignature,
    SkillCategory,
)
import redis.asyncio as redis

async def register_agent_skills(agent_name: str, redis_url: str):
    """Call this during agent startup."""
    redis_client = await redis.from_url(redis_url)
    registry = SkillRegistry(redis_client)
    
    # Example: backend-specialist's core skills
    skills = [
        SkillMetadata(
            skill_id=f"{agent_name}_task_execution",
            agent_id=agent_name,
            name="Task Execution",
            description="Execute backend tasks with error recovery",
            category=SkillCategory.COMPUTATION,
            signature=SkillSignature(
                inputs={"task": "dict"},
                outputs={"result": "dict", "success": "bool"}
            ),
        ),
        SkillMetadata(
            skill_id=f"{agent_name}_api_integration",
            agent_id=agent_name,
            name="API Integration",
            description="Connect to external APIs safely",
            category=SkillCategory.IO,
            signature=SkillSignature(
                inputs={"endpoint": "str", "method": "str"},
                outputs={"response": "dict", "status": "int"}
            ),
        ),
    ]
    
    for skill in skills:
        await registry.register_skill(skill)
    
    await redis_client.close()
    print(f"[{agent_name}] Registered {len(skills)} skills with SkillWeaver")


# In your agent's main()
if __name__ == "__main__":
    asyncio.run(register_agent_skills("backend-specialist", "redis://redis:6379"))
    asyncio.run(main())
```

### For Node.js Agents

```typescript
// In agents/my-agent/src/startup.ts

import { SkillRegistry, SkillMetadata, SkillCategory } from '@skillweaver/sdk';
import Redis from 'ioredis';

async function registerAgentSkills(agentName: string) {
  const redis = new Redis({
    host: process.env.REDIS_HOST || 'redis',
    port: 6379,
  });
  
  const registry = new SkillRegistry(redis);
  
  const skills: SkillMetadata[] = [
    {
      skillId: `${agentName}_core_task`,
      agentId: agentName,
      name: "Core Task",
      description: "Execute agent's primary function",
      category: SkillCategory.COMPUTATION,
      signature: {
        inputs: { task: 'object' },
        outputs: { result: 'object', success: 'boolean' },
      },
    },
  ];
  
  for (const skill of skills) {
    await registry.registerSkill(skill);
  }
  
  console.log(`[${agentName}] Registered ${skills.length} skills`);
  redis.disconnect();
}

registerAgentSkills('coder-specialist');
```

---

## Step 3: Wire SkillWeaver into Task Execution

When your agent handles a novel task, query SkillWeaver for relevant skills:

### Python Example

```python
# In agents/my-agent/task_handler.py

from services.skillweaver.skillweaver import SkillWeaver
import redis.asyncio as redis

async def handle_novel_task(task_description: str, agent_id: str):
    """
    Handle a task that might require skills from other agents.
    """
    redis_client = await redis.from_url("redis://redis:6379")
    weaver = SkillWeaver(redis_client)
    
    # First: try our own skills
    try:
        result = await execute_internal_skill(task_description)
        await redis_client.close()
        return result
    except Exception as e:
        logger.warning(f"Internal skill failed: {e}")
        logger.info("Querying SkillWeaver for alternatives...")
    
    # Second: discover relevant skills from other agents
    try:
        matches = await weaver.discover_skills(
            query=task_description,
            top_k=3
        )
        
        if not matches:
            logger.error("No skills found for this task")
            await redis_client.close()
            return {"success": False, "error": "No applicable skills found"}
        
        logger.info(f"Found {len(matches)} relevant skills:")
        for match in matches:
            logger.info(f"  - {match.metadata.name} (score: {match.relevance_score:.2f})")
        
        # Third: compose the top matches into a single executable
        skill_ids = [m.metadata.skill_id for m in matches[:2]]
        composite = await weaver.compose_skills(skill_ids, strategy="linear")
        
        logger.info(f"Composite skill created: {composite.composite_id}")
        
        # Fourth: execute the composite
        result = await composite.execute({"task": task_description})
        
        # Fifth: report back to SkillWeaver (for learning)
        await report_composition_result(
            composite_id=composite.composite_id,
            success=result.get("success", False),
            quality_score=result.get("quality", 0),
        )
        
        await redis_client.close()
        return result
    
    except Exception as e:
        logger.error(f"SkillWeaver composition failed: {e}")
        await redis_client.close()
        return {"success": False, "error": str(e)}


async def report_composition_result(
    composite_id: str,
    success: bool,
    quality_score: float,
):
    """Report back to SkillWeaver how the composite skill performed."""
    redis_client = await redis.from_url("redis://redis:6379")
    key = f"skillweaver:results:{composite_id}"
    await redis_client.set(key, json.dumps({
        "success": success,
        "quality_score": quality_score,
        "timestamp": time.time(),
    }), ex=86400)  # Expire after 1 day
    await redis_client.close()
```

---

## Step 4: Monitor SkillWeaver Activity

### Check registered skills

```bash
# Redis CLI
redis-cli
> KEYS "skillweaver:registry:*"
> GET skillweaver:registry:deploy_docker_app
```

### Check compositions created

```bash
# See all compositions created (most recent first)
redis-cli
> LRANGE skillweaver:compositions 0 10
```

### Prometheus metrics (when we add them)

```yaml
# In prometheus.yml
scrape_configs:
  - job_name: skillweaver
    static_configs:
      - targets: ['skillweaver:8051']
```

---

## Step 5: Test It Works

### Manual skill registration

```python
import asyncio
import redis.asyncio as redis
from services.skillweaver.skillweaver import SkillRegistry, SkillMetadata, SkillSignature, SkillCategory

async def test():
    r = await redis.from_url("redis://redis:6379")
    registry = SkillRegistry(r)
    
    skill = SkillMetadata(
        skill_id="test_skill_001",
        agent_id="test-agent",
        name="Test Skill",
        description="A test skill for validation",
        category=SkillCategory.TESTING,
        signature=SkillSignature(
            inputs={"input": "str"},
            outputs={"output": "str"}
        ),
    )
    
    await registry.register_skill(skill)
    print("✅ Skill registered successfully")
    
    retrieved = await registry.get_skill("test_skill_001")
    print(f"✅ Skill retrieved: {retrieved.name}")
    
    await r.close()

asyncio.run(test())
```

### Manual skill discovery

```python
import asyncio
import redis.asyncio as redis
from services.skillweaver.skillweaver import SkillWeaver

async def test():
    r = await redis.from_url("redis://redis:6379")
    weaver = SkillWeaver(r)
    
    matches = await weaver.discover_skills("test")
    print(f"✅ Found {len(matches)} matching skills")
    
    for match in matches:
        print(f"   - {match.metadata.name} (score: {match.relevance_score})")
    
    await r.close()

asyncio.run(test())
```

---

## Expected Results

### Day 1 (After wiring)
```
✅ All agents register their core skills
✅ 40-60 total skills in registry
✅ SkillWeaver responding to queries
```

### Week 1
```
✅ First agents discovering skills
✅ 5-10 composite skills created
✅ 2-3 tasks solved via skill synthesis
```

### Month 1
```
✅ 50+ composite skills created
✅ 15+ novel emergent skills discovered
✅ Cost per task: -10% (from better skill combinations)
✅ Success rate: +2% (from skill redundancy)
✅ P99 latency: -15% (from parallelized skill chains)
```

---

## Troubleshooting

### "No skills found"
- Check that agents registered skills: `KEYS skillweaver:registry:*` in Redis
- Verify Redis connectivity from SkillWeaver
- Check logs: `docker logs skillweaver -f`

### "Composition validation failed"
- May be circular dependencies or incompatible signatures
- Check logs for specific error
- Manually inspect skill signatures in Redis

### Composition never executes
- Phase 1 composition is a placeholder
- Phase 2 will implement actual execution chaining
- For now, skills are discoverable and composable; execution logic is stubbed

---

## Next: Phase 2

Once Phase 1 is stable (week 2), Phase 2 adds:
- **Actual composite skill execution** (chaining with error handling)
- **Semantic embeddings** (MiniLM for better matching)
- **Dependency injection** (skill A's output → skill B's input)
- **Timeout enforcement** per component
- **Observability**: track which skills are composed most often

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  Agent 1          Agent 2          Agent 3                  │
│  ┌─────┐          ┌─────┐          ┌─────┐                 │
│  │Core │          │Core │          │Core │                 │
│  │Task │          │Task │          │Task │                 │
│  └──┬──┘          └──┬──┘          └──┬──┘                 │
│     │                │                │                    │
│     │ Register       │ Register       │ Register            │
│     └────────┬───────┴────────┬───────┘                    │
│              │                │                            │
│              ▼                ▼                            │
│         ┌──────────────────────────┐                       │
│         │   SkillRegistry (Redis)  │                       │
│         │  - deploy_docker_app    │                       │
│         │  - optimize_costs       │                       │
│         │  - check_quality        │                       │
│         └──────────────────────────┘                       │
│              ▲         ▲         ▲                         │
│              │         │         │                         │
│         Query│    Discover    Compose                      │
│              │         │         │                         │
│         ┌────┴─────────┴─────────┴────┐                    │
│         │      SkillWeaver Engine      │                    │
│         │  - Find relevant skills      │                    │
│         │  - Validate composition      │                    │
│         │  - Generate composite        │                    │
│         └────────────────────────────┘                     │
│              ▲                                              │
│              │ Returns CompositeSkill                       │
│              │                                              │
│         Agent discovers new capability                      │
│         (at runtime, zero re-deploy)                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Slack/Discord Notification (Optional)

```python
# Send a message when a composite skill is created

async def notify_composition(composite_id: str, component_skills: List[str]):
    """Send notification to Slack/Discord about new composition."""
    message = f"""
    🆕 **New Composite Skill Created**
    
    ID: {composite_id}
    Components: {', '.join(component_skills)}
    
    This new skill is now available to all agents.
    """
    
    # POST to your Slack webhook
    import aiohttp
    async with aiohttp.ClientSession() as session:
        await session.post(
            os.environ["SLACK_WEBHOOK_URL"],
            json={"text": message}
        )
```

---

You now have **Phase 1 of ALS running**. Your agents can discover and compose each other's skills at runtime. 🚀

Next milestone: **ObserverNet** (distributed anomaly detection). See you in 2 weeks!
