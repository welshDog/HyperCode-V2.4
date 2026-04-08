# START HERE — HyperCode V2.0

> **One repo. One truth. This is it.**
> 696 commits. 57 services. 25+ agents. Built by one neurodivergent developer in Wales. 🏴󠁧󠁢󠁷󠁬󠁳󠁿

---

## Which launch path do you want?

### Path 1 — Local development (hot-reload, pgAdmin, mailhog)
```bash
cp .env.example .env        # fill in your secrets
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```
Gives you: FastAPI on :8000, dashboard on :8088, Redis, Postgres, pgAdmin.

---

### Path 2 — Core stack only (infra + core API + dashboard)
```bash
docker compose up -d
```
Gives you: Redis, Postgres, Ollama, HyperCode Core API, Mission Control Dashboard, Prometheus, Grafana.

---

### Path 3 — Core + all specialist agents
```bash
docker compose --profile agents up -d
```
Adds: crew-orchestrator, project-strategist, frontend/backend/db/qa/devops/security specialists, coder-agent, celery-worker.

---

### Path 4 — Core + hyper agents (architect, observer, worker, agent-x)
```bash
docker compose --profile hyper up -d
```
Adds: agent-x meta-architect, hyper-observer, hyper-worker.

---

### Path 5 — Full stack (everything)
```bash
# Windows (recommended)
.\scripts\boot.ps1 -Profile all

# Linux/Mac
docker compose --profile agents --profile hyper --profile health --profile mission up -d
```

---

### Path 6 — Monitoring only (Grafana + Prometheus)
```bash
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```
Grafana: http://localhost:3001 | Prometheus: http://localhost:9090

---

## After starting — check it's alive

```bash
# All containers healthy?
docker compose ps

# Core API responding?
curl http://127.0.0.1:8000/health

# Dashboard live?
open http://127.0.0.1:8088

# Agents heartbeating?
curl http://127.0.0.1:8000/api/v1/agents/status
```

---

## Key ports

| Service | Port | URL |
|---|---|---|
| HyperCode Core API | 8000 | http://127.0.0.1:8000 |
| Mission Control Dashboard | 8088 | http://127.0.0.1:8088 |
| Healer Agent | 8008 | http://127.0.0.1:8008 |
| Agent X (Meta-Architect) | 8080 | http://127.0.0.1:8080 |
| Crew Orchestrator | 8081 | http://127.0.0.1:8081 |
| Grafana | 3001 | http://127.0.0.1:3001 |
| Prometheus | 9090 | http://127.0.0.1:9090 |

---

## Windows path quirks

If volumes fail to mount on Windows, add the overlay:
```bash
docker compose -f docker-compose.yml -f docker-compose.windows.yml up -d
```

---

## Want to contribute?

Read [CONTRIBUTING.md](CONTRIBUTING.md) — setup guide, how to add an agent, how to run tests.

## Architecture overview?

Read [CLAUDE.md](CLAUDE.md) — the AI-readable architecture doc that also humans can read.

## Something broken?

```bash
# Healer agent auto-recovers most failures.
# For manual diagnosis:
docker compose logs hypercode-core --tail 50
curl http://127.0.0.1:8000/api/v1/system/state
```
