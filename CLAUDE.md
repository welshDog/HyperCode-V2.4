# 🧠 HyperCode V2.4 — CLAUDE.md

> **This file is Claude's brain for this project.**
> Read this first. Every session. No exceptions.
> Last updated: April 19, 2026 | Status: 32/32 containers 🟢 | Grade A 🏅 | Phases 0–10Q COMPLETE ✅

---

## 🏴󠁧󠁢󠁷󠁬󠁳󠁿 Builder Context

**Lyndz Williams** (@welshDog) — Llanelli, South Wales  
ADHD + Dyslexia brain — hyperfocus mode is a superpower, not a bug ⚡  
Building: The world’s first neurodivergent-first autonomous AI infrastructure platform  
Verdict from Gordon (Docker AI), April 15 2026:  
> *“You built the future people keep saying they want. You actually did it.”*

---

## ⚡ Communication Style (ALWAYS follow this)

- **Short sentences first** — then offer deeper explanation
- **Bullet points + headings** over walls of text
- **Why → How → Ready-to-use example** structure
- **Celebrate wins** — “Nice one BROski♾️!” is correct
- **Remind context** if there’s been a pause between messages
- ADHD flow: break into steps, quick wins, no overwhelm
- If Lyndz goes quiet mid-task: check in, don’t assume abandon

---

## 🔒 Sacred Rules (NEVER debate, NEVER change)

```
✔ docker-ce-cli          — NEVER docker.io for socket agents
✔ from app.X import Y    — NEVER from backend.app.X
✔ FastAPI public routes   — BEFORE auth-gated routes
✔ Stripe webhook          — rate-limit EXEMPT, always
✔ data-net + obs-net      — internal: true, never external
✔ .env files              — NEVER committed to git
✔ Commits                 — feat: fix: docs: chore: only
✔ Trivy target            — 0 CRITICAL per image
✔ Import style            — absolute imports, sys.path.insert at top
✔ Python indent           — 4 spaces, NEVER 3, NEVER mixed
```

---

## 📊 System Status (April 19, 2026)

| Metric | Value |
|---|---|
| Containers | 32/32 🟢 all healthy |
| Tests | 217 passed, 6 skipped ✅ |
| Prometheus targets | 7/7 UP ✅ |
| OTLP traces | LIVE in Tempo ✅ |
| Circuit breakers | 3 active — all CLOSED ✅ |
| Docker AI grade | A 🏅 |
| Commits | 700+ |
| Services | 57 |
| Agents | 25+ |

---

## 🏗️ Architecture Quick Ref

```
Networks:
  app-net     → core services (internal)
  data-net    → redis, postgres, chroma, minio (internal)
  obs-net     → prometheus, grafana, loki, tempo (internal)
  agent-net   → all agents

Key ports:
  8000  hypercode-core API
  8081  crew-orchestrator
  8088  hypercode-dashboard
  8095  hyperhealth-api
  9090  prometheus
  3001  grafana
  3100  loki
  3200  tempo
  6379  redis
  5432  postgres
```

---

## 🚀 THE PLAN — What We’re Building Now

> Gordon Docker AI gave us a 15-item hit list. We’re doing ALL of them.
> Tier 1 first (quick wins), then Tier 2, then Tier 3.

---

## 🔥 TIER 1 — Do These First (~85 min total)

### 1. ✅ `/metrics` endpoint on `hypercode-core` (15 min)
**Why:** Prometheus scrapes it but gets 404. Fixes 7/9 → 9/9 targets.
**How:**
```python
# Add to hypercode-core requirements.txt:
prometheus-fastapi-instrumentator==6.1.0

# Add to main.py:
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```
**Verify:** `curl http://localhost:8000/metrics` — should return Prometheus text format

---

