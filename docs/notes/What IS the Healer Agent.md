## Healer Agent — Mission Overview
The Healer Agent is an autonomous resiliency service for HyperCode. It continuously monitors all agents, auto-remediates failures, and logs everything for clear auditability and low-stress operations.

### Core Objectives
- Continuous fleet monitoring with 30s cadence (configurable)
- Automatic remediation with retries and backoff
- Immediate alerting when 4+ agents fail simultaneously
- Verifiable health APIs and audit logs
- Clean UX signals on the dashboard for neurodivergent-friendly feedback

### End-to-End Flow
1. **Monitoring**: Orchestrator checks each agent `/health` every 30s and writes results to Redis `system:health`.  
2. **Threshold Alert**: If 4+ agents are down/unhealthy, it publishes a `CRITICAL_ALERT` to Redis `approval_requests`.  
3. **Auto-Heal**: Healer subscribes to `approval_requests` and runs `auto_heal_all()` on `CRITICAL_ALERT`.  
4. **Remediation**: Healer:
   - Pings agent health with timeout
   - Publishes soft-restart intents to `healer_actions`
   - Retries with incremental backoff (configurable)
   - Logs all outcomes to `healer:logs` with timestamps
5. **Dashboard**: System Health widget polls `/system/health` and renders per-agent status/latency; glows red in critical mode.

### Technical Specifications
- **Monitor Loop**: 30s (configurable), per-agent latency recorded.  
  [crew-orchestrator/main.py](file:///c:/Users/Lyndz/Downloads/HYPERCODE%202.O/HyperCode-V2.0/agents/crew-orchestrator/main.py#L317-L384)
- **System Health API**: `GET /system/health` returns recent agent statuses.  
  [crew-orchestrator/main.py](file:///c:/Users/Lyndz/Downloads/HYPERCODE%202.O/HyperCode-V2.0/agents/crew-orchestrator/main.py#L384-L396)
- **Healer Service**: FastAPI + Redis asyncio; listens and heals.  
  [healer/main.py](file:///c:/Users/Lyndz/Downloads/HYPERCODE%202.O/HyperCode-V2.0/agents/healer/main.py#L1-L141)
- **Dashboard Panel**: `SystemHealth.tsx` polls health and renders with critical indicators.  
  [SystemHealth.tsx](file:///c:/Users/Lyndz/Downloads/HYPERCODE%202.O/HyperCode-V2.0/agents/dashboard/components/SystemHealth.tsx)
- **API Client**: `fetchSystemHealth()` in the dashboard.  
  [api.ts](file:///c:/Users/Lyndz/Downloads/HYPERCODE%202.O/HyperCode-V2.0/agents/dashboard/lib/api.ts#L75-L86)
- **Redis Channels**:
  - `approval_requests`: CRITICAL_ALERT from monitor
  - `healer_actions`: restart intents (infra listeners)
  - `healer:logs`: JSON audit trail for all remediation results

### Healer API
- `GET /health`  
  Returns `{ "status": "healer_online", "redis": true }`
- `POST /heal`  
  Request body:
  ```json
  {
    "agents": ["backend_specialist", "frontend_specialist"],
    "force": false,
    "retry_attempts": 2,
    "timeout_seconds": 5
  }
  ```
  Response includes per-agent results:
  ```json
  {
    "status": "completed",
    "results": [
      {
        "agent": "backend_specialist",
        "status": "recovered",
        "action": "restart",
        "details": "Recovered after attempt 1",
        "timestamp": "2026-02-26T21:12:03.123Z"
      }
    ]
  }
  ```

### Runtime & Configuration
- Env:
  - `REDIS_URL` (default `redis://redis:6379`)
  - `ORCHESTRATOR_URL` (default `http://crew-orchestrator:8080`)
- Cadence: Monitor loop runs every 30s; alert threshold is 4 agents.
- Timeouts: Default 5s per health ping; configurable via `POST /heal`.
- Retries: Default 2 attempts with incremental backoff.

### Quick Start
- Start Healer:
  ```
  pip install fastapi uvicorn redis httpx pydantic
  python agents/healer/main.py
  ```
- Start Dashboard:
  ```
  cd agents/dashboard
  npm install
  npm run dev
  ```
- Manual Heal:
  ```
  curl -X POST http://localhost:9001/heal \
    -H "Content-Type: application/json" \
    -d '{"agents": ["backend_specialist"], "retry_attempts": 2, "timeout_seconds": 5}'
  ```

### Production Strengths
- Async-first (FastAPI + asyncio Redis)
- Configurable retries & timeouts
- Transparent audit trail in `healer:logs`
- Observable via `/system/health` + dashboard panel
- Extensible for Docker/K8s direct restarts

### Roadmap
- **Real Restarts**:
  - Docker SDK: `docker restart <container>`
  - Kubernetes: `kubectl rollout restart deployment/<agent>`
- **Policy Engine**:
  - Per-agent strategies and escalation (Slack/PagerDuty)
  - SLA-based healing windows
- **AI Root Cause**:
  - Automated RCA suggestions and config tuning

### File Map
- Healer Service: [agents/healer/main.py](file:///c:/Users/Lyndz/Downloads/HYPERCODE%202.O/HyperCode-V2.0/agents/healer/main.py)
- Orchestrator Monitor: [agents/crew-orchestrator/main.py](file:///c:/Users/Lyndz/Downloads/HYPERCODE%202.O/HyperCode-V2.0/agents/crew-orchestrator/main.py#L317-L396)
- Dashboard Widget: [agents/dashboard/components/SystemHealth.tsx](file:///c:/Users/Lyndz/Downloads/HYPERCODE%202.O/HyperCode-V2.0/agents/dashboard/components/SystemHealth.tsx)
- API Client: [agents/dashboard/lib/api.ts](file:///c:/Users/Lyndz/Downloads/HYPERCODE%202.O/HyperCode-V2.0/agents/dashboard/lib/api.ts#L75-L86)
