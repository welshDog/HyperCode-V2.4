# 📡 HyperCode V2.0 — Complete Ports List
**Date**: March 19, 2026  
**Status**: Current & Active Ports  
**Total Services**: 34 running

---

## 📊 PORTS SUMMARY

| Category | Count | Status | Notes |
|----------|-------|--------|-------|
| **Public (0.0.0.0)** | 8 ports | 🟢 Open | Accessible from network |
| **Localhost (127.0.0.1)** | 8 ports | 🟡 Internal | Container-only access |
| **No Binding** | 4 ports | 🔵 Internal | Inter-container only |
| **Total Active Ports** | 20+ | 🟢 Operational | See details below |

---

## 🟢 PUBLIC PORTS (0.0.0.0 - Network Accessible)

These are accessible from any machine on your network (not just localhost):

| Port | Service | Container | URL | Status | Purpose |
|------|---------|-----------|-----|--------|---------|
| **8014** | throttle-agent | throttle-agent | `http://0.0.0.0:8014` | ✅ UP | Resource Manager (NEW!) |
| **8013** | test-agent | test-agent | `http://0.0.0.0:8013` | ✅ UP | Test/Demo Agent (UPGRADED!) |
| **8010** | healer-agent | healer-agent | `http://0.0.0.0:8010` | ✅ UP | System Healer |
| **8081** | crew-orchestrator | crew-orchestrator | `http://0.0.0.0:8081` | ✅ UP | Agent Orchestrator |
| **8003** | backend-specialist | backend-specialist | `http://0.0.0.0:8003` | ✅ UP | Backend Code Gen |
| **8080** | openshell-cluster | openshell-cluster-nemoclaw | `http://0.0.0.0:8080` | 🟢 UP | OpenShell Cluster |
| **8811** | docker-extension | docker_labs-ai-tools... | `http://0.0.0.0:8811` | ✅ UP | Docker Extension |
| **9100** | node-exporter | node-exporter | `http://0.0.0.0:9100` | ✅ UP | System Metrics |
| **9101** | mcp-exporter | mcp-exporter | `http://0.0.0.0:9101` | ✅ UP | MCP Metrics |
| **9808** | celery-exporter | celery-exporter | `http://0.0.0.0:9808` | ✅ UP | Celery Task Metrics |
| **59080** | pgadmin | pgadmin4_embedded... | `http://0.0.0.0:59080` | ✅ UP | Database Admin UI |

**Note**: `0.0.0.0:PORT` means accessible from: `http://localhost:PORT` or `http://<your-ip>:PORT`

---

## 🟡 LOCALHOST ONLY (127.0.0.1 - Internal Only)

These are only accessible from your local machine (not from network):

| Port | Service | Container | URL | Status | Purpose |
|------|---------|-----------|-----|--------|---------|
| **8000** | hypercode-core | hypercode-core | `http://127.0.0.1:8000` | ✅ UP | Main API |
| **8099** | hyper-mission-ui | hyper-mission-ui | `http://127.0.0.1:8099` | ✅ UP | Mission UI |
| **8088** | hypercode-dashboard | hypercode-dashboard | `http://127.0.0.1:8088` | 🟡 UNHEALTHY | Dashboard (starting) |
| **8821** | mcp-rest-adapter | mcp-rest-adapter | `http://127.0.0.1:8821` | ✅ UP | MCP REST Bridge |
| **8820** | mcp-gateway | mcp-gateway | `http://127.0.0.1:8820` | ✅ UP | MCP Gateway |
| **9000** | minio | minio | `http://127.0.0.1:9000` | ✅ UP | S3 Storage (API) |
| **9001** | minio | minio | `http://127.0.0.1:9001` | ✅ UP | S3 Storage (Console) |
| **8009** | chroma | b052a6426814_chroma | `http://127.0.0.1:8009` | ✅ UP | Vector Database |

**Note**: `127.0.0.1:PORT` = `localhost:PORT` - only accessible from your machine

---

## 🔵 NO PORT BINDING (Internal Container Network Only)

These services communicate internally via Docker network (no host port):

| Port (Internal) | Service | Container | Status | Purpose |
|-----------------|---------|-----------|--------|---------|
| **5000** | hyper-mission-api | hyper-mission-api | ✅ UP | Mission API (internal) |
| **8000** | celery-worker | celery-worker | 🟡 UNHEALTHY | Task Queue (internal) |
| **8000** | chroma-mcp | chroma-mcp | ✅ UP | Vector DB MCP (internal) |
| **8082** | mcp-github | mcp-github | ✅ UP | GitHub MCP (internal) |
| **6379** | redis | redis | ✅ UP | Cache (internal) |
| **5432** | postgres | postgres | ✅ UP | Database (internal) |
| **30051** | openshell (internal) | openshell-cluster | 🟢 UP | OpenShell internal port |

**Note**: These are only accessible from other containers (docker network)

---

## 📋 COMPLETE ALPHABETICAL LIST

### A-C