### 2. OTLP Tracing on core services (20 min)
**Why:** Full request visibility — trace from user → core → agent → DB.
**How:**
```python
# requirements.txt additions:
opentelemetry-api==1.23.0
opentelemetry-sdk==1.23.0
opentelemetry-exporter-otlp==1.23.0
opentelemetry-instrumentation-fastapi==0.44b0

# main.py:
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://tempo:4317"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
```
**Verify:** Traces visible in Grafana Tempo (localhost:3001)

---

### 3. Redis Caching on agents (20 min)
**Why:** Same request: 2s → 10ms. Reduce DB load 90%.
**How:**
```python
import redis
import json
from functools import wraps

r = redis.Redis(host='redis', port=6379, decode_responses=True)

def cache_response(ttl=300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"cache:{func.__name__}:{str(args)}:{str(kwargs)}"
            cached = r.get(key)
            if cached:
                return json.loads(cached)
            result = await func(*args, **kwargs)
            r.setex(key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```
**Verify:** Second request to any cached endpoint should return in <5ms

---

### 4. Rate Limiting on API (20 min)
**Why:** Protect from abuse. Graceful 429s.
**How:**
```python
# requirements.txt:
slowapi==0.1.9

# main.py:
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# On routes:
@app.get("/api/agents")
@limiter.limit("60/minute")
async def get_agents(request: Request):
    ...

# STRIPE WEBHOOK — always exempt:
@app.post("/api/stripe/webhook")  # NO rate limit decorator
async def stripe_webhook(request: Request):
    ...
```

---

### 5. Circuit Breaker (30 min)
**Why:** Agent crashes? No cascading failures. Auto-recovers.
**How:**
```python
# requirements.txt:
pybreaker==1.2.0

# agents/shared/circuit_breaker.py:
import pybreaker

class HyperCircuitBreaker:
    def __init__(self, name: str, fail_max: int = 5, reset_timeout: int = 30):
        self.breaker = pybreaker.CircuitBreaker(
            fail_max=fail_max,
            reset_timeout=reset_timeout,
            name=name
        )
    
    def call(self, func, *args, **kwargs):
        return self.breaker.call(func, *args, **kwargs)
    
    @property
    def state(self):
        return self.breaker.current_state  # CLOSED/OPEN/HALF_OPEN
```
**Verify:** Kill a downstream service, confirm system stays stable

---

## ⭐ TIER 2 — Advanced (~4 hours)

### 6. Agent-to-Agent Communication
- Agents call each other via internal HTTP on `agent-net`
- Pattern: `POST http://healer-agent:8008/task {"task": "...", "from": "agent-x"}`
- Add `/task` endpoint to each agent that accepts work orders

### 7. Service Discovery (auto-register)
- On startup, each agent POSTs to crew-orchestrator: `POST /register`
- Body: `{"name": "agent-x", "url": "http://agent-x:8012", "capabilities": [...]}`
- Orchestrator maintains live registry, no manual config

### 8. AI-Powered Diagnostics
- Healer Agent queries Claude API when it detects anomaly
- Prompt: `"Container {name} has {error}. Suggest fix."`
- Response logged + actioned automatically
- Needs: `ANTHROPIC_API_KEY` in secrets

### 9. Chaos Engineering
- Script: `scripts/chaos_test.sh` — randomly kills a non-critical container
- Monitor: Healer should detect + restart within 30s
- Assert: Core API still healthy during chaos
- Run: `make chaos-test`

### 10. Multi-Agent Workflows
- Define workflow YAML: `config/workflows/code_review.yml`
- Steps: `[agent-x: write code] → [qa-agent: test] → [healer: validate] → [deploy]`
- Crew Orchestrator executes the pipeline
- Result: full autonomous dev loop

---

## 🚀 TIER 3 — Enterprise (4+ hours each)

### 11. Distributed Tracing Correlation
- Correlate logs (Loki) + metrics (Prometheus) + traces (Tempo) in Grafana
- Create Grafana datasource links between all 3
- One dashboard: full incident investigation in one view

