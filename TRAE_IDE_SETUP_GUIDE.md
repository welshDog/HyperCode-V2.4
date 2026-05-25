# 🎓 TRAE IDE — Agent Training System Setup Guide
**For HyperCode V2.4 Agent Squad**

---

## 📚 What You Get

A complete **Trae IDE integration** that lets you:
- ✅ Chat with agents in real-time
- ✅ Train agents with new skills
- ✅ Record training sessions
- ✅ Collaborate across multiple agents
- ✅ Visualize agent capabilities
- ✅ Track training progress

---

## 🚀 QUICK START (5 minutes)

### Option 1: Web Dashboard (Easiest)

```bash
# 1. Start Trae IDE container
cd HyperCode-V2.4
docker compose -f docker-compose.yml -f docker-compose.trae.yml up -d trae-ide agent-training-api

# 2. Open browser
open http://localhost:3500

# 3. Select agent from dropdown
# 4. Start chatting!
```

**Result:** Beautiful web interface in your browser

---

### Option 2: CLI Terminal (Developer-Friendly)

```bash
# 1. Install requirements
pip install httpx asyncio pydantic

# 2. Run interactive terminal
cd HyperCode-V2.4
python trae-agent-bridge.py

# 3. Commands:
#    chat frontend-specialist "Create a React component for..."
#    train backend-specialist "FastAPI middleware patterns"
#    team "Refactor this code together"
#    status devops-engineer
```

**Result:** Full-featured CLI for power users

---

### Option 3: Python SDK (Programmatic)

```python
from trae_agent_bridge import TraeAgentClient, TraeSessionManager
import asyncio

async def main():
    # Create session manager
    manager = TraeSessionManager()
    
    # Train frontend specialist
    frontend = await manager.create_session("frontend-specialist")
    response = await frontend.send_message("Create a React form component")
    print(response)
    
    # Train all agents together
    results = await manager.multi_agent_chat(
        "Review this code together",
        ["backend-specialist", "frontend-specialist", "qa-engineer"]
    )
    
    await manager.close_all()

asyncio.run(main())
```

---

## 🎯 REAL-WORLD TRAINING EXAMPLES

### Example 1: Training Frontend Specialist

```bash
trae> chat frontend-specialist "Create a responsive dashboard layout with Tailwind CSS"
```

**Result:**
```
💭 frontend-specialist:
   [Generated React component code with Tailwind CSS classes, responsive design, accessibility features]
```

---

### Example 2: Multi-Agent Code Review

```bash
trae> team "Review this FastAPI authentication implementation for security issues"
```

**Agents respond in parallel:**
```
🤝 backend-specialist:
   API structure looks good. Consider rate limiting.

🤝 devops-engineer:
   Add CORS configuration for prod deployment.

🤝 qa-engineer:
   Test authentication flows with 2FA edge cases.
```

---

### Example 3: Training New Skill

```bash
# Create training file
cat > training-example.json << 'EOF'
{
  "agent": "database-architect",
  "skill": "PostgreSQL Performance Tuning",
  "examples": [
    {
      "problem": "Slow query on users table (100M rows)",
      "solution": "Add composite index on (status, created_at)",
      "explanation": "Speeds up filtering by 50x"
    },
    {
      "problem": "High memory usage from Seq Scan",
      "solution": "Use EXPLAIN ANALYZE to find missing indexes",
      "explanation": "Reveals index gaps in query planner"
    }
  ]
}
EOF

# Train agent
python -c "
from trae_agent_bridge import TraeSessionManager
import json, asyncio

async def train():
    manager = TraeSessionManager()
    with open('training-example.json') as f:
        data = json.load(f)
    
    db_arch = await manager.create_session('database-architect')
    await manager.record_training('database-architect', data)
    print('✓ Skill trained')

asyncio.run(train())
"
```

---

## 📊 WEB DASHBOARD FEATURES

### Main Interface
```
┌─────────────────────────────────────────────┐
│  TRAE IDE — Agent Training Dashboard        │
├─────────────────────────────────────────────┤
│                                             │
│  [Agent Selector] ▼ frontend-specialist     │
│                                             │
│  ┌─────────────────────────────────┐       │
│  │ Conversation History            │       │
│  ├─────────────────────────────────┤       │
│  │ You: Create a form component    │       │
│  │                                 │       │
│  │ Agent: [Generated response]     │       │
│  │        [with code snippet]      │       │
│  └─────────────────────────────────┘       │
│                                             │
│  [Input field] ___________________         │
│                            [Send] [Train]  │
│                                             │
│  Skills: React, Next.js, Tailwind CSS     │
│  Status: ✅ Online                         │
│  Uptime: 2h 34m                            │
│                                             │
└─────────────────────────────────────────────┘
```

### Features:
- **Agent Selector:** Switch between 6 agents
- **Live Chat:** Real-time bidirectional messaging
- **Training Panel:** Upload training data
- **Skill Browser:** View trained skills
- **Session History:** Review past interactions
- **Performance Metrics:** Track agent improvement

---

## 🔗 API ENDPOINTS

All endpoints available for custom integration:

### Chat
```bash
POST /chat
{
  "agent_name": "backend-specialist",
  "message": "Implement a caching layer",
  "context": {"language": "Python", "framework": "FastAPI"}
}
```

### Train
```bash
POST /train
{
  "agent_name": "qa-engineer",
  "skill": "Test Automation Patterns",
  "examples": [
    {
      "problem": "How to test WebSocket connections?",
      "solution": "Use pytest-asyncio with mock WebSocket",
      "explanation": "..."
    }
  ]
}
```

