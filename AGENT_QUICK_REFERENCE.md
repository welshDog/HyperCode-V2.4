# 🤖 HYPERCODE V2.4 — QUICK REFERENCE CARD
**25-Agent Squad | May 21, 2026**

---

## 🚀 ONE-LINE LAUNCH

```bash
.\scripts\launch-all-agents.ps1
```

---

## 📊 WHAT YOU'RE GETTING

| Category | Count | Status |
|----------|-------|--------|
| **Total Agents** | 25 | 🔴 MISSING → 🟢 DEPLOY |
| **Core Crew** | 5 | Orchestration brain |
| **Specialists** | 8 | Dev team (frontend, backend, DB, QA, DevOps, security, system, strategy) |
| **Infrastructure** | 8 | System coordination (monitoring, testing, MCP gateway) |
| **Utility** | 4 | Support (session, decomposition, PR review, business) |
| **Ports** | 22 | 8001-8100 (spread across tiers) |
| **Total RAM** | ~31GB | System-wide allocation |
| **Startup Time** | 20-25 mins | Full squad operational |

---

## 🔧 DEPENDENCY UPGRADES (CRITICAL)

| Package | Old | New | Why |
|---------|-----|-----|-----|
| **GitPython** | 3.1.45 | 3.1.47 | 🔴 CVE-2026-42215 + 42284 |
| **FastAPI** | 0.135.3 | 0.141.0 | Performance + 30 bug fixes |
| **SQLAlchemy** | 2.0.48 | 2.1.10 | Async pool optimizations |
| **Stripe** | 10.0.0 | 13.0.0 | Webhook v5 signing |
| **OpenAI** | 1.98.0 | 1.30.0+ | o1 models, structured output |

**File:** `backend/requirements-UPGRADED.txt` (ready to use)

---

## 🎯 CORE CREW (5 agents) — START THESE FIRST

| Port | Agent | Role | Memory |
|------|-------|------|--------|
| 8081 | **crew-orchestrator** | Task dispatcher | 1.5GB |
| 8083 | **agent-x** | Meta-architect | 2GB |
| 8082 | **brain-agent** | Memory core | 1GB |
| 8002 | **coder-agent** | Code gen | 1.5GB |
| 8011 | **tips-tricks-writer** | Docs | 512MB |

**Test:** `curl http://localhost:8081/health`

---

## 🛠️ SPECIALIST SQUAD (8 agents) — DEV CREW

| Port | Agent | Role |
|------|-------|------|
| 8012 | frontend-specialist | React/UX |
| 8003 | backend-specialist | FastAPI |
| 8004 | database-architect | PostgreSQL |
| 8005 | qa-engineer | Testing |
| 8006 | devops-engineer | CI/CD |
| 8007 | security-engineer | OWASP |
| 8009 | system-architect | Design |
| 8001 | project-strategist | OKR |

---

## 🌐 INFRASTRUCTURE (8 agents) — COORDINATION

| Port | Agent | Role |
|------|-------|------|
| 8091 | hyper-architect | System design |
| 8092 | hyper-observer | Monitoring |
| 8093 | hyper-worker | Execution |
| 8050 | goal-keeper | Goals |
| 8014 | throttle-agent | Rate limiting |
| 8015 | super-hyper-broski-agent | Mega executor |
| 8100 | test-agent | E2E tests |
| 8823 | hypercode-mcp-server | MCP gateway |

---

## 💼 UTILITY (4 agents) — SUPPORT

| Port | Agent | Role |
|------|-------|------|
| 8097 | session-snapshot | Session recording |
| 8096 | hyper-split-agent | Task decomposition |
| 8024 | coderabbit-webhook | PR review |
| 8020 | business-agent | Revenue/economy |

---

## 📋 PRE-FLIGHT CHECKLIST

Before launching:

- [ ] **Memory:** WSL2 has ≥32GB allocated (check `%USERPROFILE%\.wslconfig`)
- [ ] **Disk:** ≥15GB free on H: drive
- [ ] **.env file:** Populated with secrets (API keys, DB URL, etc.)
- [ ] **Docker:** Running (`docker ps` works)
- [ ] **Dependency upgrade:** Ready to swap `requirements.txt`

---

## 🚀 4-PHASE LAUNCH PROCESS

### Phase 1: Preflight (2 mins)
- Docker check
- Disk space check
- .env validation
- Memory estimation

### Phase 2: Build (10-15 mins)
- Builds 25 agent Dockerfiles
- Downloads base images
- Tests builds complete