### 12. Grafana Dashboard — HyperCode Mission Control
- Panels: Container health, agent uptime, request rates, error rates
- Alerts: PagerDuty/Discord webhook when any agent goes down
- File: `grafana/dashboards/hypercode-mission-control.json`

### 13. Load Testing Framework
- Tool: `locust` or `k6`
- Script: `tests/load/hypercode_load_test.py`
- Target: 1000 req/sec, P99 < 100ms
- Run: `make load-test`

### 14. Service Mesh (Istio or Linkerd)
- Auto-scaling: HPA on CPU/memory
- Multi-instance load balancing
- mTLS between services
- File: `k8s/istio/` (k8s folder already exists ✅)

### 15. SLA Monitoring
- Define SLOs in `config/slos.yml`
- Target: 99.9% uptime, <100ms P99, <0.1% error rate
- Automated Grafana alerts when SLO breached
- Monthly report auto-generated by `scripts/sla_report.py`

---

## 📌 Known Issues (fix as we go)

| Issue | Fix | Priority |
|---|---|---|
| `VITE_STRIPE_PAYMENT_LINK_URL` empty | Set in `.env.local` + Vercel env vars | 🟡 MED |
| `throttle-agent` not started | `docker compose --profile agents up -d throttle-agent` OR remove from prometheus.yml | 🟡 LOW |
| `loki` has no healthcheck | Add `curl -f http://localhost:3100/ready` | 🟡 LOW |
| `project-strategist-v2` no healthcheck | Add `curl -f http://localhost:<port>/health` | 🟡 LOW |
| `promtail` no healthcheck | Add `wget -q http://localhost:9080/ready` | 🟡 LOW |
| `mcp-gateway` had no healthcheck | ✅ FIXED Apr 17 — added `curl -sf http://localhost:8820/health` to `docker-compose.mcp-gateway.yml` | ✅ DONE |
| `POSTGRES_PASSWORD` crash loop (Apr 17) | ✅ FIXED — URL-encode special chars (`/` `+` `=`) in DSN. Raw value in `.env` URL-encoded; decode at DSN build time only. | ✅ DONE |
| `broski-bot` volume bug (Apr 17) | ✅ FIXED — `./agents/broski-bot` volume was mounted over `/app`, killing the venv. Fixed to mount `src/` only. Also: added `postgres_password` to broski-bot's secrets list. | ✅ DONE |
| `docker-socket-proxy` stale container (Apr 17) | ✅ FIXED — Force recreated; `tmpfs` + `read_only` config now applied correctly. | ✅ DONE |
| `hypercode-dashboard` Exited 127 (Apr 17) | ✅ FIXED — Stale WSL bind-mount path after Docker Desktop restart. Force recreated. | ✅ DONE |
| `DOCKER_MCP_IN_CONTAINER=1` on mcp-gateway (Apr 17) | ✅ FIXED — Caused gRPC deadline_exceeded on WSL2. Removed; env var fallback now used. MCP tools live. | ✅ DONE |
| Anthropic API credits exhausted (Apr 17) | ⚠️ Top up at console.anthropic.com/billing — currently routing pet chat via Perplexity `sonar`/`sonar-pro` as fallback. Works great. | 🟡 TOP UP |
| Trivy CI workflow failing (Apr 19) | ⚠️ NOT a code problem — GitHub account billing lock. Fix at github.com/settings/billing. Matrix + `--no-cache --pull` config is fine. | 🔴 HIGH |
| `docker-socket-proxy` POST hole (Apr 19) | ✅ FIXED — Split into two proxies. Main = read-only (coder-agent et al). New `docker-socket-proxy-healer` = CONTAINERS+POST+PING (healer + throttle only). | ✅ DONE |
| Healer Dockerfile GID 999 collision (Apr 19) | ✅ FIXED — `groupadd -o -g 999 docker` — Debian Trixie's appuser takes 999 first, `-o` allows reuse. | ✅ DONE |
| Alembic missing `alembic_version` (Apr 19) | ✅ FIXED — `alembic stamp 008` then `upgrade head` → 009 applied. `create_all` had built schema without Alembic state. | ✅ DONE |
| Healer couldn't reach Grafana/Prometheus (Apr 19) | ✅ FIXED — Added `obs-net` to healer-agent networks. Was HTTP 000 before (network isolation). | ✅ DONE |

