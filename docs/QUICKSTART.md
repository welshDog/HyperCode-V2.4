# 🚀 HyperCode V2.0 — Quick Setup

> **New here?** Start with this file, then use [START_HERE.md](START_HERE.md) if you also want the MCP Gateway + Model Runner profile.  
> **Stack stuck?** Jump straight to [RUNBOOK.md](RUNBOOK.md) — it has every fix.

---

## ⚡ Fastest Way To Start

### Windows
```powershell
.\scripts\start-agents.bat
```

### Linux/Mac
```bash
chmod +x scripts/start-agents.sh
./scripts/start-agents.sh
```

---

## 🗄️ One-Time DB Bootstrap (REQUIRED on first run)

Preferred (versioned migrations):

```powershell
docker exec hypercode-core alembic upgrade head
```

If your DB already exists (created earlier via `create_all`):

```powershell
docker exec hypercode-core alembic stamp head
```

Fallback (dev bootstrap):

```powershell
docker exec hypercode-core python -c "from app.db.session import engine; import app.models.models; from app.db.base_class import Base; Base.metadata.create_all(bind=engine); print('✅ DB tables ensured')"
```

Expected: `✅ DB tables ensured`

---

## 🔗 Manual Setup

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Add your API keys:**
   Edit `.env` and set at least `POSTGRES_PASSWORD` and your chosen LLM keys (e.g. `PERPLEXITY_API_KEY`). Avoid committing `.env`.

3. **Start the stack:**
   ```bash
   docker compose up -d
   ```

4. **Start agents (optional):**
   ```bash
   docker compose --profile agents up -d
   ```

---

## 🌱 Seed + Test Chain (after DB bootstrap)

```powershell
# Activate venv
.\.venv\Scripts\Activate.ps1

# Seed the DB (writes token.txt + project_id.txt)
python seed_data.py

# Fire swarm test (reads project_id.txt — run seed first!)
python run_swarm_test.py

# Watch Celery process the task live
docker logs --tail 200 celery-worker
```

Success = Celery logs show `✅ Updated Task X` and `✅ Saved output for Task X`

---

## 🌐 Access Points

| Service | URL |
|---|---|
| Core API | http://127.0.0.1:8000 |
| API Docs | http://127.0.0.1:8000/docs |
| Mission Control | http://127.0.0.1:8088 |
| Crew Orchestrator | http://127.0.0.1:8081 |
| Grafana | http://127.0.0.1:3001 |
| Prometheus | http://127.0.0.1:9090 |
| Ollama | http://127.0.0.1:11434 |

---

## 🎛️ Mission Control (Unified API)

Mission Control uses Core as the single API base and routes agent-ops via Core’s orchestrator gateway endpoints.

- Login uses the seeded Core user from `seed_data.py` (default: `admin@hypercode.ai` / `adminpassword`).
- Dashboard API base is controlled by:

```env
NEXT_PUBLIC_CORE_URL=http://127.0.0.1:8000
```

Crew Orchestrator health monitoring (optional, prevents false “agents down” alerts when you’re not running all agents):

```env
ORCHESTRATOR_ENABLED_AGENTS=project-strategist,backend-specialist,frontend-specialist
```

## 🦅💊 Alpha Routing (Hunter/Healer)

Alpha routing is **opt-in** and only activates when `OPENROUTER_API_KEY` is set and the caller uses a `route_context`.

Enable in dev/staging by setting:

```env
OPENROUTER_API_KEY=...
HUNTER_ALPHA_ENABLED=true
HEALER_ALPHA_ENABLED=true
```

Rollback:
- set both enable flags to `false`
- remove `OPENROUTER_API_KEY`

---

## 🛠️ Common Commands

```powershell
# View all container health
docker ps --format "table {{.Names}}\t{{.Status}}"

# View logs for any service
docker logs --tail 50 hypercode-core
docker logs --tail 50 celery-worker

# Resource usage snapshot
docker stats --no-stream

# Restart a single service
docker restart hypercode-core
```

---

## 🚨 Troubleshooting

**Docker flapping (500 errors)?**
```powershell
wsl --shutdown
# Then restart Docker Desktop
```

**Core returning empty replies?**
- Wait for `docker inspect hypercode-core --format "{{.State.Health.Status}}"` = `healthy`
- Then retry

**`relation "users" does not exist`?**
- Run the DB bootstrap command above

**Full troubleshooting guide:** See [RUNBOOK.md](RUNBOOK.md)

---

*For full agent docs see [agents/README.md](agents/README.md)*  
*For infrastructure deep-dive see [guide infrastructure setup.md](guide%20infrastructure%20setup.md)*