### Get Skills
```bash
GET /skills/backend-specialist
```

### WebSocket (Real-time)
```javascript
const ws = new WebSocket('ws://localhost:8097/ws/agent/frontend-specialist');
ws.onmessage = (e) => {
  console.log('Agent response:', e.data);
};
ws.send('Create a button component');
```

---

## 🎓 TRAINING WORKFLOWS

### Workflow 1: Skill Development (Week 1)

**Goal:** Train backend specialist on advanced FastAPI patterns

```bash
# Day 1: Authentication patterns
trae> chat backend-specialist "Show me FastAPI OAuth2 implementation with JWT"

# Day 2: Database integration
trae> chat backend-specialist "How do you handle database transactions in FastAPI?"

# Day 3: Error handling
trae> chat backend-specialist "Best practices for global exception handling"

# Day 4: Summary
trae> train backend-specialist "Advanced FastAPI Patterns" --from-history
```

**Result:** Agent has 3 new skills recorded

---

### Workflow 2: Code Quality Review

**Goal:** Improve code through multi-agent review

```bash
# Submit code for review
trae> team "Review this payment processing code for:
  1. Security issues
  2. Performance bottlenecks
  3. Test coverage gaps
  4. Infrastructure concerns"

# Analyze feedback
# Implement recommendations
# Submit revised code

# Verify improvements
trae> team "Here's the improved code. Rate each agent's suggestions."
```

**Result:** Production-grade code quality

---

### Workflow 3: Architecture Design

**Goal:** Design new system with agent collaboration

```bash
# Brainstorm architecture
trae> team "Design a real-time notification system that:
  - Scales to 1M users
  - Has <100ms latency
  - Persists messages"

# Refine with specialists
trae> chat devops-engineer "How to deploy this on Kubernetes?"
trae> chat database-architect "What database schema works best?"
trae> chat backend-specialist "Best API design for this?"

# Document decisions
trae> team "Summarize our final architecture decisions"
```

**Result:** Well-designed, production-ready system

---

## 📈 MONITORING TRAINING

### View Agent Skills
```bash
# See what each agent knows
docker exec agent-training-api python -c "
from main import SessionLocal, AgentSkill
db = SessionLocal()
for agent in ['backend-specialist', 'frontend-specialist']:
    skills = db.query(AgentSkill).filter_by(agent_name=agent).all()
    print(f'{agent}: {len(skills)} skills')
    for s in skills:
        print(f'  - {s.skill_name}')
"
```

### Track Performance
```bash
# Access Prometheus metrics
curl http://localhost:9090/api/v1/query?query=agent_response_time_ms
```

### Review Sessions
```bash
# List all training sessions
curl http://localhost:8097/sessions

# Review specific session
curl http://localhost:8097/sessions/session-2026-05-25-001
```

---

## 🔧 DOCKER SETUP

### Start Complete Training Stack
```bash
cd HyperCode-V2.4

# Option 1: With all services
docker compose -f docker-compose.yml \
               -f docker-compose.agents.yml \
               -f docker-compose.trae.yml \
               up -d

# Option 2: Just Trae (agents already running)
docker compose -f docker-compose.trae.yml up -d

# Verify
docker compose ps | grep trae
```

### Logs
```bash
# Trae IDE logs
docker compose logs -f trae-ide

# Agent training API logs
docker compose logs -f agent-training-api

# Both
docker compose logs -f trae-ide agent-training-api
```

---

## 🎯 BEST PRACTICES

### 1. **Regular Training Sessions**
- Schedule 1-2 training sessions per week
- Focus on one skill at a time
- Document results

### 2. **Cross-Agent Collaboration**
- Use `team` command for code reviews
- Different perspectives = better solutions
- Record collaborative decisions

### 3. **Skill Validation**
- Test trained skills with real problems
- Measure performance improvements
- Refine based on results

### 4. **Knowledge Sharing**
- Export trained skills
- Share between teams
- Build company knowledge base

---

## 🚀 ADVANCED FEATURES

### Export Trained Skills
```bash
curl http://localhost:8097/skills/backend-specialist > backend-skills.json
```

### Share Skills with Other Agents
```bash
# Train another agent with same skill
python -c "
import json
with open('backend-skills.json') as f:
    skills = json.load(f)

# Apply to frontend-specialist
for skill in skills['skills']:
    # POST to frontend-specialist training endpoint
    pass
"
```

### Create Agent Personas
```bash
# Define custom agent personalities
docker exec agent-training-api python -c "
import redis
r = redis.Redis()
r.hset('agent:personas', mapping={
    'strict-reviewer': 'Focus on code quality',
    'security-expert': 'Focus on security',
    'performance-specialist': 'Focus on speed'
})
"
```

---

## 📞 TROUBLESHOOTING

### Agents Offline
```bash
# Check if agents are running
docker compose ps | grep "8002\|8003\|8004\|8005\|8006"

# Restart if needed
docker compose restart backend-specialist
```

### No Response from Agent
```bash
# Check agent logs
docker compose logs backend-specialist | tail -20

# Verify connectivity
curl http://localhost:8003/health
```

### Training Not Saving
```bash
# Check skill repository
docker exec skill-repository psql -U skills -d skill_store -c "SELECT * FROM agent_skills LIMIT 5;"
```

---

## ✨ NEXT STEPS

1. **Start Trae IDE** → http://localhost:3500
2. **Chat with one agent** → Get familiar with interface
3. **Train one skill** → Upload training data
4. **Review multi-agent feedback** → See collaboration
5. **Build custom workflows** → Automate your process

---

**Ready to train your agents?** Let's go! 🚀

