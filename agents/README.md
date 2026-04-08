# 🤖 HyperCode V2.0 Agent Crew - Docker Setup

Complete Docker configuration for running your specialist AI agent team.

---

## 🚀 Quick Start (Choose Your Path)

### 🌟 Path 1: Lean Stack (4GB RAM Systems)
Perfect for development & testing on limited hardware:

```bash
cd HyperCode-V2.0
docker compose -f docker-compose.yml -f docker-compose.agents-lite.yml up -d
```

**What you get:**
- ✅ crew-orchestrator (task routing)
- ✅ coder-agent (development)
- ✅ tips-tricks-writer (content)
- ✅ healer-agent (health monitoring)
- **Total footprint:** ~2GB RAM, 2 CPU

**Spawn more agents as needed:**
```bash
cd agents/agent-factory
./spawn_agent.sh frontend-specialist
./spawn_agent.sh backend-specialist
```

### 🔥 Path 2: Full Stack (8GB+ RAM Systems)
All agents running for maximum capability:

```bash
cd HyperCode-V2.0
docker compose --profile agents up -d
```

**What you get:** All 13 specialist agents running concurrently

### 🎯 Path 3: On-Demand Spawning
Start agents as you need them (recommended):

```bash
cd HyperCode-V2.0/agents/agent-factory

# Spawn specific agents
./spawn_agent.sh crew-orchestrator
./spawn_agent.sh coder-agent
./spawn_agent.sh healer-agent

# Or batch spawn development crew
for agent in coder-agent frontend-specialist backend-specialist; do
  ./spawn_agent.sh "$agent"
done
```

---

## 📚 Agent Factory Commands

See `agents/agent-factory/README.md` for complete documentation.

### Spawn an Agent
```bash
cd agents/agent-factory
./spawn_agent.sh <agent-name>
```

**Available agents:**
```
Core Crew:
  • crew-orchestrator      — Central orchestration & task routing
  • healer-agent           — System health monitoring & auto-healing
  • coder-agent            — Code generation & development
  • tips-tricks-writer     — Content & documentation

Specialists:
  • frontend-specialist    — UI/UX development
  • backend-specialist     — API & server development
  • database-architect     — Database design & queries
  • qa-engineer           — Testing & validation
  • devops-engineer       — Infrastructure & CI/CD
  • security-engineer     — Security audits & hardening
  • system-architect      — System design & architecture
  • project-strategist    — Project planning & delegation
  • test-agent           — Testing automation
```

### Check Agent Status
```bash
docker ps | grep agent
docker logs <agent-name> -f
docker inspect <agent-name>
```

### Stop/Restart Agents
```bash
docker stop <agent-name>
docker restart <agent-name>
docker rm <agent-name>
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│  Crew Orchestrator (Port 8081)                  │
│  ├─ Task routing & delegation                   │
│  ├─ Agent coordination                          │
│  └─ Redis-backed state                          │
└──────────────────┬──────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
   ┌────▼───┐ ┌────▼───┐ ┌──▼──────┐
   │ Coder  │ │Frontend│ │Backend  │
   │ 8002   │ │8012    │ │8003     │
   └────────┘ └────────┘ └─────────┘
        │          │          │
        └──────────┼──────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
   ┌────▼───┐ ┌────▼───┐ ┌──▼──────┐
   │Database│ │   QA   │ │DevOps   │
   │8004    │ │8005    │ │8006     │
   └────────┘ └────────┘ └─────────┘
```

---

## 📋 Agent Services

| Agent | Port | Purpose | RAM | Profile |
|-------|------|---------|-----|---------|
| **crew-orchestrator** | 8081 | Task routing & coordination | 512M | agents |
| **coder-agent** | 8002 | Code generation & development | 512M | agents |
| **tips-tricks-writer** | 8011 | Content generation | 512M | agents |
| **healer-agent** | 8010 | System monitoring & healing | 512M | agents |
| frontend-specialist | 8012 | UI/UX development | 1G | agents |
| backend-specialist | 8003 | API & server development | 1G | agents |
| database-architect | 8004 | Database design & optimization | 1G | agents |
| qa-engineer | 8005 | Testing & validation | 1G | agents |
| devops-engineer | 8006 | Infrastructure & CI/CD | 1G | agents |
| security-engineer | 8007 | Security audits & hardening | 1G | agents |
| system-architect | 8008 | System design & architecture | 1G | agents |
| project-strategist | 8001 | Planning & delegation | 1G | agents |
| test-agent | (varies) | Test automation | 512M | agents |

---

## 🔧 Docker Compose Files

### Main Compose File
```bash
docker-compose.yml
```
Contains:
- Core infrastructure (Redis, Postgres, Ollama)
- Dashboard & monitoring
- All agent service definitions

### Lean Profile (Low-RAM)
```bash
docker-compose.agents-lite.yml
```
Override file for 4GB systems. Use with:
```bash
docker compose -f docker-compose.yml -f docker-compose.agents-lite.yml up -d
```

Resources per agent:
- Limits: 512M RAM, 0.5 CPU
- Reservations: 256M RAM, 0.25 CPU

---

## 🎯 Usage Examples

### Plan a Feature
```bash
curl -X POST http://localhost:8081/plan \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Create shopping cart feature",
    "context": {"tech_stack": "React, FastAPI, PostgreSQL"}
  }'
```

