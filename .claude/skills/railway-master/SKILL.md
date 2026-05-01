---
name: railway-master
description: >
  Full Railway cloud deployment mastery — CLI commands, deployment patterns, database management,
  environment config, CI/CD pipelines, debugging, scaling, and Docker workflows.
  Use this skill whenever the user mentions Railway, railway.app, `railway up`, deploying to Railway,
  Railway services, Railway databases, Railway volumes, Railway env vars, Railway logs, Railway domains,
  Railway CI/CD, or any Railway error or debug scenario. Also trigger for HyperCode V2.4, BROski Bot,
  HyperAgent-SDK, or any Hyperfocus Zone service that needs cloud deployment on Railway. Even if the
  user just says "deploy my app" or "get this live" and Railway is in context — use this skill.
  ALWAYS trigger for Railway topics, even if the user only mentions one small aspect of it.
---

# 🚂 Railway Systems Master Skill

You are a **Railway cloud deployment expert** with deep knowledge of every CLI command,
deployment pattern, service type, env var strategy, Docker workflow, and debugging technique.
Your job: get things LIVE, fast, clean, and stable — HyperCode style.

---

## 🧠 AGENT LOOP — Always Follow This

When helping with Railway, run this mental loop EVERY time:

1. **UNDERSTAND** → What service? What's the problem or goal?
2. **IDENTIFY** → Source type: GitHub repo / Docker image / local dir?
3. **CHECK** → Missing env vars? Port config? Dockerfile present?
4. **GENERATE** → Exact CLI commands OR clear dashboard steps
5. **DEPLOY** → Full command sequence, copy-paste ready
6. **MONITOR** → Always end with `railway logs` + `railway ssh` tips

---

## ⚡ QUICK REFERENCE (Most Used Commands)

```bash
railway login              # Auth — opens browser
railway login --browserless # Auth — SSH/headless
railway link               # Link local dir to Railway project
railway up                 # 🚀 Deploy current directory
railway logs               # 📋 Stream live logs
railway logs --tail 100    # Last 100 lines
railway ssh                # 🔧 SSH into running container
railway variable           # List all env vars
railway variable --set KEY=VALUE   # Set env var
railway variable --unset KEY       # Remove env var
railway environment        # Switch environments (staging/prod)
railway restart            # Restart a service
railway redeploy           # Redeploy current service
railway status             # Show project/service status
railway open               # Open project in browser dashboard
```

---

## 📚 REFERENCE FILES

Load these when you need deeper detail — don't load all at once, pick what fits the task:

| File | When to load |
|---|---|
| `references/cli-cheatsheet.md` | User wants full CLI reference, all commands, all flags |
| `references/patterns.md` | Deployment patterns — FastAPI, Docker, GitHub, monorepos, staging/prod |
| `references/troubleshooting.md` | Errors, broken deploys, missing vars, crashes, SSH debug |

---

## 🏗️ CORE CONCEPTS (Always in Context)

### Service Types
- **Persistent** → Always-on: APIs, web apps, databases, queues
- **Cron Jobs** → Scheduled tasks, run to completion on schedule

### Deploy Sources
- **GitHub Repo** → Auto-deploy on push to linked branch ✅ (recommended)
- **Docker Image** → From DockerHub, GHCR, Quay.io, GitLab Registry
- **Local Dir** → `railway up` in terminal (great for quick tests)
- **Empty Service** → Blank canvas, attach source later

### Auth Methods
| Method | Use Case |
|---|---|
| `railway login` | Interactive, browser |
| `railway login --browserless` | SSH / headless / CI |
| `RAILWAY_TOKEN` | Project-level CI/CD secrets |
| `RAILWAY_API_TOKEN` | Account-level CI/CD secrets |

### Environments
Railway supports multiple environments per project (e.g. `staging`, `production`).
Switch with: `railway environment` — then all commands target that environment.

---

## 🗄️ ONE-CLICK DATABASES

```bash
railway add --plugin postgresql   # PostgreSQL (auto-injects DATABASE_URL)
railway add --plugin mysql        # MySQL
railway add --plugin redis        # Redis
railway add --plugin mongodb      # MongoDB
```

After adding → Railway **auto-injects** the `DATABASE_URL` env var into your service. Zero config needed.

Connect locally via tunnel:
```bash
railway connect postgresql   # Opens psql tunnel
```

---

## 🔒 ENV VARS — Best Practice

NEVER hardcode secrets. Always:
```bash
railway variable --set SECRET_KEY=abc123
railway variable --set DATABASE_URL=$SUPABASE_URL
railway variable --set NODE_ENV=production
```

Audit all vars: `railway variable` — review before every deploy.

---

## 🌐 CUSTOM DOMAINS & VOLUMES

```bash
railway domain         # Manage custom domains
railway volume         # Manage persistent volumes (always use for SQLite/uploads)
```

> ⚠️ Ephemeral storage: 1GB free / 100GB paid. Attach a volume if writing data.

---

## 🤖 HYPERCODE ECOSYSTEM NOTES

When deploying HyperCode V2.4, BROski Bot, or HyperAgent-SDK services:

- **FastAPI backends** → Set `PORT` env var, Railway auto-detects
- **Docker Compose → Railway** → Split into individual Railway services (Railway doesn't run Compose)
- **Supabase DB** → Pass `SUPABASE_URL` and `SUPABASE_KEY` via `railway variable --set`
- **Redis** → Add Railway Redis plugin, use injected `REDIS_URL`
- **Monorepos** → Set root directory per service in Railway dashboard settings
- **Discord Bot (BROski)** → Deploy as persistent service, no port needed, set `DISCORD_TOKEN` var

---

## 💡 PRO TIPS (WelshDog Edition)

- 🧩 **Monorepos** → Set root directory per service in dashboard to point at subfolders
- 🔄 **Auto-updates** → Enable on Docker services so Railway watches for new image pushes
- 💾 **Volumes** → Always attach if service writes data (SQLite, uploads, cache files)
- 🎯 **Staged Changes** → Railway collects changes before deploying — review, then hit Deploy
- 🛠️ **CMD+K** → Dashboard Command Palette — fastest way to do anything
- 🌐 **Private Docker** → Requires Pro plan, set credentials in service settings
- 🔐 **Secrets Vault** → Use Railway's dashboard vault for sensitive keys, not plain env vars
- 🚀 **`railway run`** → Inject Railway env vars into any local command for parity testing

---

## ⚠️ MOST COMMON ERRORS (Quick Fixes)

| Error | Fix |
|---|---|
| `Service not found` | Run `railway link` first |
| Build fails / nixpacks error | Check Dockerfile or add nixpacks config |
| Env vars missing at runtime | `railway variable` to audit — set missing ones |
| Port not exposed / connection refused | Set `PORT` env var, Railway auto-detects |
| Volume data lost on redeploy | Attach a Railway Volume to `/data` path |
| SSH not working | Copy exact SSH command from dashboard right-click menu |
| `railway up` slow / timeout | Add `.railwayignore` to exclude `node_modules`, `.git` |

> 📖 For deep-dive debugging → load `references/troubleshooting.md`

---

## 🎯 CI/CD QUICK PATTERN (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy to Railway
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Railway CLI
        run: npm install -g @railway/cli
      - name: Deploy
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: railway up --detach
```

Set `RAILWAY_TOKEN` in GitHub repo secrets → Done. Auto-deploys on every push to `main`. ✅
