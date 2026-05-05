# ✅ WHATS_DONE.md — HyperCode Ecosystem
> One file. Short bullets. No walls of text.
> **Updated: May 5, 2026 (evening BST)** — update this every session.

---

## 🏗️ THE 5 REPOS

| Repo | What it is | Where |
|---|---|---|
| HyperCode-V2.4 | Main platform — Docker, FastAPI, agents, infra | `H:\HyperStation zone\HyperCode\HyperCode-V2.4` |
| HyperAgent-SDK | TypeScript SDK — agent spec, CLI, templates | `H:\HyperAgent-SDK` |
| Hyper-Vibe-Coding-Course | Course frontend + Supabase + token shop | `H:\Hyper-Vibe-Coding-Course` |
| BROskiPets-LLM-dNFT | Pet NFT system — LLM + on-chain | `github.com/welshDog/BROskiPets-LLM-dNFT` |
| BROski-Obsidian-Brain | Second Brain vault — Obsidian + GitHub bridge | `H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne` ✅ May 5 |

---

## ✅ BUILT AND WORKING

### Infrastructure
- 48 Docker containers running ✅ (post-cleanup May 3)
- 5 isolated networks — `data-net` + `obs-net` internal (no internet) ✅
- Docker secrets pattern — `.txt` files, never baked into images ✅
- Kubernetes + Helm charts in `k8s/` + `helm/` — scale path ready ✅
- Memory limits on ALL services ✅
- `scripts/pre-build-check.sh` ✅ — aborts if <15GB free
- Socket-proxy split — main read-only, healer proxy write-only ✅ April 19
- Healer on obs-net — can reach Grafana/Prometheus for diagnostics ✅ April 19
- healthcheck IPv6 fix — hypercode-core uses `localhost` not `127.0.0.1` ✅ May 4
- Weekly cleanup: `docker system prune -a --filter "until=168h"`

### Observability
- Prometheus 7/7 targets UP ✅
- Grafana at `:3001` ✅
- OTLP traces live in Tempo ✅
- Loki + Promtail — log aggregation running ✅
- Gordon Tier 3 Grafana dashboard — KPI, pool stacks, queue depth, DLQ, heatmap ✅ April 19
- Gordon Tier 3 Prometheus alerts — 10 alerts (DB pool + Celery) ✅ April 19

### Backend (FastAPI — hypercode-core)
- `/metrics` Prometheus endpoint ✅
- `/health` with Redis cache (10s TTL) ✅
- Rate limiting — Redis DB 2, Stripe webhook exempt, memory:// in tests ✅
- Redis caching (`@cache_response`) — DB 1 ✅
- Circuit breakers — 3 active: `llm-router`, `crew-orchestrator`, `stripe-api` ✅
- Security headers middleware ✅
- Core deps split — `requirements.txt` core only, `requirements-ai.txt` optional AI ✅ April 23
- AI backend profile — `docker compose --profile ai up -d` ✅ April 23

### Database
- PostgreSQL running, Alembic migrations up to `009` ✅ April 19
- Async engine + connection pooling (`asyncpg`, pool_size=10) ✅
- Migration 009 — `pgcrypto` + `uuid-ossp` extensions ✅
- DB pool metrics — `DBPoolCollector` on `/metrics` ✅ April 19

### Stripe + Payments
- Full Stripe checkout + webhook + BROski$ awards ✅
- B3 E2E Stripe loop PROVED ✅ April 25
- `scripts/Test-ShopPurchase.ps1` — E2E test passing ✅ May 3
- **Stripe webhook secret updated + redeployed** ✅ May 5 🔥

### BROski$ Token Economy
- `public.users.broski_tokens` balance + `token_transactions` ledger ✅
- `award_tokens()` + `spend_tokens()` SECURITY DEFINER ✅
- Token grants: starter=200, builder=800, hyper=2500 ✅
- **BROski$ Obsidian Coin Tracker LIVE** ✅ May 5 (Dataview widget, Level 11)

### Course Frontend (Hyper-Vibe)
- `/pricing` → Stripe checkout → `/payment-success` → enrolled ✅
- Certificates, Quiz, Referral system ✅
- **`/welcome` hero onboarding page LIVE on Vercel** ✅ May 3
- **Security headers 6/6** ✅ (`frontend/vercel.json`)
- Dev command: `npm run dev:frontend` ✅ May 4

### Agents (25+)
- healer-agent, agent-x, crew-orchestrator, hyper-architect, hyper-observer ✅
- MCP-GitHub LIVE — 26 tools via `mcp-gateway` ✅
- crew-orchestrator forwards `X-API-Key` to agent `/execute` calls ✅
- coder-agent ↔ Ollama end-to-end working ✅
- **hyper-split-agent** ✅ April 25
- **broski-pets-bridge LIVE** ✅ April 29

### 🏆 Hyperfocus Features — ALL 5 DONE ✅
- Feature 1: Micro-Achievement Git Hook ✅ April 25
- Feature 2: HyperSplit Agent ✅ April 25
- Feature 3: Session Snapshot Agent ✅ April 25
- Feature 4: Morning Briefing `/briefing` ✅ April 26
- Feature 5: Focus/Panic Mode `make focus` / `make calm` ✅ April 26

