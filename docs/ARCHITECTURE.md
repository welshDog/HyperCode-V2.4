# HyperCode V2.4: Architecture & Technical Manual

> **Last Updated:** 2026-04-15
> **Status:** 29/29 containers healthy — Stripe LIVE — CognitiveUplink WS LIVE

---

## Executive Summary

HyperCode V2.4 is a **self-evolving cognitive AI architecture** — a swarm of specialized AI agents that autonomously design, deploy, heal, and evolve themselves inside a Docker-based infrastructure. It is neurodivergent-first: built for ADHD/autistic/dyslexic developers who think in systems and need tools that move at the speed of thought.

The system goes beyond a code assistant: it runs missions, routes commands to specialist agents, self-heals broken services, handles Stripe payments, and streams real-time results to a live dashboard.

---

## 1. System Architecture

### 1.1 Core Services

| Service | Port | Role |
|---------|------|------|
| **HyperCode Core** (`hypercode-core`) | 8000 | FastAPI backbone — auth, DB, Stripe, MCP gateway, WS hub |
| **Crew Orchestrator** | 8081 | Agent lifecycle + mission execution + approval gating |
| **Agent X** (Meta-Architect) | 8080 | Autonomously designs and deploys new agents via Docker |
| **Healer Agent** | 8008 | Self-healing — monitors containers, auto-recovers failures |
| **Celery Worker** | — | Background task processing (Redis broker) |
| **Mission Control** | 8088 | Next.js real-time dashboard + CognitiveUplink chat |
| **Grafana Observability** | 3001 | Full Prometheus + Grafana + Loki + Tempo stack |

### 1.2 Infrastructure Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 (backend / agents) + TypeScript (dashboard) |
| API Framework | FastAPI + Pydantic + SQLAlchemy 2.0 |
| Task Queue | Celery 5.x + Redis 7 |
| Database | PostgreSQL 15 |
| Caching / Pub-Sub | Redis 7 |
| LLM Backend | Ollama (local, Docker Model Runner) |
| Vector Store | ChromaDB |
| Object Storage | MinIO |
| Observability | Prometheus + Grafana + Loki + Tempo + Promtail |
| Security | Trivy (CVE scanner) + non-root containers + cap drops |
| Payments | Stripe Checkout + webhooks |
| Container Runtime | Docker Compose (multi-file strategy) |

---

## 2. Network Topology (Phase 10B)

Five isolated Docker networks — two are `internal: true` (no external internet):

```
┌─ frontend-net ──────────────────────┐  internet: yes
│  dashboard · mission-ui · mcp-server│
└─────────────────────────────────────┘
          │
┌─ backend-net ────────────────────────┐  internet: yes
│  hypercode-core (bridges all layers) │
└──────────────────────────────────────┘
          │
┌─ agents-net ─────────────────────────┐  internet: yes (LLM API calls)
│  crew-orchestrator · agent-x         │
│  healer · celery-worker · specialists│
└──────────────────────────────────────┘
          │
┌─ data-net ───────────────────────────┐  internal: true (NO internet)
│  redis · postgres · minio · chroma   │
└──────────────────────────────────────┘
          │
┌─ obs-net ────────────────────────────┐  internal: true (NO internet)
│  prometheus · grafana · loki         │
│  tempo · promtail                    │
└──────────────────────────────────────┘
```

`hypercode-core` is the only service that spans all non-internal networks — it acts as the controlled bridge between frontend, agents, and data layers.

---

## 3. Key Subsystems

### 3.1 CognitiveUplink WebSocket (`WS /ws/uplink`)

Neural chat interface from Mission Control → Crew Orchestrator.

```
Dashboard (CognitiveUplink.tsx)
    │  ws://localhost:8000/ws/uplink
    ▼
hypercode-core (app/ws/uplink.py)
    │  POST http://crew-orchestrator:8081/execute
    │  X-API-Key: ${ORCHESTRATOR_API_KEY}
    ▼
crew-orchestrator
    │  routes to specialist agent
    ▼
agent result → back through WS → dashboard chat bubble
```

