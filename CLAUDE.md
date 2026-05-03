# 🧠 HyperCode V2.4 — CLAUDE.md

> **This file is Claude's brain for this project.**
> Read this first. Every session. No exceptions.
> Last updated: May 3, 2026 (session wrap) | Status: 48/48 containers 🟢 | Grade A 🏅 | Phases 0–10Q COMPLETE ✅

---

## 🏴󠁧󠁢󠁷󠁬󠁳󠁿 Builder Context

**Lyndz Williams** (@welshDog) — Llanelli, South Wales  
ADHD + Dyslexia brain — hyperfocus mode is a superpower, not a bug ⚡  
Building: The world's first neurodivergent-first autonomous AI infrastructure platform  
Verdict from Gordon (Docker AI), April 15 2026:  
> *"You built the future people keep saying they want. You actually did it."*

---

## ⚡ Communication Style (ALWAYS follow this)

- **Short sentences first** — then offer deeper explanation
- **Bullet points + headings** over walls of text
- **Why → How → Ready-to-use example** structure
- **Celebrate wins** — "Nice one BROski♾️!" is correct
- **Remind context** if there's been a pause between messages
- ADHD flow: break into steps, quick wins, no overwhelm
- If Lyndz goes quiet mid-task: check in, don't assume abandon

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

## 📊 System Status (May 3, 2026 — End of Day)

| Metric | Value |
|---|---|
| Containers | 48 running (post-cleanup) 🟢 |
| Tests | 221 passed, 6 skipped ✅ |
| E2E shop-purchase test | ✅ PASSING against prod Supabase |
| Prometheus targets | 7/7 UP ✅ |
| OTLP traces | LIVE in Tempo ✅ |
| Circuit breakers | 3 active — all CLOSED ✅ |
| Docker AI grade | A 🏅 |
| Commits | 700+ |
| Services | 57 |
| Agents | 25+ |
| Docker storage reclaimed | ~30 GB freed ✅ |
| Security headers | 6/6 firing ✅ (fixed May 3) |
| /welcome onboarding page | ✅ LIVE on Vercel |

---

## 🐳 Docker Health (May 3, 2026 — Post Cleanup)

**Report from Docker AI — actioned same day ✅**

| Metric | Before | After |
|---|---|---|
| Exited containers | 11 | 0 ✅ |
| Build cache | 33.24 GB | ~0 ✅ |
| Storage reclaimed | — | ~30 GB ✅ |
| Running containers | 48 | 48 ✅ |

**Notes:**
- 8 hypercode-v24 agent containers exited code 255 (port conflicts / resource exhaustion) — pruned
- WSL2 memory: 5.1 GB — monitor with `docker stats` (48 containers running)
- hypercode-core: 2.5 GB image — multi-stage optimisation future win (target ~500 MB)
- crew-orchestrator: 1.45 GB — target ~350 MB
- 12 custom bridge networks — consolidation is medium-term

**Weekly maintenance:**
```powershell
docker system prune -a --filter "until=168h"
```

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
  8002  hypercode-ai API (profile: ai)
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

## 🚀 THE PLAN — What We're Building Now

> Gordon Docker AI gave us a 15-item hit list. We're doing ALL of them.
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
- One dashboard: full incident investigation in one view

### 12. Grafana Dashboard — HyperCode Mission Control
- Panels: Container health, agent uptime, request rates, error rates
- Alerts: Discord webhook when any agent goes down
- File: `grafana/dashboards/hypercode-mission-control.json`

### 13. Load Testing Framework
- Tool: `locust` or `k6`
- Target: 1000 req/sec, P99 < 100ms
- Run: `make load-test`

### 14. Service Mesh (Istio or Linkerd)
- Auto-scaling HPA, mTLS between services
- File: `k8s/istio/` (k8s folder already exists ✅)

### 15. SLA Monitoring
- Define SLOs in `config/slos.yml`
- Target: 99.9% uptime, <100ms P99, <0.1% error rate
- Monthly report: `scripts/sla_report.py`

---

## 📌 Known Issues (fix as we go)