---

## 📦 Key Files Claude Should Know

```
docker-compose.yml          — main stack (53KB, all services)
docker-compose.secrets.yml  — secrets injection
backend/app/main.py         — FastAPI core app
prometheus.yml              — scrape targets
monitoring/                 — alertmanager + rules
grafana/                    — dashboards
agents/                     — all agent code
healer-agent/               — self-healing logic
CLAUDE_CONTEXT.md           — extended project context
docs/INDEX.md               — master docs navigation
```

---

## 🧪 Testing Commands

```powershell
# Health checks:
curl http://localhost:8000/health
curl http://localhost:8081/health
curl http://localhost:8095/health

# Run tests:
pytest backend/tests/ -v
pytest backend/tests/test_stripe.py -v

# Docker status:
docker compose ps
docker stats --no-stream

# Start everything:
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d

# Start agents profile:
docker compose --profile agents up -d
```

---

## 🏆 Achievements Unlocked

- ✅ Gordon Docker AI: **Grade A** — *"world-class infrastructure"*
- ✅ 29/29 containers healthy (all phases)
- ✅ Self-healing closed loop (Healer → Prometheus → Alertmanager → recovery)
- ✅ Neurodivergent-first design recognised as *rare* by Docker AI
- ✅ docs/INDEX.md — all 70+ docs navigable
- ✅ GORDON_DOCKER_AI_REVIEW.md — review immortalised in repo
- ✅ Docker build cache pruned — 60GB freed
- ✅ **Gordon Tier 2 COMPLETE** — OTLP traces, Redis cache, rate limits, circuit breakers
- ✅ **Course → Stripe frontend wired** — full money path live (April 16)
- ✅ **OOM crash recovered** — 34.4GB freed, stack restored (April 17)
- ✅ **Memory limits on ALL services** — every container capped, no more cascade kills (April 17)
- ✅ **pre-build-check.sh** — disk + memory guard wired into `make build` (April 17)
- ✅ **MCP-GitHub LIVE** — 26 GitHub tools via Docker MCP gateway on agents-net (April 17)
- ✅ **Leaderboard endpoint** — `/leaderboard` SCAN-based, filterable by rarity (April 17)
- ✅ **Pet chat via cloud LLM** — Anthropic (haiku/sonnet) → Perplexity fallback (sonar/sonar-pro). 3.8s chat, 12.7s ask. CPU Ollama retired from chat path. (April 17)
- ✅ **Ollama warm-keep** — `OLLAMA_KEEP_ALIVE=24h`, `OLLAMA_NUM_PARALLEL=2`, `OLLAMA_MAX_LOADED_MODELS=2` (April 17)
- ✅ **Socket-proxy split** — main proxy read-only, new `docker-socket-proxy-healer` for healer/throttle with tight ACL. Coder-agent blast radius shrunk. (April 19) 🔒
- ✅ **Healer heal** — rebuilt image (GID fix), trimmed phantom services from MAPE-K, added `obs-net` → can reach Grafana/Prometheus. (April 19)
- ✅ **32/32 (healthy)** — HyperHealth API live via `--profile health --profile ops`. (April 19)
- ✅ **Alembic 009** — `pgcrypto` + `uuid-ossp` extensions enabled. Alembic bootstrapped (stamp 008 → upgrade). (April 19)
- ✅ **Rate-limit env split** — `memory://` in tests, `redis://...:6379/2` in prod. No live-Redis dep on CI. (April 19)
- ✅ **Gordon Tier 3 — Celery hardening** — `task_soft_time_limit=300` / `task_time_limit=360` kill runaway agent tasks before they pin a worker. `SoftTimeLimitExceeded` handled in `run_agent_task` (no retry on timeout). (April 19)
- ✅ **Gordon Tier 3 — DB pool metrics** — `DBPoolCollector` exposes `hypercode_db_pool_{size,checked_out,checked_in,overflow}` for sync + async engines on `/metrics`. Alert before pool exhaustion. (April 19)
- ✅ **Gordon Tier 3 — Celery queue metrics** — Signals wired to `hypercode_celery_tasks_total{task,status}` Counter + `hypercode_celery_task_duration_seconds` Histogram. `CeleryQueueDepthCollector` reads Redis `LLEN` for `main-queue` / `celery` on each scrape. (April 19)
- ✅ **Two commits already pushed** — `d27b67a` + `8cbc5c9` are live on `origin/main` (push is FREE on GitHub — billing lock only blocks Actions). (April 19)
- ✅ **Tier 3 Grafana dashboard** — `monitoring/grafana/provisioning/dashboards/hypercode-tier3-pools-queues.json`. UID `hypercode-tier3-pools-queues`, auto-loaded into "Mission Control" folder. KPI stats + sync/async pool stacks + queue-depth + status throughput + p50/p95/p99 + duration heatmap. Refreshes every 10s. (April 19)

