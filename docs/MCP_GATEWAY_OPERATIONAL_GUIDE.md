# Operational Guide: MCP Gateway + Model Runner for HyperCode V2.0

## What Just Shipped

You now have a **production-grade MCP infrastructure profile** that adds:

- ✅ **MCP Gateway** (Central control for agent tool access)
- ✅ **Docker Model Runner** (Replace Ollama with optimized LLM serving)
- ✅ **4 MCP Tools** (GitHub, PostgreSQL, File System, Vector DB)
- ✅ **Agent Integration Layer** (Python client for agents to use tools)
- ✅ **Environment Configuration** (All settings in `.env.mcp`)

---

## 🚀 Quick Start

### 1. Load the MCP Infrastructure Profile

```bash
# Start main stack + MCP/Model Runner
docker compose -f docker-compose.yml -f docker-compose.mcp-gateway.yml up -d

# Or just start MCP profile (if main stack already running)
docker compose -f docker-compose.mcp-gateway.yml up -d
```

### 2. Configure Environment

Copy the MCP settings to your `.env`:

```bash
# Option A: Append (if .env already exists)
cat .env.mcp >> .env

# Option B: Manual setup (if you prefer)
# Add these to .env:
MCP_GATEWAY_API_KEY=agent-key-001
MCP_GATEWAY_ADMIN_KEY=admin-super-secret-key
GITHUB_TOKEN=ghp_YOUR_GITHUB_TOKEN_HERE
GPU_ENABLED=false
MODEL_RUNNER_DEFAULT_MODEL=phi3:3.8b-mini-instruct-4k-q4_K_M
```

### 3. Verify Services Running

```bash
# Check all MCP services healthy
docker compose ps | grep mcp

# Expected output:
# mcp-gateway          mcp-gateway:8820     Up (healthy)
# mcp-github           mcp-github:3001      Up (healthy)
# mcp-postgres         mcp-postgres:3002    Up (healthy)
# mcp-filesystem       mcp-filesystem:3003  Up (healthy)
# mcp-vectordb         mcp-vectordb:3004    Up (healthy)
# model-runner         model-runner:11434   Up (healthy)
```

### 4. Test the Gateway

```bash
# Discover available tools
curl -H "Authorization: Bearer agent-key-001" \
  http://localhost:8820/tools/discover

# Test a tool call (GitHub list repos)
curl -X POST \
  -H "Authorization: Bearer agent-key-001" \
  -H "Content-Type: application/json" \
  -d '{"tool": "github:list_repos", "params": {"owner": "welshDog"}}' \
  http://localhost:8820/tools/call
```

---

## 🤖 Wire an Agent to Use MCP

### Example: Backend Specialist Agent

Edit `agents/02-backend-specialist/Dockerfile` or `main.py`:

```python
# Import the MCP client
from shared.mcp_client import MCPClient

class BackendSpecialistAgent:
    def __init__(self):
        self.mcp = MCPClient()  # Auto-discovers gateway from env
    
    async def analyze_repo(self, owner: str, repo: str):
        """Use MCP tools to analyze GitHub repo"""
        
        # List issues via MCP Gateway
        issues_result = await self.mcp.github.list_issues(owner, repo)
        if issues_result.success:
            issues = issues_result.data
            print(f"Found {len(issues)} open issues")
        
        # Query database for agent history
        history_result = await self.mcp.postgres.execute_query(
            "SELECT * FROM agent_decisions WHERE repo = %s LIMIT 10",
            {"repo": repo}
        )
        
        # Search for similar analysis in vector DB
        similar_result = await self.mcp.vectordb.search(
            f"Analyze {owner}/{repo}",
            limit=3
        )
        
        return {
            "issues": issues,
            "history": history_result.data,
            "similar_analyses": similar_result.data
        }
```

### Environment Variables for Agent

Add to `docker-compose.yml` service definition:

