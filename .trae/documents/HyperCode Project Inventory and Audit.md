# HyperCode Project Inventory and Audit

Status: Baseline documentation established for current repository state. Generated on 2026-02-01.

## Overview
- Monorepo comprising backends, frontends, agent orchestration, and infrastructure.
- Core runtime services orchestrated via Docker Compose; optional Kubernetes manifests present.
- Monitoring via Prometheus, Blackbox Exporter, and Redis Exporter.

## Technology Stack and Versions
- Backend (HyperCode Core): Python 3.11, FastAPI (>=0.104.1), Uvicorn (>=0.24.0), Celery 5.3.6, Redis 7, SQLAlchemy 2.x, Alembic 1.13.x.
- Agents Platform (Hyper-Agents-Box): Python 3.11, FastAPI 0.115.5, Uvicorn 0.31.0, LangChain suite, Discord.py.
- Frontend (Hyperflow Editor): React 19, Vite 5, TypeScript 5.9, Vitest 4, Playwright 1.58.
- Frontend (BROski Terminal): Next.js 16.1, React 19, TypeScript 5, Vitest 1.x, Playwright 1.58, Tailwind 4.
- Datastores: PostgreSQL 16 (alpine), Redis 7 (alpine).
- Observability: Prometheus (latest), Blackbox Exporter (latest), Redis Exporter v1.44.0.

References:
- Docker Compose: [docker-compose.yml](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/docker-compose.yml)
- Prometheus: [prometheus.yml](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/prometheus.yml)
- HyperCode Core: [pyproject.toml](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hypercode-core/pyproject.toml), [requirements.txt](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hypercode-core/requirements.txt)
- Hyperflow Editor: [package.json](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hyperflow-editor/package.json)
- BROski Terminal: [package.json](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/BROski%20Business%20Agents/broski-terminal/package.json)
- Hyper-Agents-Box: [requirements.txt](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/Hyper-Agents-Box/requirements.txt), [docker/Dockerfile](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/Hyper-Agents-Box/docker/Dockerfile)

## Modules and Services
- hypercode-core (Python FastAPI backend): [server.py](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hypercode-core/hypercode/server.py)
- hyperflow-editor (Visual editor, React+Vite): [vite.config.ts](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hyperflow-editor/vite.config.ts)
- broski-terminal (Next.js app): [next.config.ts](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/BROski%20Business%20Agents/broski-terminal/next.config.ts)
- hyper-agents-box (Agents orchestrator + Health API): [main.py](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/Hyper-Agents-Box/main.py), [agents/health_api.py](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/Hyper-Agents-Box/agents/health_api.py)
- Infrastructure: Kubernetes manifests [k8s](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/k8s), Monitoring [monitoring](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/monitoring), Infra-as-code [infra](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/infra)

## Deployment Environments
- Local/Dev via Docker Compose
  - Services: hypercode-core, broski-terminal, hyperflow-editor, hyper-agents-box, postgres, redis, redis-exporter, prometheus, blackbox-exporter, celery-worker.
  - Network: bridge `hypernet`.
  - Volumes: `pgdata` for Postgres.
- Kubernetes (manifests present): [deployment.yaml](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/k8s/deployment.yaml), [service.yaml](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/k8s/service.yaml), [ingress.yaml](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/k8s/ingress.yaml), [namespace.yaml](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/k8s/namespace.yaml)

### Deployment Procedure (Compose)
1. Ensure Docker is running.
2. From project root, run `docker compose up -d --build`.
3. Verify health:
   - Backend: http://localhost:8000/health
   - Terminal: http://localhost:3000/api/health
   - Agents: http://localhost:5000/agents/health
   - Prometheus: http://localhost:9090/

## Configuration and Environment Variables
- docker-compose service envs:
  - HYPERCODE_DB_URL, HYPERCODE_REDIS_URL for hypercode-core/celery.
  - NEXT_PUBLIC_CORE_URL, NEXT_PUBLIC_AGENTS_URL for broski-terminal.
- Hyperflow Editor .env:
  - VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY ([.env.example](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hyperflow-editor/.env.example)).
- Hyper-Agents-Box .env:
  - DISCORD_TOKEN, OLLAMA_BASE_URL, OPENAI_API_KEY, PERPLEXITY_API_KEY, ENVIRONMENT, VAULT/paths, security/API_KEY_SECRET ([.env.example](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/Hyper-Agents-Box/.env.example)).
