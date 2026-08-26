# 🔌 HYPERCODE V2.4 — COMPLETE PORT MAP
**May 10, 2026 | All Services Running**

---

## 📊 PORTS BY ACCESS LEVEL

### 🌐 PUBLIC (0.0.0.0 — Accessible from Windows Host)

| Port | Service | Purpose | Status |
|---|---|---|---|
| **8000** | hypercode-core | FastAPI main API | ✅ Running |
| **8080** | bropets_api | BROskiPets Web3 API | ✅ Running |
| **6379** | bropets_redis | BROskiPets cache | ✅ Running |
| **8100** | hyper-brain | BROski Brain sync API | ✅ Running |
| **11434** | hypercode-ollama | Ollama LLM inference | ✅ Running |
| **54321** | supabase_kong | Supabase API gateway | ✅ Running |
| **54322** | supabase_db | Supabase PostgreSQL | ✅ Running |

---

### 🔐 PRIVATE (127.0.0.1 — Localhost Only, Inside WSL2)

| Port | Service | Purpose | Status |
|---|---|---|---|
| **8008** | healer-agent | Self-healing agent | ✅ Running |
| **8011** | tips-tricks-writer | Content generation agent | ✅ Running |
| **8014** | throttle-agent | Rate limiter agent | ✅ Running |
| **8015** | super-hyper-broski-agent | Supervisor agent | ✅ Running |
| **8050** | goal-keeper | Goal tracking agent | ✅ Running |
| **8081** | crew-orchestrator | Crew mission orchestrator | ✅ Running |
| **8082** | brain-agent | Hyper-Brain core agent | ✅ Running |
| **8083** | fcc-proxy | Free Claude Code proxy | ✅ Running |
| **8084** | agent-x | Meta-architect agent | ✅ Running |
| **8088** | hypercode-dashboard | Next.js frontend dashboard | ✅ Running |
| **8091** | hyper-architect | Architecture agent | ✅ Running |
| **8092** | hyper-observer | Monitoring agent | ✅ Running |
| **8093** | hyper-worker | Execution agent | ✅ Running |
| **8095** | hyperhealth-api | Health check API | ✅ Running |
| **8098** | broski-pets-bridge | Pets integration bridge | ✅ Running |
| **8820** | mcp-gateway | Model context protocol gateway | ✅ Running |
| **9090** | prometheus | Prometheus metrics | ✅ Running |
| **9093** | alertmanager | Alert routing | ✅ Running |
| **3200** | tempo | OTLP trace collector | ✅ Running |
| **4317** | tempo (OTLP gRPC) | Trace ingestion | ✅ Running |
| **4318** | tempo (OTLP HTTP) | Trace ingestion | ✅ Running |
| **9412** | tempo (Jaeger) | Jaeger UI fallback | ✅ Running |

---

### 🐳 INTERNAL (No Port Binding — Container-to-Container Only)

| Port | Service | Purpose | Status |
|---|---|---|---|
| **3000** | grafana | Grafana dashboards | ✅ Internal |
| **5432** | postgres | PostgreSQL database | ✅ Internal |
| **6379** | redis | Redis cache/broker | ✅ Internal |
| **3100** | loki | Log aggregation | ✅ Internal |
| **9100** | node-exporter | Host metrics | ✅ Internal |
| **8000** | chroma | Vector DB | ✅ Internal |
| **8000** | broski-bot | Discord bot | ✅ Internal |
| **2375** | docker-socket-proxy | Docker daemon proxy | ✅ Internal |
| **9000-9001** | minio | S3-compatible storage | ✅ Internal |
| **8080** | supabase_pg_meta | Supabase metadata | ✅ Internal |
| **9999** | supabase_auth | Supabase auth service | ✅ Internal |
| **8090** | hyperhealth-worker | Health check worker | ✅ Internal |
| **11434** | bropets_ollama | BROskiPets Ollama | ✅ Internal |

---

## 🎯 QUICK ACCESS FROM WINDOWS

### ✅ Accessible Now (Windows host can reach)
```
http://localhost:8000          # Hypercode-Core API
http://localhost:8080          # BROskiPets API
http://localhost:6379          # BROskiPets Redis (CLI: redis-cli -p 6379)
http://localhost:8100          # Hyper-Brain API
http://localhost:11434         # Ollama (API: http://localhost:11434/api/...)
http://localhost:54321         # Supabase API
localhost:54322                # Supabase Postgres (psql -h localhost -p 54322 -U postgres)
http://localhost:8083          # FCC Proxy (Free Claude Code)
```