### 🧠 BROski Brain — COMPLETE May 5 ✅
- **Repo:** `github.com/welshDog/BROski-Obsidian-Brain-for-HyperFocus-z0ne`
- Full PARA vault scaffold ✅
- 4 project notes pre-seeded (HyperCode, HyperAgent, BROskiPets, Hyper-Vibe) ✅
- Dashboard + Dataview live queries ✅
- Templates: Daily, Project, Task, Morning Briefing ✅
- BROski$ Coin Tracker — Dataview widget ✅ (Level 11)
- Focus/Calm/Hyper CSS modes ✅ (Level 12)
- GitHub bridge: `scripts/github_to_obsidian.py` — syncs 4 repos → vault ✅ (Level 9)
- Obsidian Git: auto-commits vault every 10 mins → GitHub ✅ (Level 10)
- Docker container: `docker/Dockerfile.github-sync` + compose ready ✅
- `setup.ps1` one-run bootstrap ✅
- **Levels 9, 10, 11, 12 ALL UNLOCKED** 🎮

### 🐾 BROskiPets
- broski-pets-bridge LIVE ✅ April 29
- Docker DNS fixed ✅
- IDOR hardened on pets endpoints ✅
- Cosmic Dragon minted + leaderboard live ✅
- XP confirmed: 0→10, streak day 1 ✅

### Security
- Trivy scanner running ✅ (CI blocked — GitHub billing lock)
- Socket-proxy least privilege ✅ April 19
- Stripe keys rotated + scrubbed from 218 commits ✅

### Celery
- `task_acks_late=True`, `worker_prefetch_multiplier=1` ✅
- `run_agent_task` with exponential backoff ✅
- Gordon Tier 3: soft/hard time limits, DLQ on max retries ✅ April 19
- Priority queues: high/normal/low + dlq (capped 10k) ✅ April 19
- Celery queue metrics — Counter + Histogram + Redis LLEN depth ✅ April 19

### HyperAgent-SDK
- `@w3lshdog/hyper-agent@0.1.7` published ✅
- CLI: validate, registry, studio, status, agents, tokens, graduate ✅

---

## 🔧 ONE-TIME MANUAL STEPS REMAINING

- [ ] Register Supabase DB Webhook: `token_transactions` → INSERT → `sync-tokens-to-v24`
- [ ] Fix GitHub Actions billing lock — github.com/settings/billing
- [ ] Add `env_file: .env` to `hypercode-core` in `docker-compose.yml`
- [ ] Set `VITE_STRIPE_PAYMENT_LINK_URL` in `.env.local` + Vercel env vars
- [ ] Add `DISCORD_USER_ID=<your_id>` to `.env` so `make calm` awards tokens correctly
- [ ] Add `GITHUB_PAT` to HyperCode-V2.4 `.env` + spin up `github-sync` Docker container

---

## 🚀 NEXT UP (in order)

1. **E2E checkout test** — card `4242 4242 4242 4242` — verify new webhook secret works end-to-end
2. **First student invite** — `/welcome` is green 🎓
3. **BROskiPets Phase 1** — mint first pet via BROski$
4. **HyperAgent-SDK Phase 2** — npm 0.2.0
5. **Fix GitHub Actions billing lock**
6. **Level 13** — Morning Briefing live
7. **Level 14** — GitHub Webhooks real-time
8. **Level 15** — HyperAgent AI Daily Briefing

---

## 🔑 KEY FACTS (never re-look-up)

```
Start command:   docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
AI backend:      docker compose --profile ai up -d
Discord bot:     docker compose --profile discord up -d broski-bot
Tests:           pytest backend/tests -q  (223 passed, 6 skipped)
Prometheus live: monitoring/prometheus/prometheus.yml
Redis DB split:  DB 1 = cache  |  DB 2 = rate limits
Stripe webhook:  ALWAYS rate-limit exempt
Alembic:         if missing → 'alembic stamp 008' then upgrade head (up to 009)
Supabase table:  courses uses price_pence (int) + is_active (bool)
Docker context:  must be 'desktop-linux' on Windows
Memory limits:   ALL services capped — agent-x=1G, core=1.5G, postgres=2G
healthcheck:     hypercode-core uses localhost not 127.0.0.1 (IPv6)
Pre-build check: make build → auto-runs pre-build-check.sh
make focus:      stops 14 non-essential containers + 25-min timer
make calm:       restores all + awards 75 BROski$
broski-pets:     health → http://localhost:8098/health
Course path:     H:\Hyper-Vibe-Coding-Course
Course dev:      npm run dev:frontend
Brain repo:      H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne
Brain vault:     HYPERFOCUS_ZONE/ folder inside brain repo
GitHub sync:     python scripts/github_to_obsidian.py (needs GITHUB_PAT env var)
Obsidian Git:    auto-commits vault every 10 mins to brain repo
IDE:             Trae IDE (Windows) + Claude Code terminal
Trae Pro:        expired May 2026 — Claude Code is agent brain this month
Stripe webhook:  secret updated May 5 ✅ — fresh whsec_ live in Supabase
```

---

## 📁 WHERE THINGS LIVE

```
docker-compose.yml                    — main stack
docker-compose.secrets.yml            — secrets injection
backend/app/main.py                   — FastAPI core
backend/app/core/config.py            — all settings
monitoring/prometheus/                — LIVE Prometheus config
frontend/vercel.json                  — Vercel config + security headers ✅
frontend/src/pages/Welcome.tsx        — hero onboarding page (LIVE)
scripts/Test-ShopPurchase.ps1         — E2E shop test
agents/                               — all agent code
secrets/                              — Docker secrets (.txt files, gitignored)
HYPER_ECOSYSTEM_PLAN_MAY4.md         — 4-repo master plan
BROski-Obsidian-Brain/scripts/        — github_to_obsidian.py + setup.ps1
BROski-Obsidian-Brain/docker/         — Dockerfile.github-sync + compose
```