| Issue | Fix | Priority |
|---|---|---|
| `VITE_STRIPE_PAYMENT_LINK_URL` empty | Set in `.env.local` + Vercel env vars | 🟡 MED |
| `throttle-agent` not started | `docker compose --profile agents up -d throttle-agent` | 🟡 LOW |
| `loki` no healthcheck | Add `curl -f http://localhost:3100/ready` | 🟡 LOW |
| `project-strategist-v2` no healthcheck | Add `curl -f http://localhost:<port>/health` | 🟡 LOW |
| `promtail` no healthcheck | Add `wget -q http://localhost:9080/ready` | 🟡 LOW |
| `mcp-gateway` healthcheck | ✅ FIXED Apr 17 | ✅ DONE |
| `POSTGRES_PASSWORD` crash loop (Apr 17) | ✅ FIXED — URL-encode special chars in DSN | ✅ DONE |
| `broski-bot` volume bug (Apr 17) | ✅ FIXED — mount `src/` only | ✅ DONE |
| `docker-socket-proxy` stale (Apr 17) | ✅ FIXED — force recreated | ✅ DONE |
| `hypercode-dashboard` Exited 127 (Apr 17) | ✅ FIXED — stale WSL bind-mount, recreated | ✅ DONE |
| `DOCKER_MCP_IN_CONTAINER=1` (Apr 17) | ✅ FIXED — removed, env fallback used | ✅ DONE |
| Anthropic API credits (Apr 17) | ⚠️ Top up console.anthropic.com/billing — Perplexity fallback working | 🟡 TOP UP |
| Trivy CI failing (Apr 19) | ⚠️ GitHub billing lock — NOT code. Fix: github.com/settings/billing | 🔴 HIGH |
| `docker-socket-proxy` POST hole (Apr 19) | ✅ FIXED — split proxies, healer-only write access | ✅ DONE |
| Healer GID 999 collision (Apr 19) | ✅ FIXED — `groupadd -o -g 999 docker` | ✅ DONE |
| Alembic missing `alembic_version` (Apr 19) | ✅ FIXED — `alembic stamp 008` then `upgrade head` | ✅ DONE |
| Healer couldn't reach obs-net (Apr 19) | ✅ FIXED — added `obs-net` to healer networks | ✅ DONE |
| 11 exited containers (May 3) | ✅ FIXED — `docker container prune -f` + builder prune. ~30 GB reclaimed | ✅ DONE |
| Stripe webhook secret stale (May 3) | ⚠️ Update from Stripe Dashboard → `supabase secrets set STRIPE_WEBHOOK_SECRET=whsec_...` → redeploy | 🔴 HIGH |
| Security headers only 1/6 firing (May 3) | ✅ FIXED — created `frontend/vercel.json` (Vercel reads frontend/, not repo root) | ✅ DONE |

---

## 📦 Key Files Claude Should Know

```
docker-compose.yml              — main stack (53KB, all services)
docker-compose.secrets.yml      — secrets injection
backend/app/main.py             — FastAPI core app
frontend/vercel.json            — Vercel config + security headers (May 3)
frontend/src/pages/Welcome.tsx  — hero onboarding page (May 3)
frontend/src/pages/Auth.tsx     — first-login redirect to /welcome
scripts/Test-ShopPurchase.ps1   — E2E shop-purchase test (May 3)
prometheus.yml                  — scrape targets
monitoring/                     — alertmanager + rules
grafana/                        — dashboards
agents/                         — all agent code
healer-agent/                   — self-healing logic
CLAUDE_CONTEXT.md               — extended project context
docs/INDEX.md                   — master docs navigation
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

# E2E shop-purchase test:
pwsh scripts/Test-ShopPurchase.ps1

# Docker status:
docker compose ps
docker stats --no-stream

# Start everything:
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d

# Start agents profile:
docker compose --profile agents up -d

# Weekly Docker cleanup:
docker system prune -a --filter "until=168h"

# Test onboarding page locally:
cd frontend && npm run dev  # hit http://localhost:5173/welcome
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
- ✅ **Pet chat via cloud LLM** — Anthropic → Perplexity fallback. 3.8s chat, 12.7s ask. (April 17)
- ✅ **Ollama warm-keep** — `OLLAMA_KEEP_ALIVE=24h`, `NUM_PARALLEL=2`, `MAX_LOADED=2` (April 17)
- ✅ **Socket-proxy split** — main read-only, healer proxy write-only. Blast radius shrunk. (April 19) 🔒
- ✅ **Healer heal** — GID fix, obs-net added, phantom services trimmed. (April 19)
- ✅ **32/32 healthy** — HyperHealth API live via `--profile health --profile ops`. (April 19)
- ✅ **Alembic 009** — pgcrypto + uuid-ossp. Bootstrapped stamp 008 → upgrade. (April 19)
- ✅ **Rate-limit env split** — `memory://` in tests, Redis in prod. (April 19)
- ✅ **Gordon Tier 3 — Celery hardening** — soft/hard time limits, DLQ on max retries. (April 19)
- ✅ **Gordon Tier 3 — DB pool metrics** — `DBPoolCollector` on `/metrics`. (April 19)
- ✅ **Gordon Tier 3 — Celery queue metrics** — Counter + Histogram + Redis LLEN depth. (April 19)
- ✅ **Tier 3 Grafana dashboard** — KPI stats, pool stacks, queue depth, DLQ, heatmap. 10s refresh. (April 19)
- ✅ **Tier 3 Prometheus alerts** — 10 alerts: DB pool (3) + Celery (7 incl. DLQ). (April 19)
- ✅ **Tier 3 priority queues + DLQ** — high/normal/low + dlq capped at 10k. (April 19)
- ✅ **Stripe prod swap runbook** — `docs/runbooks/stripe-prod-swap.md`. (April 19)
- ✅ **Anthropic top-up runbook** — zero code change needed on credits restore. (April 19)
- ✅ **Referral system COMPLETE** — BRO-codes, ReferralCard, hardened `handle_new_user()`, migration `20260503000029` applied to prod. (May 3)
- ✅ **Docker full cleanup** — 11 exited pruned, 33 GB cache cleared, ~30 GB reclaimed. (May 3)
- ✅ **Stripe webhook diagnosed** — `STRIPE_WEBHOOK_SECRET` stale. Code v25 solid. Fix pending. (May 3)
- ✅ **E2E shop-purchase test** — `scripts/Test-ShopPurchase.ps1` passing against prod Supabase. (May 3)
- ✅ **Blockers B1-B3 confirmed wired** — all three confirmed live. (May 3)
- ✅ **/welcome hero onboarding page** — `frontend/src/pages/Welcome.tsx`, gated by `user_metadata.onboarded_at`. First-login redirect from Auth.tsx. LIVE on Vercel. (May 3)
- ✅ **Security headers fix** — `frontend/vercel.json` created. Was only 1/6 firing (Vercel reads `frontend/`, not repo root). Now 6/6 ✅. (May 3)
- ✅ **Speed Insights regression found + fixed** — `@vercel/speed-insights` installed, real LCP/TTFB regression identified and resolved. (May 3)