### Execute with Specific Agent
```bash
curl -X POST http://localhost:8081/agent/coder-agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Generate a TypeScript utility for date formatting",
    "context": {}
  }'
```

### Check Agent Health
```bash
curl http://localhost:8081/health          # Orchestrator
curl http://localhost:8002/health          # Coder agent
curl http://localhost:8012/health          # Frontend specialist
```

---

## 🐳 Docker Commands

### Start Services

```bash
# Lean profile (recommended for 4GB systems)
docker compose -f docker-compose.yml -f docker-compose.agents-lite.yml up -d

# Full stack with all agents
docker compose --profile agents up -d

# Just core services (no agents)
docker compose up -d
```

### Monitor & Debug

```bash
# View all containers
docker ps

# View agent logs
docker logs crew-orchestrator -f
docker logs coder-agent -f

# Check resource usage
docker stats

# Inspect container details
docker inspect coder-agent
```

### Stop & Cleanup

```bash
# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v

# Remove specific agent
docker stop coder-agent
docker rm coder-agent

# Cleanup unused images
docker image prune -a

# Full cleanup (warning: removes all Docker data)
docker system prune -a
```

---

## 🧠 Hive Mind Integration

All agents share knowledge through:

- **Team_Memory_Standards.md** — Coding standards & conventions
- **Agent_Skills_Library.md** — Reusable skills & patterns
- **Redis** — Real-time task coordination
- **PostgreSQL** — Persistent memory & history
- **agent_memory volume** — Shared workspace

---

## 🔍 Monitoring & Health

### Agent Health Endpoints
```bash
# Orchestrator
curl http://localhost:8081/health

# Individual agents (typically)
curl http://localhost:8002/health    # coder-agent
curl http://localhost:8012/health    # frontend-specialist
curl http://localhost:8003/health    # backend-specialist
```

### Prometheus Metrics
Access at `http://localhost:9090`

```
# Agent CPU usage
container_cpu_usage_seconds_total{name=~".*agent.*"}

# Agent memory
container_memory_usage_bytes{name=~".*agent.*"}

# Agent restarts
container_last_seen{name=~".*agent.*"}
```

### Grafana Dashboards
Access at `http://localhost:3001`

Pre-configured dashboards:
- Docker container metrics
- Agent performance
- System resource usage

---

## 🔐 Security Best Practices

1. **Environment variables** — Never commit `.env` files
2. **API keys** — Store in Docker Secrets or secrets manager
3. **Network isolation** — Agents on backend-net by default
4. **Resource limits** — Configured to prevent runaway containers
5. **Auto-restart** — Enabled for production stability

---

## 🚨 Troubleshooting

### Agent Won't Start
```bash
# Check logs
docker logs <agent-name>

# Verify dependencies
docker ps | grep -E "redis|postgres|hypercode-core"

# Restart dependencies first
docker restart redis postgres hypercode-core

# Then restart agent
docker restart <agent-name>
```

### Out of Memory
```bash
# Check current usage
docker stats --no-stream

# Stop unused agents
docker stop <agent-name>

# If WSL2 (Windows): Increase memory
# Edit: %USERPROFILE%\.wslconfig
[wsl2]
memory=8GB
processors=4
```

### Port Conflicts
```bash
# Find what's using port 8002
docker ps --format "{{.Names}} {{.Ports}}" | grep 8002

# Stop conflicting container
docker stop <container>

# Restart agent
docker restart <agent-name>
```

### Connection Errors
```bash
# Test Redis connection
docker exec redis redis-cli ping

# Test Postgres connection
docker exec postgres pg_isready

# Test Ollama connection
docker exec hypercode-ollama ollama list
```

---

## 📁 Project Structure

```
agents/
├── agent-factory/              ⭐ NEW: On-demand spawning
│   ├── spawn_agent.sh          — Spawn individual agents
│   └── README.md               — Complete usage guide
├── healer/                     — Health monitoring & healing
│   ├── main.py
│   ├── adapters/
│   └── requirements.txt
├── crew-orchestrator/          — Central orchestration
│   ├── main.py
│   └── requirements.txt
├── 01-frontend-specialist/
├── 02-backend-specialist/
├── 03-database-architect/
├── 04-qa-engineer/
├── 05-devops-engineer/
├── 06-security-engineer/
├── 07-system-architect/
├── 09-tips-tricks-writer/
├── test-agent/
├── coder/                      — Code generation agent
└── base-agent/                 — Shared base class

Configuration_Kit/              — Hive Mind (shared knowledge)
├── Team_Memory_Standards.md
└── Agent_Skills_Library.md
```

---

## 🎓 Next Steps

1. ✅ **Deploy lean profile** for your system size
2. ✅ **Monitor with Grafana** at http://localhost:3001
3. ✅ **Test agent communication** with curl requests
4. ✅ **Spawn agents on-demand** using agent-factory
5. ✅ **Implement custom workflows** for your use case
6. ✅ **Scale to Kubernetes** for production

---

## 📖 Documentation

- **Agent Factory:** `agents/agent-factory/README.md`
- **Healer Agent:** `agents/healer/README.md`
- **Main README:** `README.md`
- **Compose Files:**
  - `docker-compose.yml` — Main services
  - `docker-compose.agents-lite.yml` — Lean profile

---

**🏴󠁧󠁢󠁷󠁬󠁳󠁿 Built for HyperCode V2.0 — Neurodivergent-first AI Agent Ecosystem**
