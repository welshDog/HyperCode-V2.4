# 🦅 HyperCode V2.0 — Golden Startup Runbook

> **The definitive "never get stuck again" guide.**  
> Verified live on March 15, 2026. Keep this updated as the stack evolves.

---

## ⚡ TL;DR — The 5-Step Golden Chain

```powershell
# 1. Bootstrap DB (first time or fresh volume only)
docker exec hypercode-core python -c "from app.db.session import engine; import app.models.models; from app.db.base_class import Base; Base.metadata.create_all(bind=engine); print('✅ DB tables ensured')"

# 2. Confirm Core is healthy
docker inspect hypercode-core --format "{{.State.Health.Status}}"

# 3. Seed DB + write token.txt + project_id.txt
python seed_data.py

# 4. Fire the swarm test
python run_swarm_test.py

# 5. Watch Celery work live
docker logs --tail 200 celery-worker
```

---

## 🧠 Startup Sequence (What The Stack Expects)

The correct boot order is:

```
Postgres + Redis → healthy first
       ↓
hypercode-core → healthy
       ↓
celery-worker → ready
       ↓
agents → can do real work
```

**Never run seed_data.py until `hypercode-core` status = `healthy`.**

Check health status with:
```powershell
docker inspect hypercode-core --format "{{.State.Health.Status}}"
# Wait until output = "healthy"
```

---

## 🗄️ DB Bootstrap (One-Time Per Fresh Volume)

Preferred (versioned migrations):

```powershell
docker exec hypercode-core alembic upgrade head
```

If your DB was already created via `create_all` and you just want Alembic to “take ownership”:

```powershell
docker exec hypercode-core alembic stamp head
```

Fallback (dev bootstrap):

Tables can also be created via SQLAlchemy `Base.metadata.create_all`.

Run this **once** after a fresh DB volume or first clone:

```powershell
docker exec hypercode-core python -c "
from app.db.session import engine
import app.models.models
from app.db.base_class import Base
Base.metadata.create_all(bind=engine)
print('✅ DB tables ensured')
"
```

Expected output:
```
✅ DB tables ensured
```

This resolves: `psycopg2.errors.UndefinedTable: relation "users" does not exist`

---

## 🌱 Seeding The Database

```powershell
# Activate venv first
.\.venv\Scripts\Activate.ps1

# Run seed script
python seed_data.py
```

`seed_data.py` will:
1. Create admin user (`admin@hypercode.ai`) — skips if exists
2. Login and get JWT token
3. Create "BROski Project" — or grab first existing project
4. Write **both** files to disk:
   - `token.txt` — JWT for API calls
   - `project_id.txt` — real project ID (no more hardcoded `1`!)

Expected output:
```
🌱 Seeding Database...
Creating User...
✅ User created.
Logging in...
✅ Token received: eyJ...
✅ Project created: ID 1
🎉 Seeding Complete!
✅ token.txt written
✅ project_id.txt written
```

---

## 🧪 Running The Swarm Test

```powershell
python run_swarm_test.py
```

- Reads `project_id.txt` (hard-stops if missing — run `seed_data.py` first)
- POSTs a `translate` task to Core API
- Triggers `hypercode.tasks.process_agent_job` via Celery

Then watch Celery process it:
```powershell
docker logs --tail 200 celery-worker
```

Success looks like:
```
✅ Updated Task 2
✅ Saved output for Task 2
```

---

## 🚨 Troubleshooting

### Docker Desktop Linux Engine Flapping
**Symptom:** `request returned 500 Internal Server Error ... dockerDesktopLinuxEngine/v1.53`

**Fix:**
```powershell
# Reset WSL2 integration layer (run as admin)
wsl --shutdown
# Wait 10 seconds, then restart Docker Desktop
```

---

### Core Returns `(52) Empty reply from server`
**Symptom:** `curl http://127.0.0.1:8000/health` returns empty reply

**Causes:**
1. Core is still booting — wait 15–30 seconds and retry
2. DB tables missing — run the DB bootstrap command above
3. Docker engine instability — run `wsl --shutdown` + restart Docker Desktop

**Test with Python (most reliable on Windows):**
```powershell
python -c "import requests; r = requests.get('http://127.0.0.1:8000/health'); print(r.status_code, r.json())"
```

---

### `seed_data.py` — Connection Aborted
**Symptom:** `Connection aborted. RemoteDisconnected('Remote end closed connection without response')`

**Fix:** Core isn't ready yet. Wait until:
```powershell
docker inspect hypercode-core --format "{{.State.Health.Status}}"
# = healthy
```
Then re-run `seed_data.py`.

---

### Celery Worker Shows `unhealthy` In `docker ps`
**Reality check:** Celery is probably fine.  
Confirm with:
```powershell
docker logs --tail 10 celery-worker
# Should show: "celery@... ready."
```
The `unhealthy` Docker status is often a stale flag from startup — not a real problem if logs show `ready`.