- BROski Terminal .env:
  - NEXT_PUBLIC_CORE_URL ([.env.example](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/BROski%20Business%20Agents/broski-terminal/.env.example)).

## Build and Testing Processes
- hyperflow-editor (Vite): `npm run dev`, `npm run build`, `npm run test`, `npm run lint`, Playwright via `npm run test` with config.
- broski-terminal (Next.js): `npm run dev`, `npm run build`, `npm run start`, `npm run test:unit`, `npm run test:e2e`, `npm run lint`.
- hypercode-core (Python): Poetry-configured project; tests via `pytest` using [pytest.ini](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hypercode-core/pytest.ini), scripts in [pyproject.toml](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hypercode-core/pyproject.toml).
- Hyper-Agents-Box: `python main.py` runs Health API & Discord bot; tests present via pytest dependencies.

## APIs and Endpoints
- HyperCode Core API ([server.py](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hypercode-core/hypercode/server.py)):
  - GET `/` → Online status.
  - GET `/health` → Component ok snapshot.
  - GET `/ready` → Dependency readiness (DB, Redis, JWT secret) with 200/503.
  - GET `/metrics` → Prometheus metrics.
  - GET `/celery/health` → Worker status snapshot.
  - GET `/workflows` (scope `workflows:read`) → List workflows.
  - POST `/workflows` (scope `workflows:write`) → Create workflow.
  - DELETE `/admin/workflows/{wf_id}` (scope `admin:delete`) → Delete workflow (audit recorded).
  - GET `/admin/audit/logs` (scope `admin:read`) → Retrieve audit log.
  - GET `/runs/{run_id}` (scope `runs:read`) → Retrieve run.
  - POST `/compile` (scope `compile:write`) → Compile visual flow to HyperCode and simulate.
  - POST `/cache/warm` (scope `cache:warm`) → Warm cache keys.
  - GET `/cache/metrics` → Cache hit/miss and Redis memory.
  - POST `/auth/refresh` → Refresh JWT (requires configured secret).
- Hyper-Agents-Box Health API ([agents/health_api.py](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/Hyper-Agents-Box/agents/health_api.py)):
  - GET `/health` → Ok.
  - GET `/agents/health` → Agents heartbeat snapshot + system metrics.
  - POST `/agents/register` → Register agent.
  - POST `/agents/heartbeat` → Agent heartbeat.
  - WS `/ws/health` → Live health feed.

## Third-Party Integrations
- Supabase (hyperflow-editor, broski-terminal): `@supabase/supabase-js`.
- Discord Bot (Hyper-Agents-Box): `discord.py`.
- LLMs: Ollama (local), OpenAI, PERPLEXITY via LangChain adapters.
- Google APIs (broski-terminal): `googleapis`.

## Database Schema and Migrations
- Alembic initialized: [alembic.ini](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hypercode-core/alembic.ini), [alembic/versions](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hypercode-core/alembic/versions).
- Models are not surfaced in the listing; schema evolution governed via Alembic; run migrations on deploy.

## Monitoring
- Prometheus scrapes Redis Exporter and Blackbox probes configured in [prometheus.yml](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/prometheus.yml).
- Blackbox probes: Backend `/health`, `/celery/health`, Terminal `/api/health`.
- Monitoring assets present under [monitoring](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/monitoring).

## Dependency Audit (Summary)
- JS (hyperflow-editor): Outdated packages detected (`vite` major update available; `zustand` major update; minor bumps: React 19.2.4, TS-ESLint, Playwright, Vitest).
- JS (broski-terminal): Minor/patch updates available (Next 16.1.6, React 19.2.4, Vitest 4.x upgrade path).
- Python (hypercode-core): `fastapi>=0.104.1` lags behind Agents Box `fastapi==0.115.5`; consider aligning to latest compatible FastAPI 0.115.x.
- Python (Hyper-Agents-Box): Versions look current; validate at runtime.

Raw npm outdated outputs are available on demand; recommended upgrades should be validated with tests.