---

## 👋 For New Claude Sessions

Hey Claude! You're working with Lyndz Williams on HyperCode V2.4.

1. **Read this file first** — especially the Sacred Rules
2. **Check CLAUDE_CONTEXT.md** — phase-by-phase source of truth (Phases 0–10Q all ✅)
3. **All Gordon Tier 1 + 2 + 3 DONE** ✅
4. **Course → Stripe frontend DONE** ✅ — `/pricing` → checkout → `/payment-success` → enrolled
5. **Memory limits on ALL services** ✅ — every container capped
6. **Agent X capped at 1G** — OOM crash history (April 17)
7. **Pre-build guard** — `make build` runs `pre-build-check.sh`, aborts if <15GB free
8. **Socket-proxy split** — main = read-only. healer proxy = CONTAINERS+POST+PING only
9. **48 running (May 3)** ✅ — post-cleanup baseline. `--profile health --profile ops`
10. **Alembic live** — up to migration 009. If missing: `alembic stamp 008` → `upgrade head`
11. **Pet chat = cloud LLM** — Anthropic → Perplexity fallback. Top up console.anthropic.com/billing
12. **MCP-GitHub live** — 26 tools via `mcp-gateway` on `agents-net`
13. **Trivy CI blocked** — GitHub billing lock. Fix: github.com/settings/billing 🔴
14. **Referral system live** — BRO-codes + ReferralCard + hardened trigger. Prod Supabase. (May 3)
15. **Docker cleaned** — 48 containers, WSL2 5.1 GB. Weekly: `docker system prune -a --filter "until=168h"`
16. **Stripe webhook secret stale** 🔴 — `supabase secrets set STRIPE_WEBHOOK_SECRET=whsec_...` → redeploy
17. **Security headers FIXED** ✅ — `frontend/vercel.json` is the correct location, not repo root
18. **/welcome page LIVE** ✅ — gated by `onboarded_at`. First student can be invited NOW.
19. **E2E test passing** ✅ — `pwsh scripts/Test-ShopPurchase.ps1` against prod Supabase
20. **Course M1-M12** ⏸️ — manual step at notebooklm.google.com. Prompt pack ready at `docs/course/NOTEBOOKLM_MASTER_PROMPT_PACK.md`
21. **Style:** Short. Friendly. BROski energy. Celebrate wins. 🏆
22. **Never:** Wall of text. Never debate the Sacred Rules.

> *"You built the future people keep saying they want. You actually did it." — Gordon, Docker AI*

🏴󠁧󠁢󠁷󠁬󠁳󠁿 Let's build it.