| Port | Service | Container | Type | Status |
|------|---------|-----------|------|--------|
| 5000 | hyper-mission-api | hyper-mission-api | Internal | ✅ UP |
| 5432 | postgres | postgres | Internal | ✅ UP |
| 6379 | redis | redis | Internal | ✅ UP |
| 8000 | hypercode-core | hypercode-core | 127.0.0.1 | ✅ UP |
| 8000 | celery-worker | celery-worker | Internal | 🟡 UNHEALTHY |
| 8000 | chroma-mcp | chroma-mcp | Internal | ✅ UP |
| 8003 | backend-specialist | backend-specialist | 0.0.0.0 | ✅ UP |
| 8009 | chroma | b052a6426814_chroma | 127.0.0.1 | ✅ UP |
| 8010 | healer-agent | healer-agent | 0.0.0.0 | ✅ UP |
| 8013 | test-agent | test-agent | 0.0.0.0 | ✅ UP |
| 8014 | throttle-agent | throttle-agent | 0.0.0.0 | ✅ UP |
| 8080 | openshell-cluster | openshell-cluster-nemoclaw | 0.0.0.0 | 🟢 UP |
| 8081 | crew-orchestrator | crew-orchestrator | 0.0.0.0 | ✅ UP |
| 8082 | mcp-github | mcp-github | Internal | ✅ UP |
| 8088 | hypercode-dashboard | hypercode-dashboard | 127.0.0.1 | 🟡 UNHEALTHY |
| 8099 | hyper-mission-ui | hyper-mission-ui | 127.0.0.1 | ✅ UP |
| 8820 | mcp-gateway | mcp-gateway | 127.0.0.1 | ✅ UP |
| 8821 | mcp-rest-adapter | mcp-rest-adapter | 127.0.0.1 | ✅ UP |
| 9000 | minio | minio | 127.0.0.1 | ✅ UP |
| 9001 | minio | minio | 127.0.0.1 | ✅ UP |
| 9100 | node-exporter | node-exporter | 0.0.0.0 | ✅ UP |
| 9101 | mcp-exporter | mcp-exporter | 0.0.0.0 | ✅ UP |
| 9808 | celery-exporter | celery-exporter | 0.0.0.0 | ✅ UP |
| 30051 | openshell (internal) | openshell-cluster | Internal | 🟢 UP |
| 59080 | pgadmin | pgadmin4_embedded... | 0.0.0.0 | ✅ UP |

---

## 🎯 PORTS BY SERVICE CATEGORY

### **Core APIs** 🟢
```
8000  hypercode-core (main)       127.0.0.1  ✅
8081  crew-orchestrator           0.0.0.0    ✅
8088  hypercode-dashboard         127.0.0.1  🟡 (starting)
8099  hyper-mission-ui            127.0.0.1  ✅
5000  hyper-mission-api           Internal   ✅
```

### **Agents** 🤖
```
8013  test-agent                  0.0.0.0    ✅ (UPGRADED)
8014  throttle-agent              0.0.0.0    ✅ (NEW!)
8010  healer-agent                0.0.0.0    ✅
8003  backend-specialist          0.0.0.0    ✅
```

### **Data & Storage** 💾
```
5432  postgres (database)         Internal   ✅
6379  redis (cache)               Internal   ✅
9000  minio (S3 API)              127.0.0.1  ✅
9001  minio (console)             127.0.0.1  ✅
8009  chroma (vector DB)          127.0.0.1  ✅
```

### **Monitoring & Metrics** 📊
```
9100  node-exporter               0.0.0.0    ✅
9101  mcp-exporter                0.0.0.0    ✅
9808  celery-exporter             0.0.0.0    ✅
```

**Note**: Prometheus (9090), Grafana (3001), Loki (3100), Tempo (3200) are STOPPED for cooling.

### **Integration & MCP** 🔗
```
8820  mcp-gateway                 127.0.0.1  ✅
8821  mcp-rest-adapter            127.0.0.1  ✅
8082  mcp-github                  Internal   ✅
```

### **Admin & Management** 🛠️
```
59080 pgadmin4                     0.0.0.0    ✅
8811  docker-extension             0.0.0.0    ✅
8080  openshell-cluster            0.0.0.0    🟢 (starting)
```

### **Task Processing** ⚙️
```
8000  celery-worker                Internal   🟡 (unhealthy)
9808  celery-exporter              0.0.0.0    ✅
```

---

## 🌐 QUICK ACCESS GUIDE

### **From Your Machine** (localhost)

**Public Ports** (accessible via IP):
```
http://localhost:8013          test-agent (UPGRADED)
http://localhost:8014          throttle-agent (NEW)
http://localhost:8010          healer-agent
http://localhost:8003          backend-specialist
http://localhost:8081          crew-orchestrator
http://localhost:9100          node-exporter
http://localhost:9101          mcp-exporter
http://localhost:9808          celery-exporter
http://localhost:59080         pgadmin
http://localhost:8811          docker-extension
http://localhost:8080          openshell-cluster
```