### Phase 3: Deploy (3 mins)
- `docker compose up -d` all agents
- Services start in parallel

### Phase 4: Health (1 min)
- Verifies all 25 agents respond
- Reports startup status
- Displays dashboards

**Total: 20-25 minutes end-to-end**

---

## 🔍 MONITORING DASHBOARDS

Once running:

| URL | What | Credentials |
|-----|------|-------------|
| `http://localhost:3001` | Grafana | admin / admin |
| `http://localhost:9090` | Prometheus | (public) |
| `http://localhost:8000/docs` | Core API | X-API-Key header |
| `http://localhost:8081/docs` | Crew Orchestrator | X-API-Key header |
| `http://localhost:8082/docs` | Brain Agent | X-API-Key header |

---

## 🧪 QUICK VALIDATION

After launch:

```bash
# Check all 25 are running
docker ps | grep hypercode-.*-agent | wc -l

# Test core crew
curl http://localhost:8081/health  # orchestrator
curl http://localhost:8083/health  # agent-x
curl http://localhost:8082/health  # brain

# Check memory usage
docker stats --no-stream

# View logs
docker logs crew-orchestrator
docker logs agent-x
docker logs brain-agent

# Test swarm formation
curl -X POST http://localhost:8081/swarm/form \
  -H "X-API-Key: $API_KEY" \
  -d '{"agents": 3, "timeout": 10}'
```

---

## 🛑 TROUBLESHOOTING QUICK FIXES

| Issue | Fix |
|-------|-----|
| **OOM (Out of Memory)** | Increase WSL2 memory or reduce agent count |
| **Port already in use** | `netstat -ano \| findstr :8081` → kill PID |
| **Agent stuck starting** | Check logs: `docker logs <agent>` |
| **Network errors** | Verify networks: `docker network ls` |
| **Redis/DB not available** | Check core services: `docker ps \| grep redis` |

---

## 📊 RESOURCE ALLOCATION

```
System: ~31GB total
├─ Core services:    4GB (core, postgres, redis, etc.)
├─ Observability:    2GB (prometheus, grafana, loki, tempo)
├─ 25 Agents:        21.3GB
│  ├─ Tier 1 (5):    7.5GB
│  ├─ Tier 2 (8):    6.5GB
│  ├─ Tier 3 (8):    6GB
│  └─ Tier 4 (4):    1.3GB
└─ Buffer:           2GB
```

**Minimum system:** 64GB RAM, 32GB available for Docker

---

## 🎯 SUCCESS = 

✅ 25 agents running  
✅ All respond to /health  
✅ No OOM crashes  
✅ Prometheus ingesting metrics  
✅ Grafana dashboards populated  
✅ crew-orchestrator can route tasks  
✅ agent-x can spawn new agents  
✅ brain-agent storing context  

---

## 📂 KEY FILES

| File | Purpose |
|------|---------|
| `scripts/launch-all-agents.ps1` | Main launcher (one-click deploy) |
| `docker-compose.agents-full.yml` | 25 agent service definitions |
| `backend/requirements-UPGRADED.txt` | Updated dependencies |
| `AGENT_SQUAD_BUILD_PLAN.md` | Detailed implementation guide |
| `AGENT_DEPLOYMENT_REPORT.md` | Comprehensive status report |

---

## 🚀 NEXT STEPS

1. **Update deps:** Copy `requirements-UPGRADED.txt` → `requirements.txt`
2. **Launch:** Run `.\scripts\launch-all-agents.ps1`
3. **Monitor:** Check `docker ps` and Grafana dashboards
4. **Test:** Run smoke tests and swarm formation
5. **Celebrate:** You just deployed 25 agents! 🎉

---

## 💡 REMEMBER

- **Tier 1 (core):** Always keep running — they orchestrate everything
- **Tier 2 (specialists):** Dev team — can restart individually
- **Tier 3 (infra):** System helpers — optional but recommended
- **Tier 4 (utility):** Nice-to-have — disable if memory constrained

---

## 🔐 SECURITY

✅ All secrets in .env (never in images)  
✅ Docker network isolation  
✅ Memory limits prevent DoS  
✅ Health checks catch failures  
✅ Prometheus audit trails  

---

## 📞 SUPPORT

**Logs:** `docker compose logs -f <agent>`  
**Status:** `docker ps`  
**Metrics:** `http://localhost:9090`  
**Dashboard:** `http://localhost:3001`  

---

**Ready to activate the full squad? → `.\scripts\launch-all-agents.ps1` 🚀♾️**