## Security Audit (Key Findings)
- JWT verification bypass risk: If `HYPERCODE_JWT_SECRET` is unset, tokens are decoded with `verify_signature=False` ([server.py:L60-L64](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hypercode-core/hypercode/server.py#L60-L64)). Severity: High. Remediation: require secret; reject requests if absent.
- Admin endpoints depend on scopes but inherit the JWT weakness; potential IDOR if signature disabled. Severity: High.
- Rate limiting is in-memory per process ([server.py:L48-L57](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hypercode-core/hypercode/server.py#L48-L57)); inadequate across multiple replicas. Severity: Medium. Remediation: Redis-backed counters.
- CORS open methods/headers with dev origins ([server.py:L156-L163](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hypercode-core/hypercode/server.py#L156-L163)). Severity: Low in dev; tighten for prod.
- Health endpoints expose operational metadata; ensure no sensitive data leaks. Severity: Low.

## Architecture Diagram (Mermaid)

```mermaid
graph TD
  subgraph Frontends
    A[Hyperflow Editor (Vite)] -->|POST /compile| B(HyperCode Core API)
    C[BROski Terminal (Next.js)] -->|REST w/ scopes| B
  end

  subgraph Backend
    B --> D[(PostgreSQL)]
    B --> E[(Redis)]
    B --> F[Celery Worker]
  end

  subgraph Agents
    G[Hyper-Agents-Box] --> H{Health API}
    C -->|NEXT_PUBLIC_AGENTS_URL| H
  end

  subgraph Monitoring
    I[Prometheus] --> J[Blackbox Exporter]
    I --> K[Redis Exporter]
    J --> B
    J --> C
    K --> E
  end
```

## Data Flow (Compile & Simulate)
- Visual graph in Hyperflow Editor is sent to `/compile` ([server.py](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hypercode-core/hypercode/server.py#L309-L357)).
- Compiler maps nodes → HyperCode code ([compiler.py](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hypercode-core/hypercode/compiler.py)).
- Simulator executes or runs bio pipelines ([simulator.py](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/hypercode-core/hypercode/simulator.py)).
- Results stored in memory under `RUNS` for retrieval via `/runs/{run_id}`.

## Technical Debt & Deprecated Code
- Mixed FastAPI versions between projects; standardize to reduce compatibility drift.
- In-memory stores for rate limiting, idempotency, workflows/runs; migrate to Redis/DB for multi-instance reliability.
- Security: enforce mandatory JWT secret and signature verification; add scope validation tests.
- Tailwind v4 adoption in broski-terminal may require config stabilization.
- Vite major upgrade path pending in hyperflow-editor; evaluate plugin compatibility.

## Access Verification Checklist
- Documentation locations: [docs/](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/docs), project root `.trae/documents`.
- Source repositories and paths confirmed in this inventory.
- Credentials required:
  - Supabase anon key (frontend), Discord token (agents), OpenAI/PERPLEXITY keys (optional), OLLAMA local server.
  - Backend secrets: `HYPERCODE_JWT_SECRET`, `HYPERCODE_DB_URL`, `HYPERCODE_REDIS_URL`.
- Action: Distribute `.env.example` derivatives and central secrets via vault; run access checks with the Health API.

## Knowledge Transfer Plan
- Session 1 (Architecture & Infra, 60m): Walkthrough of services, Docker/K8s, monitoring.
- Session 2 (Backends & APIs, 60m): HyperCode Core endpoints, JWT & scopes, Celery.
- Session 3 (Frontends & Editor, 60m): Hyperflow Editor flows, Next.js terminal.
- Session 4 (Agents Platform, 60m): Health API, Discord bot, LLM adapters.
- Materials: This inventory; link to existing guides ([DEPLOYMENT_GUIDE.md](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/DEPLOYMENT_GUIDE.md), [COMPREHENSIVE_PROJECT_REPORT.md](file:///c:/Users/lyndz/Downloads/My%20Hyper%20Agents/THE%20HYPERCODE/COMPREHENSIVE_PROJECT_REPORT.md)).

## Recommended Next Actions
- Align FastAPI versions and add mandatory JWT secret enforcement.
- Upgrade JS dependencies where safe; run Vitest+Playwright suites post-upgrade.
- Migrate in-memory stores to Redis/Postgres for consistency under scale.
- Tighten CORS and add rate-limit backed by Redis.
- Establish secrets management (env loader + vault) across services.