Message contract:
- Inbound: `{ type: 'execute', payload: { command: str } }` or `{ type: 'ping' }`
- Outbound: `{ type: 'response', payload: str }` or `{ type: 'error', data: str }` or `{ type: 'pong' }`

### 3.2 Stripe Payment Stack (Phase 10F / 10G)

```
Dashboard /pricing page
    │  POST /api/stripe/checkout
    ▼
hypercode-core stripe_service.py
    │  stripe.checkout.Session.create(mode=payment|subscription)
    ▼
Stripe → redirect to success_url
    │  POST /api/stripe/webhook (Stripe-Signature verified)
    ▼
DB writes: subscription row, payment record, enrollment
```

Token packs → `mode="payment"`. Course subscriptions → `mode="subscription"`.

### 3.3 Agent Key Auth (Phase 10D)

All agent-to-agent calls use `X-API-Key` headers with `hc_`-prefixed keys (43 chars, URL-safe). Per-key rate limiting enforced in middleware. Keys stored hashed in DB.

### 3.4 Self-Healing (Healer Agent)

Healer monitors all containers via the Docker socket proxy. On failure it:
1. Attempts `docker restart`
2. Publishes alert to Redis `hypercode:logs`
3. Records incident in PostgreSQL

### 3.5 BROski$ Token Economy

- `broski_tokens` balance column on `users` table
- `token_transactions` append-only ledger (idempotency guards)
- `award_tokens()` / `spend_tokens()` — SECURITY DEFINER, server-side only
- Digital shop: Prompt Packs (200 BROski$), Templates (150 BROski$), Bonus Lessons (100 BROski$)

---

## 4. Observability

| Tool | Port | Purpose |
|------|------|---------|
| Prometheus | internal | Scrapes metrics from core, celery, node-exporter, cAdvisor |
| Grafana | 3001 | Dashboards — CPU, memory, request rates, agent status |
| Loki | internal | Log aggregation (Promtail ships container logs) |
| Tempo | internal | Distributed tracing (OpenTelemetry from hypercode-core) |
| Redis `hypercode:logs` | internal | Live log ring buffer (last 1000 entries) |
| Redis `agents:heartbeat:*` | internal | Agent liveness keys (TTL 30s) |

---

## 5. Secrets & Configuration

- Local dev: `.env` file (never committed). Special-char passwords must be quoted.
- Production: `./secrets/*.txt` files + `docker-compose.secrets.yml` override.
- **NEVER** set `POSTGRES_PASSWORD_FILE` alongside `POSTGRES_PASSWORD` — causes startup conflict.

Key env vars:
```
ORCHESTRATOR_API_KEY   — agent-to-agent auth
STRIPE_SECRET_KEY      — Stripe payments
STRIPE_WEBHOOK_SECRET  — webhook signature verification
HYPERCODE_REDIS_URL    — Redis connection string
DATABASE_URL           — PostgreSQL connection string
```

---

## 6. Security Standards

Every Dockerfile follows:
1. `FROM python:3.11-slim` — never `latest`
2. `apt-get upgrade -y` on every build
3. pip toolchain pinned (`pip==26.0.1`, `setuptools>=80.0.0`, etc.)
4. Non-root user (`appuser`)
5. Trivy scanned — target: ZERO CRITICAL, <5 HIGH

---

## 7. Start Commands

```bash
# Core stack (29 containers)
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d

# Add all AI agents
docker compose -f docker-compose.yml -f docker-compose.secrets.yml --profile agents up -d

# Full stack (all profiles)
docker compose -f docker-compose.yml -f docker-compose.secrets.yml \
  --profile agents --profile hyper --profile health --profile mission up -d
```

---

> **built with WelshDog + BROski 🚀🌙**