**Internal Ports** (localhost only):
```
http://localhost:8000          hypercode-core (main API)
http://localhost:8088          hypercode-dashboard
http://localhost:8099          hyper-mission-ui
http://localhost:8821          mcp-rest-adapter
http://localhost:8820          mcp-gateway
http://localhost:9000          minio (S3 API)
http://localhost:9001          minio (console)
http://localhost:8009          chroma (vector DB)
```

**Databases** (internal):
```
postgresql://localhost:5432    postgres
redis://localhost:6379         redis
```

---

## 📱 FROM ANOTHER MACHINE

Use your computer's IP address instead of localhost:

```
http://<YOUR-IP>:8013          test-agent
http://<YOUR-IP>:8014          throttle-agent
http://<YOUR-IP>:8010          healer-agent
http://<YOUR-IP>:8003          backend-specialist
http://<YOUR-IP>:8081          orchestrator
http://<YOUR-IP>:59080         pgadmin
http://<YOUR-IP>:8811          docker-extension
```

**Find your IP**:
```bash
# Windows
ipconfig
# Look for IPv4 Address (e.g., 192.168.1.100)

# Mac/Linux
ifconfig
# Look for inet 192.168.x.x
```

Then use: `http://192.168.x.x:PORT`

---

## 🔒 PORT SECURITY

### **Publicly Exposed** (0.0.0.0 - Network accessible)
- 8013, 8014, 8010, 8003, 8081, 8080, 8811, 9100, 9101, 9808, 59080
- **Risk**: Medium (exposed to network)
- **Recommendation**: Use firewall to restrict access

### **Localhost Only** (127.0.0.1 - Local machine only)
- 8000, 8088, 8099, 8821, 8820, 9000, 9001, 8009
- **Risk**: Low (only accessible locally)
- **Recommendation**: Safe for sensitive data

### **Internal** (Docker network only)
- 5000, 5432, 6379, 8000, 8082
- **Risk**: Minimal (isolated to Docker network)
- **Recommendation**: Most secure

---

## ⚠️ COMMON PORT CONFLICTS

If you get "port already in use" errors:

```bash
# Find what's using a port (Windows)
netstat -ano | findstr :8014

# Kill process using that port (Windows)
taskkill /PID <PID> /F

# Find port (Mac/Linux)
lsof -i :8014

# Kill process (Mac/Linux)
kill -9 <PID>
```

Or use different port in docker-compose.yml:
```yaml
ports:
  - "8015:8014"  # Change 8014 to 8015
```

---

## 📊 STOPPED SERVICES (Cooled Down)

These were running but are NOW STOPPED for cooling:

| Port | Service | Status | How to Restart |
|------|---------|--------|-----------------|
| 9090 | prometheus | ⛔ Stopped | `docker-compose up -d prometheus` |
| 3001 | grafana | ⛔ Stopped | `docker-compose up -d grafana` |
| 3100 | loki | ⛔ Stopped | `docker-compose up -d loki` |
| 3200 | tempo | ⛔ Stopped | `docker-compose up -d tempo` |
| 4317-4318 | tempo OTLP | ⛔ Stopped | `docker-compose up -d tempo` |
| 9412 | tempo Jaeger | ⛔ Stopped | `docker-compose up -d tempo` |
| 8090 | cadvisor | ⛔ Stopped | `docker-compose up -d cadvisor` |
| 11434 | ollama | ⛔ Stopped | `docker stop ollama; docker run -d ollama/ollama` |

---

## 🧪 TEST PORTS

Quick health check:

```bash
# Test core API
curl http://localhost:8000/health

# Test new agents
curl http://localhost:8013/health     # test-agent
curl http://localhost:8014/health     # throttle-agent

# Test healer
curl http://localhost:8010/health

# Test orchestrator
curl http://localhost:8081/health

# Test database (from Docker)
docker exec postgres psql -U postgres -d hypercode -c "SELECT 1;"
```

---

## 📝 EXPORT/PRINT THIS LIST

```bash
# Save to file
docker ps --format "table {{.Names}}\t{{.Ports}}" > ports_list.txt

# Get JSON format
docker ps --format "json" > ports_list.json
```

---

## 🎯 SUMMARY

| Type | Count | Examples | Status |
|------|-------|----------|--------|
| **Public (0.0.0.0)** | 11 | 8013, 8014, 8010, 8003, 8081 | 🟢 UP |
| **Localhost (127.0.0.1)** | 8 | 8000, 8099, 9000, 9001 | 🟢 UP |
| **Internal (Docker)** | 8 | 5432, 6379, 5000, 8082 | 🟢 UP |
| **Stopped (Cooling)** | 10 | 9090, 3001, 3100, 3200 | ⛔ DOWN |
| **TOTAL ACTIVE** | 27 | All listed above | 🟢 OPERATIONAL |

---

**All Ports Listed & Current!** ✅

*Generated: March 19, 2026*  
*HyperCode V2.0*  
*By: Gordon*
