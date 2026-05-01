# 🏗️ Railway Deployment Patterns

## Pattern 1: FastAPI App (HyperCode Style)

### Requirements
- `Dockerfile` OR Railway auto-detects Python via nixpacks
- `PORT` env var (Railway injects automatically, but set explicitly to be safe)

### Steps
```bash
cd /your/fastapi/project
railway login
railway link                                     # Link to existing Railway project
railway variable --set DATABASE_URL=$SUPABASE_URL
railway variable --set SECRET_KEY=your_secret
railway variable --set PORT=8000
railway up                                       # 🚀 Deploy!
railway logs                                     # Watch it go live
```

### Recommended Dockerfile for FastAPI
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE $PORT
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Pattern 2: GitHub Auto-Deploy (CI/CD)

Best for production. Every push to `main` → auto-deploys. Zero manual steps.

1. Push repo to GitHub
2. Railway dashboard → **New Service** → **Connect Repo**
3. Select branch (e.g. `main`) → Railway watches and auto-deploys ✅
4. Set env vars in dashboard: **Service → Variables tab**

Pro tip: Set up separate Railway environments for `staging` (linked to `dev` branch) and `production` (linked to `main` branch).

---

## Pattern 3: Docker Image Deploy

Use when you have a pre-built image in a registry.

**In Railway dashboard:**
- New Service → Docker Image
- Enter image path:

```
ghcr.io/yourusername/hypercode:latest
docker.io/yourusername/broskipets:v1.2
quay.io/yourorg/service:stable
```

**Enable auto-updates** (in service settings) → Railway polls for new image versions and redeploys automatically. ✅

**Private registries** → Pro plan required. Set username/password in service settings.

---

## Pattern 4: Local Dir Quick Deploy (Test/Prototype)

```bash
cd /your/project
railway init          # Creates new Railway project
railway up            # Deploys current folder — instant!
railway logs          # Watch it spin up
railway open          # Opens in browser dashboard
```

Great for: testing a new microservice, quick prototype, checking that a Docker build works in prod.

---

## Pattern 5: Staging vs Production Environments

```bash
# Set up staging
railway environment   # Select 'staging'
railway variable --set NODE_ENV=staging
railway variable --set LOG_LEVEL=debug
railway deploy

# Switch to production
railway environment   # Select 'production'
railway variable --set NODE_ENV=production
railway variable --set LOG_LEVEL=warn
railway deploy
```

**Best Practice:** Link `staging` to `dev` branch (GitHub), `production` to `main` branch. Merge PR → staging auto-deploys. Merge to main → production auto-deploys.

---

## Pattern 6: Monorepo Multi-Service Deploy (HyperCode V2.4 Style)

HyperCode V2.4 is a monorepo with multiple services. Each service gets its own Railway service:

**Dashboard config (per service):**
- Service → Settings → **Root Directory** → set to subfolder (e.g. `/api`, `/worker`, `/dashboard`)

```
hypercode-v2.4/
├── api/           → Railway service: "api" (root: /api)
├── worker/        → Railway service: "worker" (root: /worker)
├── dashboard/     → Railway service: "dashboard" (root: /dashboard)
└── docker-compose.yml  ← NOT used by Railway directly
```

**Railway ≠ Docker Compose.** Split each Compose service into its own Railway service. Use Railway's internal networking (private hostnames) for inter-service communication.

---

## Pattern 7: Discord Bot Deploy (BROski Bot)

Discord bots are persistent services with **no HTTP port** needed.

```bash
railway link
railway variable --set DISCORD_TOKEN=your_bot_token
railway variable --set DATABASE_URL=$SUPABASE_URL
railway variable --set REDIS_URL=$REDIS_URL
# Do NOT set PORT — bots don't need it
railway up
railway logs    # Watch bot connect to Discord gateway
```

**No domain needed.** Discord bots connect outbound — Railway just keeps the process alive.

---

## Pattern 8: GitHub Actions CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy to Railway

on:
  push:
    branches: [main]
  workflow_dispatch:   # Allow manual trigger

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Railway CLI
        run: npm install -g @railway/cli

      - name: Deploy to Railway
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: railway up --detach

      - name: Wait and Check Logs
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: |
          sleep 15
          railway logs --tail 50
```

**Setup:**
1. Get `RAILWAY_TOKEN` from Railway dashboard → Project Settings → Tokens
2. Add to GitHub: Repo → Settings → Secrets → `RAILWAY_TOKEN`
3. Push to `main` → triggers auto-deploy ✅

---

## Pattern 9: Database + API Combo (Full Stack)

```bash
# 1. Create project
railway init

# 2. Add PostgreSQL
railway add --plugin postgresql
# → DATABASE_URL auto-injected into all services ✅

# 3. Add Redis
railway add --plugin redis
# → REDIS_URL auto-injected ✅

# 4. Deploy API
cd api/
railway up --service api

# 5. Connect locally for migrations
railway connect postgresql
# → Opens psql, run your migrations

# 6. Check everything
railway logs --service api
```

---

## Pattern 10: Cron Job Service

Railway supports scheduled tasks natively.

**Dashboard:**
- New Service → Cron Job
- Set schedule (cron syntax): `0 2 * * *` (runs at 2am daily)
- Set command: `python scripts/cleanup.py`
- Set env vars via Variables tab

**CLI equiv:**
```bash
railway add  # Then select Cron Job type
```

Cron jobs run to completion, then stop — you only pay for runtime, not idle time. ✅