```yaml
backend-specialist:
  environment:
    # MCP Configuration
    MCP_GATEWAY_URL=http://mcp-gateway:8820
    MCP_GATEWAY_API_KEY=agent-key-001
    MCP_USE_GATEWAY=true
    
    # Model Runner
    LLM_ENDPOINT=http://model-runner:11434
    LLM_MODEL=phi3:3.8b-mini-instruct-4k-q4_K_M
```

---

## 📊 Monitoring MCP Gateway

### Prometheus Metrics (Auto-Scraped)

MCP Gateway exposes metrics at `http://mcp-gateway:8820/metrics`:

- `mcp_tool_calls_total` — Total tool invocations
- `mcp_tool_call_duration_seconds` — Latency per tool
- `mcp_tool_errors_total` — Error count by tool
- `mcp_rate_limit_exceeded_total` — Rate limit hits
- `mcp_cache_hits_total` — Cache effectiveness

### Grafana Dashboard

Add to Prometheus targets:

```yaml
scrape_configs:
  - job_name: 'mcp-gateway'
    static_configs:
      - targets: ['mcp-gateway:8820']
```

Then import dashboard (we'll provide one).

### Audit Logs

MCP Gateway logs all tool calls to PostgreSQL (`mcp_audit` schema):

```bash
# View recent tool invocations
docker exec postgres psql -U postgres -d hypercode -c \
  "SELECT agent_id, tool_name, status, latency_ms FROM mcp_audit.tool_calls ORDER BY created_at DESC LIMIT 10;"
```

---

## 🔧 Configuration Deep Dive

### MCP Gateway

| Setting | Default | Purpose |
|---------|---------|---------|
| `MCP_GATEWAY_API_KEY` | (required) | Agent access token |
| `MCP_RATE_LIMIT_PER_MINUTE` | 1000 | Protect backend from agent spam |
| `MCP_AUDIT_ENABLED` | true | Log all tool calls (compliance) |
| `AUTO_DISCOVER_TOOLS` | true | Find MCP servers automatically |

### Docker Model Runner

| Setting | Default | Purpose |
|---------|---------|---------|
| `MODEL_RUNNER_DEFAULT_MODEL` | phi3 | Lightweight, good for local dev |
| `GPU_ENABLED` | false | Set to true if you have NVIDIA GPU |
| `GPU_MEMORY_GB` | 4 | Max GPU memory per model |
| `MODEL_RUNNER_CACHE_PATH` | /cache | Cache downloaded models here |

**Model Options** (sorted by speed/quality):

- `tinyllama:1.1b` — Super fast, minimal RAM (good for quick tasks)
- `phi3:3.8b-mini-instruct` — ⭐ Default, fast + capable
- `mistral:7b-instruct` — Better quality, slower
- `neural-chat:7b` — Creative, balanced
- `zephyr:7b-beta` — Excellent reasoning

To download a model on startup:

```bash
docker exec model-runner ollama pull mistral:7b-instruct
```

### MCP Tools

| Tool | Requires | Use Case |
|------|----------|----------|
| **github** | `GITHUB_TOKEN` | Repo analysis, PR automation |
| **postgres** | DB URL | Query agent state, audit logs |
| **filesystem** | (none) | Read/write code, configs |
| **vectordb** | ChromaDB | RAG, similarity search |

---

## ⚠️ Security Checklist

- [ ] Set strong `MCP_GATEWAY_API_KEY` (not `agent-key-001` in production)
- [ ] Generate separate API keys per agent role (limit blast radius)
- [ ] Set `MCP_POSTGRES_READ_ONLY=true` for untrusted agents
- [ ] Restrict `MCP_FILESYSTEM_ALLOWED_DIRS` to needed paths only
- [ ] Enable audit logging (`MCP_AUDIT_ENABLED=true`)
- [ ] Review `mcp_audit.tool_calls` regularly for suspicious patterns
- [ ] Use `network_mode: internal` for MCP services in production
- [ ] Rotate `GITHUB_TOKEN` monthly

---

## 🐛 Troubleshooting

### Gateway Not Responding

```bash
# Check gateway health
curl http://localhost:8820/health

# Check logs
docker logs mcp-gateway

# Verify auth token
curl -H "Authorization: Bearer agent-key-001" \
  http://localhost:8820/tools/discover
```

### Model Runner Won't Start

```bash
# Check if GPU drivers are available
docker exec model-runner nvidia-smi  # If GPU_ENABLED=true

# Try with CPU only
docker exec model-runner ollama list

# Check available disk space for models
docker exec model-runner df -h /models
```

### Agent Can't Connect to Gateway

```bash
# Verify network connectivity
docker exec backend-specialist-mcp \
  curl -v http://mcp-gateway:8820/health

# Check DNS resolution
docker exec backend-specialist-mcp \
  getent hosts mcp-gateway
```

---

## 📈 Next Steps

### Immediate (This Week)

1. **Wire 2-3 Agents** → Use MCP client in backend-specialist, crew-orchestrator
2. **Test Tool Calls** → Verify GitHub, Postgres, FileSystem tools work
3. **Monitor Metrics** → Add MCP dashboard to Grafana
4. **Enable Audit** → Review logs for patterns

### Medium-Term (Next 2 Weeks)

5. **Add Custom MCP Tools** → Build tools specific to HyperCode (e.g., agent-health, deployment-status)
6. **Implement Caching** → Cache frequent tool calls (e.g., repo lists)
7. **Optimize Models** → Profile agents, pick best model per task
8. **Rate Limit Tuning** → Adjust limits based on actual usage

### Advanced (Next Month)

9. **Multi-Model Routing** → Route tasks to best model (local vs cloud)
10. **Tool Composition** → Chain tools (e.g., GitHub PR → DB insert → VectorDB index)
11. **Autonomous Evolution** → Let devops-engineer upgrade models based on performance

---

## 📚 API Reference

### MCP Gateway Endpoints

```
POST /tools/call
  Body: {"tool": "name", "params": {...}}
  Returns: {"result": data, "latency_ms": 45, "from_cache": false}

GET /tools/discover
  Returns: {"tools": [{"name": "github:list_repos", "description": "..."}]}

GET /tools/{category}
  Returns: Tools in category (github, postgres, etc.)

GET /metrics
  Returns: Prometheus metrics

GET /health
  Returns: {"status": "healthy", "tools": 4, "uptime_seconds": 3600}
```

### MCPClient Python API

```python
from shared.mcp_client import MCPClient

client = MCPClient()

# GitHub
result = await client.github.list_repos(owner="welshDog")
result = await client.github.list_issues(owner="welshDog", repo="HyperCode-V2.0")
result = await client.github.create_issue(owner="...", repo="...", title="...", body="...")

# PostgreSQL
result = await client.postgres.execute_query("SELECT * FROM agents")
result = await client.postgres.list_tables()

# File System
result = await client.filesystem.read_file("/workspace/README.md")
result = await client.filesystem.write_file("/data/output.txt", "content")

# Vector DB
result = await client.vectordb.search("HyperCode architecture", limit=5)
result = await client.vectordb.add_document("content", {"tag": "agent-design"})
```

---

## 🎯 Success Metrics

After 1 week:
- ✅ All MCP services healthy + discoverable
- ✅ ≥1 agent successfully calling tools via gateway
- ✅ 0 errors in `mcp_audit.tool_calls` table
- ✅ Tool latency <500ms for 95% of calls

After 1 month:
- ✅ 5+ agents using MCP tools
- ✅ Model Runner saving $$ vs cloud LLM calls
- ✅ Tool cache hit rate >40%
- ✅ Zero security incidents in audit logs

---

## 💬 Questions?

- **Gateway auth failing?** Check `MCP_GATEWAY_API_KEY` in `.env`
- **Model download stuck?** Check disk space: `docker system df`
- **Tools not discovered?** Ensure MCP containers are healthy: `docker compose ps`

BROski Power Level: 🦅♾️ AGENT META-ARCHITECT UNLOCKED 🔥
