# Contributing to HyperCode V2.0

> Built neurodivergent-first. ADHD-friendly. Pattern-thinker approved. Everyone welcome.

This guide covers everything you need to go from zero to a merged PR — environment setup, adding an agent, running tests, and the commit conventions we use.

---

## Table of Contents

1. [Before you start](#before-you-start)
2. [Environment setup](#environment-setup)
3. [Which Docker Compose file to use](#which-docker-compose-file-to-use)
4. [Project structure in 2 minutes](#project-structure-in-2-minutes)
5. [How to add a new agent](#how-to-add-a-new-agent)
6. [How to add a backend endpoint](#how-to-add-a-backend-endpoint)
7. [Running tests](#running-tests)
8. [Commit conventions](#commit-conventions)
9. [Opening a PR](#opening-a-pr)
10. [Neurodivergent-friendly notes](#neurodivergent-friendly-notes)
11. [Support the project](#support-the-project)

---

## Before you start

- Read [START_HERE.md](START_HERE.md) first — pick your launch path
- Read [CLAUDE.md](CLAUDE.md) — the architecture overview (it's also what the AI reads)
- Check open issues before starting new work — someone might already be on it
- Small focused PRs merge faster than big sweeping ones

---

## Environment setup

### Prerequisites

- Docker Desktop 4.x+ (with Compose V2)
- Python 3.13+ (for running backend tests locally)
- Node.js 20+ (for dashboard work)
- Git with pre-commit hooks (Husky handles this automatically)

### First-time setup

```bash
# 1. Clone
git clone https://github.com/welshDog/HyperCode-V2.0.git
cd HyperCode-V2.0

# 2. Copy environment config
cp .env.example .env
# Edit .env — fill in POSTGRES_PASSWORD, SECRET_KEY, and any API keys you need

# 3. Create the external Docker network (one-time)
docker network create hypercode_public_net

# 4. Start the dev stack
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 5. Run database migrations
docker exec hypercode-core alembic upgrade head

# 6. Verify everything is up
curl http://127.0.0.1:8000/health
```

### Python local setup (for running tests without Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
```

---

## Which Docker Compose file to use

| I want to... | Command |
|---|---|
| Develop the backend | `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d` |
| Test agents | `docker compose --profile agents up -d` |
| Test observability | `docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d` |
| Run everything | `.\scripts\boot.ps1 -Profile all` |
| Run minimal (low RAM) | `docker compose -f docker-compose.nano.yml up -d` |

**Never commit changes to** `docker-compose.dev.yml` unless they're intentional dev-only additions.

---

## Project structure in 2 minutes

```
HyperCode-V2.0/
├── backend/app/          # FastAPI core — all API routes live here
│   ├── api/              # Router registration (api.py is the hub)
│   ├── ws/               # WebSocket broadcasters (metrics, agents, events, logs)
│   ├── routes/           # REST endpoints (reliability, tasks, etc.)
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request/response models
│   └── services/         # Business logic
├── agents/               # Every AI agent has its own folder here
│   ├── healer/           # Self-healing agent (FastAPI, monitors services)
│   ├── dashboard/        # Mission Control (Next.js, TypeScript)
│   ├── shared/           # Shared utilities across agents
│   └── {agent-name}/     # Your new agent goes here
├── tests/
│   ├── unit/             # Fast, no external dependencies (fakeredis)
│   └── integration/      # Needs Redis + Postgres running
├── scripts/              # Deployment, health checks, tooling
└── docker-compose.yml    # The canonical 57-service stack
```

---

## How to add a new agent

Each agent is a self-contained folder under `agents/`. Follow this pattern:

### 1. Create the folder structure

```bash
mkdir -p agents/my-agent
touch agents/my-agent/__init__.py
touch agents/my-agent/main.py
touch agents/my-agent/requirements.txt
touch agents/my-agent/Dockerfile
```

### 2. Write the agent (`main.py`)

```python
from fastapi import FastAPI
import redis.asyncio as aioredis
import asyncio, datetime, os

app = FastAPI(title="My Agent")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
AGENT_ID = "my-agent"

@app.on_event("startup")
async def startup():
    app.state.redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    asyncio.create_task(_heartbeat_loop())

async def _heartbeat_loop():
    """Publish heartbeat every 10s so the dashboard shows this agent as online."""
    key = f"agents:heartbeat:{AGENT_ID}"
    while True:
        try:
            await app.state.redis.hset(key, mapping={
                "name": AGENT_ID,
                "status": "online",
                "last_seen": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
            await app.state.redis.expire(key, 30)
        except Exception:
            pass
        await asyncio.sleep(10)

@app.get("/health")
async def health():
    return {"status": "ok", "agent": AGENT_ID}
```

### 3. Write the Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
# Build context is ./agents — so paths are relative to agents/
COPY my-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY my-agent/ /app/my-agent
COPY shared/ /app/agents/shared/
RUN touch /app/agents/__init__.py
ENV PYTHONPATH=/app
EXPOSE 8009
CMD ["uvicorn", "my-agent.main:app", "--host", "0.0.0.0", "--port", "8009"]
```

### 4. Add to `docker-compose.yml`

```yaml
  my-agent:
    build:
      context: ./agents
      dockerfile: my-agent/Dockerfile
    container_name: my-agent
    restart: unless-stopped
    ports:
      - "127.0.0.1:8009:8009"
    environment:
      - REDIS_URL=redis://redis:6379/0
    networks:
      - backend-net
      - data-net
    depends_on:
      redis:
        condition: service_healthy
    profiles:
      - agents
```

### 5. The heartbeat is what makes it show up on the dashboard

After 10 seconds, your agent will appear in `GET /api/v1/agents/status` and increment `activeAgents` on the metrics panel. No extra registration needed — the heartbeat key is discovered automatically.

---

## How to add a backend endpoint

### 1. Create a new route file

```python
# backend/app/routes/my_feature.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class MyResponse(BaseModel):
    message: str

@router.get("/my-feature", response_model=MyResponse)
async def get_my_feature():
    return MyResponse(message="hello")
```

### 2. Register it in `backend/app/api/api.py`

```python
from app.routes import my_feature
api_router.include_router(my_feature.router, prefix="", tags=["my-feature"])
```

### 3. Write a test in `tests/unit/`

```python
# tests/unit/test_my_feature.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_my_feature_returns_200():
    r = client.get("/api/v1/my-feature")
    assert r.status_code == 200
    assert r.json()["message"] == "hello"
```

### Rules

- All new endpoints **must** use Pydantic response models
- No hardcoded schema — use Alembic migrations for any DB changes
- If it touches Redis, test it with `fakeredis`
- All WebSocket handlers must handle `WebSocketDisconnect` gracefully

---

## Running tests

```bash
# All tests
python -m pytest tests/ --tb=short -q

# Unit tests only (fast, no Docker needed)
python -m pytest tests/unit/ -v --tb=short

# Integration tests (needs Redis + Postgres running)
docker compose up -d redis postgres
python -m pytest tests/integration/ -q

# Specific file
python -m pytest tests/unit/test_dashboard_endpoints.py -q --tb=short

# With coverage
python -m pytest tests/ --cov=backend/app --cov-report=term-missing
```

### Test conventions

- Unit tests use `fakeredis` — never a real Redis connection
- Integration tests use the real Docker services
- Use `pytest.mark.asyncio` for async test functions
- Name tests `test_{what it does}_{expected outcome}`

---

## Commit conventions

We use [Conventional Commits](https://www.conventionalcommits.org/). Subject line must be under 100 characters.

```
feat: add quantum compiler endpoint
fix: healer heartbeat TTL reset on recovery
chore: untrack compiled binaries
docs: add quantum-compiler README
test: cover dashboard WebSocket endpoints
refactor: extract metrics snapshot builder
```

Pre-commit hooks (Husky + commitlint) will reject messages that don't match. They run automatically on `git commit`.

**One change per commit.** Don't bundle unrelated fixes.

---

## Opening a PR

1. Fork the repo and work on a branch: `git checkout -b feat/my-feature`
2. Keep PRs small and focused — one feature or fix per PR
3. Make sure all tests pass: `python -m pytest tests/unit/ -q`
4. Write a clear PR description: what problem does it solve, how did you test it
5. Reference any related issue: `Closes #42`

The CI pipeline runs automatically on every PR:
- Python linting (Ruff + Pylint)
- Unit tests
- Integration tests
- Security scan
- Accessibility check

All gates must pass before merge.

---

## Neurodivergent-friendly notes

This project was built brain-first. A few things to know:

- **No such thing as a dumb question** — open a Discussion if you're unsure
- **ADHD-friendly commits** — small atomic commits are better than one giant PR you procrastinated on
- **Pattern thinkers welcome** — if you see a better architectural pattern, open an issue and explain it
- **Async everything** — the codebase is fully async, which fits the "many things at once" brain well
- **BROski$ economy** — completing tasks earns coins and XP. It's real. Check `/api/v1/broski/`

The HYPER-AGENT-BIBLE (`agents/HYPER-AGENT-BIBLE.md`) is the philosophical backbone. Worth reading if you want to understand *why* things are built the way they are.

---

## Support the project

Help build the neurodivergent-first AI platform. Your support funds agent evolution, healer improvements, and ND UX research.

[![Sponsor](https://img.shields.io/badge/sponsor-30363D?style=for-the-badge&logo=github&logoColor=white)](https://github.com/sponsors/welshDog)

---

## Questions?

Open a GitHub Discussion or file an issue with the `question` label.
