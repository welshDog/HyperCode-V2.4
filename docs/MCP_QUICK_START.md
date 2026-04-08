# Quick Reference: MCP + Model Runner Integration

## 🚀 One-Line Start

```powershell
# Windows
docker compose -f docker-compose.yml -f docker-compose.mcp-gateway.yml up -d

# Linux/Mac
docker compose -f docker-compose.yml -f docker-compose.mcp-gateway.yml up -d
```

## ✅ Verify Running

```bash
docker compose ps | findstr mcp
# OR
docker compose ps -f name=mcp
```

## 🧪 Quick Test

```bash
# Discover available tools
curl -H "Authorization: Bearer agent-key-001" http://localhost:8820/tools/discover

# Call a tool
curl -X POST \
  -H "Authorization: Bearer agent-key-001" \
  -H "Content-Type: application/json" \
  -d '{"tool":"github:list_repos","params":{"owner":"welshDog"}}' \
  http://localhost:8820/tools/call
```

## 🐍 Use in Agent Code

```python
from shared.mcp_client import MCPClient

async def my_agent():
    client = MCPClient()
    
    # GitHub
    repos = await client.github.list_repos(owner="welshDog")
    
    # Database
    agents = await client.postgres.execute_query("SELECT * FROM agents")
    
    # Search
    docs = await client.vectordb.search("HyperCode architecture", limit=5)
    
    await client.close()
```

## 📋 What's Included

- **mcp-gateway**: Central auth + rate limiting for tool access
- **model-runner**: Local LLM server (phi3 by default)
- **mcp-github**: Repo operations
- **mcp-postgres**: Database queries
- **mcp-filesystem**: Safe file access
- **mcp-vectordb**: RAG / similarity search

## ⚙️ Configuration

Edit `.env.mcp` or append to `.env`:

```bash
MCP_GATEWAY_API_KEY=your-secure-key
GITHUB_TOKEN=ghp_your_token
GPU_ENABLED=false
MODEL_RUNNER_DEFAULT_MODEL=phi3:3.8b-mini-instruct-4k-q4_K_M
```

## 🔥 Next: Wire an Agent

Edit `docker-compose.yml`:

```yaml
backend-specialist:
  environment:
    - MCP_GATEWAY_URL=http://mcp-gateway:8820
    - MCP_GATEWAY_API_KEY=${MCP_GATEWAY_API_KEY}
    - LLM_ENDPOINT=http://model-runner:11434
```

Then use MCP client in agent code (see above).

## 📚 Documentation

Full guide: `docs/MCP_GATEWAY_OPERATIONAL_GUIDE.md`

## 💬 Troubleshoot

Gateway down?
```bash
docker logs mcp-gateway
```

Model won't start?
```bash
docker logs model-runner
```

Can't connect?
```bash
docker exec backend-specialist-mcp curl http://mcp-gateway:8820/health
```