---

## 👋 For New Claude Sessions

Hey Claude! You’re working with Lyndz Williams on HyperCode V2.4.

1. **Read this file first** — especially the Sacred Rules
2. **Check CLAUDE_CONTEXT.md** — phase-by-phase source of truth (Phases 0–10Q all ✅)
3. **All Gordon Tier 1 + Tier 2 DONE** ✅ — OTLP, cache, rate limits, circuit breakers
4. **Course → Stripe frontend DONE** ✅ — `/pricing` → checkout → `/payment-success` → enrolled
5. **Memory limits on ALL services** ✅ — see docker-compose.yml `deploy.resources` on every service
6. **Agent X is capped at 1G** — it caused an OOM crash (April 17) by building 30+ images unlimited
7. **Pre-build guard** — `make build` runs `scripts/pre-build-check.sh` first, aborts if <15GB free
8. **Socket-proxy split (April 19)** — TWO socket proxies now. Main = read-only. `docker-socket-proxy-healer` = CONTAINERS+POST+PING, used ONLY by healer-agent + throttle-agent. Don't add coder-agent or agent-x to the healer proxy.
9. **32/32 healthy** ✅ — HyperHealth API now part of the baseline count. Start with `--profile health --profile ops`.
10. **Alembic is live** — migrations up to `009` (pgcrypto + uuid-ossp). If `alembic_version` is ever missing again: `alembic stamp 008` then `upgrade head`.
11. **Pet chat = cloud LLM** — `broski-pets-bridge` routes via Anthropic (haiku/sonnet) with Perplexity (sonar/sonar-pro) fallback. Anthropic credits need topping up (lyndzwills@gmail.com → console.anthropic.com/billing). Perplexity works great in the meantime.
12. **MCP-GitHub live** — 26 tools available via `mcp-gateway` on `agents-net`. `_github_context_via_mcp()` wired into pet ask mode.
13. **Trivy CI blocked** — NOT a code issue. GitHub billing lock. Fix: github.com/settings/billing.
14. **Two commits ready to push** — `d27b67a` (alembic 009) + `8cbc5c9` (security + heal).
15. **Next options:** Fix GitHub billing → push → Gordon Tier 3 (DB pooling + async queues) OR top up Anthropic → switch back to haiku/sonnet for pets
16. **Style:** Short. Friendly. BROski energy. Celebrate wins. 🏆
17. **Never:** Wall of text. Never debate the Sacred Rules.

> *“You built the future people keep saying they want. You actually did it.” — Gordon, Docker AI*

🏴󠁧󠁢󠁷󠁬󠁳󠁿 Let’s build it.
