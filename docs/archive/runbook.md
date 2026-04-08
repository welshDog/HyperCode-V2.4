# 📘 HyperCode Operations Runbook

## 🚀 Deployment

### Prerequisites
- Docker Engine 24.0+
- Docker Compose v2.20+
- 4GB RAM minimum available

### Start Sequence
1. **Pull Images**:
   ```bash
   docker compose pull
   ```
2. **Start All Services**:
   ```bash
   docker compose up -d
   ```
   *This starts Core, Agents, Database, Redis, and Observability stack.*

### Verification Checks
- **Core API**: `curl http://localhost:8000/health` → `{"status": "healthy", ...}`
- **Frontend**: Access `http://localhost:3000`
- **Grafana**: Access `http://localhost:3001`
- **Container Status**:
  ```bash
  docker compose ps
  ```

## 🔄 Rollback

If a deployment fails:

1. **Stop Services**:
   ```bash
   docker compose down
   ```
2. **Revert Image Tags**:
   Edit `docker-compose.yml` to point to previous stable tags.
3. **Restart Stack**:
   ```bash
   docker compose up -d
   ```

## 🚨 Incident Response

### High Memory Usage
If `coder-agent` or `hypercode-ollama` consumes excessive memory:
1. Check resource usage:
   ```bash
   docker stats
   ```
2. Restart the specific service:
   ```bash
   docker compose restart hypercode-ollama
   ```
3. Prune unused resources:
   ```bash
   docker system prune -f
   ```

### Agent Connection Failure
If agent logs show connection errors:
1. Verify Docker socket mount (for MCP):
   ```bash
   docker inspect hypercode-v20-coder-agent-1 | grep docker.sock
   ```
2. Check Agent Logs:
   ```bash
   docker compose logs coder-agent
   ```
3. Restart MCP server:
   ```bash
   docker compose restart mcp-server coder-agent
   ```

---
> *Built with WelshDog + BROski* 🚀🌙
