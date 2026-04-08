# 🎯 HyperCode V2.0 - Agent Factory

On-demand agent spawning without manual Docker Compose syntax.

## Quick Start

### Spawn a Single Agent
```bash
cd agents/agent-factory
./spawn_agent.sh coder-agent
```

### Available Agents
```
Core Crew:
  • crew-orchestrator   — Task routing & orchestration brain
  • healer-agent        — System health monitoring & auto-healing
  • coder-agent         — Code generation & development
  • tips-tricks-writer  — Content & documentation generation

Specialists:
  • frontend-specialist   — UI/UX development
  • backend-specialist    — API & server development
  • database-architect    — Database design & optimization
  • qa-engineer          — Testing & quality assurance
  • devops-engineer      — Infrastructure & deployment
  • security-engineer    — Security audits & hardening
  • system-architect     — System design & architecture
  • project-strategist   — Project planning & management
  • test-agent          — Testing & validation
```

## Usage Patterns

### 1️⃣ Lean Stack (4GB RAM Systems)
For systems with limited memory, use the lite profile:

```bash
# Start only essential agents (~2GB RAM)
docker compose -f docker-compose.yml -f docker-compose.agents-lite.yml up -d

# Start individual agents as needed
./spawn_agent.sh frontend-specialist
./spawn_agent.sh backend-specialist
```

**What's included:**
- `crew-orchestrator` (512M) — Task routing
- `coder-agent` (512M) — Code generation
- `tips-tricks-writer` (512M) — Content
- `healer-agent` (512M) — Health monitoring

**What's excluded:** All other specialists (saves ~4GB)

### 2️⃣ Full Stack (8GB+ RAM Systems)
For high-performance systems with full agent support:

```bash
# Start all agents with profile
docker compose --profile agents up -d

# Then spawn additional agents on-demand
./spawn_agent.sh frontend-specialist
./spawn_agent.sh backend-specialist
./spawn_agent.sh qa-engineer
```

### 3️⃣ Cherry-Pick Agents
Start only the agents you need:

```bash
# Just development crew
./spawn_agent.sh coder-agent
./spawn_agent.sh frontend-specialist
./spawn_agent.sh backend-specialist

# Wait for them to initialize
sleep 5

# Verify they're running
docker ps | grep specialist
docker ps | grep orchestrator
```

## Command Reference

### Spawn an Agent
```bash
./spawn_agent.sh <agent-name>
```

**Examples:**
```bash
./spawn_agent.sh coder-agent
./spawn_agent.sh healer-agent
./spawn_agent.sh frontend-specialist
./spawn_agent.sh qa-engineer
```

### View Agent Logs
```bash
docker logs <agent-name> --tail 100 -f
```

**Example:**
```bash
docker logs coder-agent --tail 100 -f
docker logs healer-agent -f
```

### Check Agent Status
```bash
docker ps | grep <agent-name>
docker inspect <agent-name>
```

### Restart an Agent
```bash
docker restart <agent-name>
```

### Stop an Agent
```bash
docker stop <agent-name>
```

### Remove an Agent Container
```bash
docker rm <agent-name>
```

## Environment Variables

### Healer Agent Configuration
The `healer-agent` monitors system health. Customize what it watches:

```bash
# Only watch core services (default)
export HEALER_WATCHED_SERVICES=hypercode-core,redis,postgres,celery-worker,hypercode-ollama

# Watch core + specific agents
export HEALER_WATCHED_SERVICES=hypercode-core,redis,postgres,coder-agent,frontend-specialist

# Then spawn
./spawn_agent.sh healer-agent
```

### Memory Limits
By default, lean profile agents use 512M max. To increase:

Edit `docker-compose.agents-lite.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 768M  # Increase from 512M
```

## Troubleshooting

### Agent Fails to Start
Check logs:
```bash
docker logs <agent-name> --tail 50
```