---

### `psycopg2.errors.UndefinedTable: relation "users" does not exist`
Run the DB bootstrap command:
```powershell
docker exec hypercode-core python -c "from app.db.session import engine; import app.models.models; from app.db.base_class import Base; Base.metadata.create_all(bind=engine); print('✅ DB tables ensured')"
```

---

## 🌐 Service Access Points

| Service | URL | Notes |
|---|---|---|
| HyperCode Core API | http://127.0.0.1:8000 | Main FastAPI backend |
| API Docs (Swagger) | http://127.0.0.1:8000/docs | Interactive API explorer |
| Mission Control | http://127.0.0.1:8088 | Next.js dashboard |
| Crew Orchestrator | http://127.0.0.1:8081 | Agent orchestration |
| Healer Agent | http://127.0.0.1:8010 | Self-healing monitor |
| Grafana | http://127.0.0.1:3001 | Observability dashboards |
| Prometheus | http://127.0.0.1:9090 | Metrics |
| Ollama | http://127.0.0.1:11434 | Local LLM |
| MinIO | http://127.0.0.1:9000 | Object storage |

---

## 🎛️ Mission Control (Unified API)

Mission Control (8088) uses a single API base (Core) and routes agent-ops via Core’s orchestrator gateway endpoints.

- Login uses the seeded Core user from `seed_data.py` (default: `admin@hypercode.ai` / `adminpassword`).
- Core gateway endpoints:
  - `GET /api/v1/orchestrator/agents`
  - `GET /api/v1/orchestrator/system/health`
  - `POST /api/v1/orchestrator/approvals/respond`
  - `WS  /api/v1/orchestrator/ws/approvals`

Config:

```env
NEXT_PUBLIC_CORE_URL=http://127.0.0.1:8000
```

## 🧠 Crew Orchestrator Health Monitoring (F4 Fix)

Crew Orchestrator periodically probes agent `/health` endpoints and can emit `HEALTH ALERT` events when many agents are down. If you’re not running the full agent roster, set `ORCHESTRATOR_ENABLED_AGENTS` to avoid false positives.

```env
ORCHESTRATOR_ENABLED_AGENTS=project-strategist,backend-specialist,frontend-specialist
```

## 🦅💊 Alpha Routing (Hunter/Healer)

Alpha routing is **opt-in** and only activates when:
- `OPENROUTER_API_KEY` is set, and
- the caller passes `route_context=...` into the Brain/agent path.

### Enable (dev/staging)

Add to your environment (examples):

```env
OPENROUTER_API_KEY=...

HUNTER_ALPHA_ENABLED=true
HUNTER_ALPHA_PRIVACY_MODE=redact

HEALER_ALPHA_ENABLED=true
HEALER_ALPHA_PRIVACY_MODE=redact
```

### Verify (safe, no secrets)

```powershell
docker exec hypercode-core python -c "from app.core.config import settings; from app.core.model_routes import ModelRouteContext, select_model_route; settings.HUNTER_ALPHA_ENABLED=True; print(select_model_route(ModelRouteContext(kind='architecture',cross_repo=True), settings))"
```

### Rollback

Rollback is env-only:
- set `HUNTER_ALPHA_ENABLED=false`
- set `HEALER_ALPHA_ENABLED=false`
- remove `OPENROUTER_API_KEY`

Validation after rollback:
- no OpenRouter requests occur
- local Ollama and existing cloud fallback behavior remain unchanged
| pgAdmin | http://127.0.0.1:59080 | DB admin UI |

---

## 🔥 Quick Health Check (All Containers)

```powershell
# Full stack status snapshot
docker ps --format "table {{.Names}}\t{{.Status}}"

# Resource usage
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

---

*Last verified: April 05, 2026 — HyperCode V2.4 🦅♾️*

---

## 🏗️ Canonical Entrypoint Migration (V3+)

As of V2.4, the project has been fully migrated from the deprecated `HyperCode-V2.0` directory to the canonical `HyperCode-V2.4` entrypoint structure (paving the way for V3+).

**Key Rules:**
- **No Hardcoded Legacy Paths:** Do not use `HyperCode-V2.0` in any scripts, compose files, or configuration files. All host bind mounts must point to the current project root or use relative paths (`./`).
- **CI Guard:** A GitHub Actions workflow (`.github/workflows/no-legacy-paths.yml`) is in place to fail any pull request or push that reintroduces the string `HyperCode-V2.0`.
- **Resolving Stale Mounts:** If containers enter a restart loop with `ModuleNotFoundError` or `can't open file` errors, verify that your active `.env` or Compose overrides are not mapping volumes to a non-existent legacy directory. Re-run deployments from the correct V2.4 root.