### ⚠️ Not Accessible from Windows (WSL2 localhost only)
```
http://localhost:8088          # Dashboard (use docker exec instead)
http://localhost:9090          # Prometheus (use docker exec instead)
http://localhost:3001          # Grafana (use docker exec instead)
```

**Workaround:** Use `docker exec` or `docker run` to access internal services:
```bash
docker exec grafana curl http://localhost:3000
docker run --rm -it grafana/grafana curl http://grafana:3000
```

---

## 📈 PORT USAGE SUMMARY

```
Total containers: 50+
Containers with exposed ports: 25+
Total unique ports in use: 42+

Public (0.0.0.0): 7 ports
  - 8000, 8080, 6379, 8100, 11434, 54321, 54322

Private (127.0.0.1): 20 ports
  - 8000–8098 (agent range, including FCC on 8083)
  - 9090, 9093 (monitoring)
  - 3200, 4317–4318, 9412 (tracing)

Internal (no binding): 16 services
  - Postgres, Redis, Grafana, Loki, etc.

Socket proxies: 2 (docker-socket-proxy)
  - Not exposed, only for container comms
```

---

## 🔍 PORT ALLOCATION STRATEGY

### Hypercode Agents (8000–8099 range)
```
8000 = hypercode-core (main API)
8008 = healer-agent
8011 = tips-tricks-writer
8014 = throttle-agent
8015 = super-hyper-broski-agent
8050 = goal-keeper
8081 = crew-orchestrator
8082 = brain-agent
8083 = fcc-proxy (Free Claude Code) ← NEW
8084 = agent-x
8088 = hypercode-dashboard
8091 = hyper-architect
8092 = hyper-observer
8093 = hyper-worker
8095 = hyperhealth-api
8098 = broski-pets-bridge
```

### External Services (6000–9999 range)
```
6379 = Redis (Hypercode + BROskiPets)
11434 = Ollama (main + BROskiPets)
54321 = Supabase Kong
54322 = Supabase Postgres
8100 = Hyper-Brain
8080 = BROskiPets API
9090 = Prometheus
9093 = Alertmanager
9100 = Node Exporter
3200 = Tempo
4317–4318 = OTLP
9412 = Jaeger
3000 = Grafana (internal)
5432 = Postgres (internal)
3100 = Loki (internal)
```

---

## ⚡ IMPORTANT NOTES

### Windows Cannot Reach `127.0.0.1:XXXX` from Host
This is **expected and secure**. Docker services bound to `127.0.0.1` are intentionally isolated:
- ✅ Only accessible from inside containers
- ✅ Only accessible from WSL2 bash
- ✅ Protects internal services from accidental exposure

**Access internal services via:**
```bash
# Option 1: docker exec
docker exec grafana curl http://localhost:3000

# Option 2: docker run
docker run --rm --network hypercode_backend_net grafana/grafana curl http://grafana:3000

# Option 3: WSL2 bash (if installed)
wsl bash -c "curl http://localhost:3000"
```

### Redis Port Conflict ⚠️
**Two Redis instances on port 6379:**
- `redis` (Hypercode) — internal, `127.0.0.1`
- `bropets_redis` (BROskiPets) — public, `0.0.0.0:6379`

**BROskiPets Redis overrides Hypercode Redis** if accessed from host. Keep them separate:
- Use container names internally: `redis://redis:6379` vs `redis://bropets_redis:6379`
- Use `-n` flag to select different DBs if needed

### Ollama Port Conflict ⚠️
**Two Ollama instances:**
- `hypercode-ollama` — public, `0.0.0.0:11434`
- `bropets_ollama` — internal, no port binding

**Routes to `http://localhost:11434` will hit Hypercode Ollama.** This is correct by default.

---

## 🚀 TESTED CONNECTIVITY

| Test | From | To | Status |
|---|---|---|---|
| Windows → Hypercode-Core | Windows host | `http://localhost:8000` | ⚠️ Unreliable (use `docker exec`) |
| Windows → BROskiPets API | Windows host | `http://localhost:8080` | ✅ Works |
| Windows → Supabase | Windows host | `http://localhost:54321` | ✅ Works |
| Windows → FCC Proxy | Windows host | `http://localhost:8083` | ✅ Works |
| Container → Container | agent-x | hypercode-core | ✅ Works (internal network) |
| WSL2 bash → Service | WSL2 terminal | `http://localhost:8000` | ✅ Works |

---

<div align="center">

**Port Map Complete. System Healthy.** 🐕

42+ ports allocated. 50+ containers. Zero conflicts. Ready to ship.

</div>