Common issues:
- **Port conflict:** Agent port already in use
- **Memory:** System out of RAM (add swap or restart unused containers)
- **Dependency:** Required service not running (check `redis`, `postgres`, `hypercode-core`)

### Fix: Restart Core Services
```bash
# Make sure core dependencies are running
docker compose up -d redis postgres hypercode-core

# Then spawn agent
./spawn_agent.sh <agent-name>
```

### Agent Port Already in Use
```bash
# Find what's using the port
docker ps --filter "expose=8002"  # Example: coder-agent port

# Stop conflicting container
docker stop <conflicting-container>

# Spawn agent
./spawn_agent.sh <agent-name>
```

### Check System Resources
```bash
# Memory usage
docker stats --no-stream

# Disk usage
docker system df

# Free up space if needed
docker system prune -f
```

## Monitoring & Health

### Health Check Endpoint
Most agents expose a `/health` endpoint:

```bash
curl http://localhost:8002/health  # coder-agent
curl http://localhost:8081/health  # crew-orchestrator
curl http://localhost:8010/health  # healer-agent
```

### Performance Metrics
Via Prometheus (running at `http://localhost:9090`):

```
# Agent CPU usage
container_cpu_usage_seconds_total{name=~".*agent.*"}

# Agent memory
container_memory_usage_bytes{name=~".*agent.*"}

# Agent uptime
time() - container_start_time_seconds{name=~".*agent.*"}
```

### Live Monitoring
```bash
# Watch all agents in real-time
watch -n 1 'docker stats --no-stream | grep agent'

# Or with docker compose
docker compose stats --no-stream
```

## Advanced Usage

### Mass Spawn Agents
```bash
# Spawn multiple agents sequentially
for agent in coder-agent frontend-specialist backend-specialist; do
  echo "Spawning $agent..."
  ./spawn_agent.sh "$agent"
  sleep 2
done
```

### Spawn with Custom Config
```bash
# Set memory limit before spawning
export DOCKER_MEMORY_LIMIT=768m
./spawn_agent.sh coder-agent
```

### Development Workflow
```bash
# 1. Start core services
docker compose up -d redis postgres hypercode-core

# 2. Spawn development agents
./spawn_agent.sh coder-agent
./spawn_agent.sh frontend-specialist
./spawn_agent.sh backend-specialist

# 3. Watch logs
docker compose logs -f coder-agent frontend-specialist

# 4. Run tests
./spawn_agent.sh test-agent

# 5. Stop when done
docker compose down
```

## Performance Tips

### Optimize for Low RAM (4GB Systems)
1. **Use lean profile:**
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.agents-lite.yml up -d
   ```

2. **Don't run all agents together:**
   ```bash
   # ❌ Bad: OOM kill
   docker compose --profile agents up -d
   
   # ✅ Good: Spawn as needed
   ./spawn_agent.sh coder-agent
   ./spawn_agent.sh healer-agent
   ```

3. **Increase WSL2 memory (if on Windows):**
   Edit `%USERPROFILE%\.wslconfig`:
   ```ini
   [wsl2]
   memory=8GB
   processors=4
   ```

### Optimize for High Performance (8GB+ Systems)
1. **Start full stack:**
   ```bash
   docker compose --profile agents up -d
   ```

2. **Increase resource limits:**
   Edit `docker-compose.yml`:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 1G    # Increase from 512M
         cpus: "1"     # Increase from 0.5
   ```

3. **Enable caching:**
   ```bash
   # Cache models locally
   export OLLAMA_MODEL_CACHE=/path/to/cache
   ./spawn_agent.sh coder-agent
   ```

## 📚 Related Docs

- **Main README:** `../README.md`
- **Docker Compose:** `../../docker-compose.yml`
- **Lite Profile:** `../../docker-compose.agents-lite.yml`
- **Healer Agent:** `../healer/README.md`

---

**🏴󠁧󠁢󠁷󠁬󠁳󠁿 Built for HyperCode V2.0 — Neurodivergent-first AI Agent Ecosystem**
