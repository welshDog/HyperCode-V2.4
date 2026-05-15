# ✅ WHATS_DONE.md — HyperCode Ecosystem
> One file. Short bullets. No walls of text.
> **Updated: May 15, 2026** — update this every session.

---

## 🏗️ THE 5 REPOS

| Repo | What it is | Where |
|---|---|---|
| HyperCode-V2.4 | Main platform — Docker, FastAPI, agents, infra | `H:\HyperStation zone\HyperCode\HyperCode-V2.4` |
| HyperAgent-SDK | TypeScript SDK — agent spec, CLI, templates | `H:\HyperAgent-SDK` |
| Hyper-Vibe-Coding-Course | Course frontend + Supabase + token shop + Web3 pets | `H:\Hyper-Vibe-Coding-Course` |
| BROskiPets-LLM-dNFT | Pet NFT system — LLM + on-chain | `H:\dNFTpet\BROskiPets-LLM-dNFT` |
| BROski-Obsidian-Brain | Second Brain vault — Obsidian + GitHub bridge | `H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne` ✅ May 5 |

---

## ✅ BUILT AND WORKING

### 🔥 May 15, 2026 — Discord “One Brain” Lock-In
- **Option A enforced:** `broski-bot` calls Core only — no Supabase in bot ✅
- **Discord bot library locked:** `discord.py==2.4.0` ✅
- **Bot entrypoint locked:** `python -u -m cogs.bot` ✅
- **Core “One Door” endpoint:** `POST /api/v1/discord/actions` + idempotency ✅
- Premium Discord embeds: medals + colors + mentions + comma formatting ✅
- `scripts/env_check.py` keys-only preflight for `.env` + secrets + profiles ✅

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
- Claude hyper skill zip added ✅ May 7

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
- Stripe webhook secret updated + redeployed ✅ May 5 🔥

### BROski$ Token Economy
- `public.users.broski_tokens` balance + `token_transactions` ledger ✅
- `award_tokens()` + `spend_tokens()` SECURITY DEFINER ✅
- Token grants: starter=200, builder=800, hyper=2500 ✅
- BROski$ Obsidian Coin Tracker LIVE ✅ May 5 (Dataview widget, Level 11)

### Course Frontend (Hyper-Vibe)
- `/pricing` → Stripe checkout → `/payment-success` → enrolled ✅
- Certificates, Quiz, Referral system ✅
- `/welcome` hero onboarding page LIVE on Vercel ✅ May 3
- Security headers 6/6 ✅ (`frontend/vercel.json`)
- Dev command: `npm run dev:frontend` ✅ May 4
- BUSINESS_PLAN.md v1.1 — sponsor-ready, corrected pricing (£9 Pro / £29 Hyper) ✅ May 5
- Vercel env vars — VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY on ALL 3 environments ✅ May 5
- `/register` Failed to fetch bug FIXED ✅ May 5
- Dead asset cleanup — phantom preload + unused hero.webp removed ✅ May 5

### 🐾 BROskiPets — WEB3 MINT LIVE 🔥 (May 7, 2026)
- broski-pets-bridge LIVE ✅ April 29
- Docker DNS fixed ✅
- IDOR hardened on pets endpoints ✅
- Cosmic Dragon minted + leaderboard live ✅
- XP confirmed: 0→10, streak day 1 ✅
- **RainbowKit + wagmi + viem Web3 wallet integration** ✅ May 7
- **Base Sepolia testnet + Base mainnet configured** ✅ May 7
- **`useMintPet` hook — two-step mint flow (Edge Function auth + on-chain tx)** ✅ May 7
- **Supabase Edge Functions: mint auth + pet balance check** ✅ May 7
- **Supabase migrations: mint_nonces + pet ID sequencing** ✅ May 7
- **CSP headers updated** for WalletConnect + blockchain RPC endpoints ✅ May 7
- **10 pet species images + species catalogue with metadata** ✅ May 7
- **SpeciesPicker component** — visual species selection ✅ May 7
- **MintPetButton** — wallet connection + balance check + full mint flow ✅ May 7
- **Pets page rebuilt** — three-step mint interface ✅ May 7
- **Pinata dry-run upload** scripts added to Claude settings ✅ May 7

### Agents (25+)
- healer-agent, agent-x, crew-orchestrator, hyper-architect, hyper-observer ✅
- MCP-GitHub LIVE — 26 tools via `mcp-gateway` ✅
- crew-orchestrator forwards `X-API-Key` to agent `/execute` calls ✅
- coder-agent ↔ Ollama end-to-end working ✅
- hyper-split-agent ✅ April 25
- broski-pets-bridge LIVE ✅ April 29

### 🏆 Hyperfocus Features — ALL 5 DONE ✅
- Feature 1: Micro-Achievement Git Hook ✅ April 25
- Feature 2: HyperSplit Agent ✅ April 25
- Feature 3: Session Snapshot Agent ✅ April 25
- Feature 4: Morning Briefing `/briefing` ✅ April 26
- Feature 5: Focus/Panic Mode `make focus` / `make calm` ✅ April 26

### 🧠 BROski Brain — COMPLETE May 5 ✅
- Repo: `github.com/welshDog/BROski-Obsidian-Brain-for-HyperFocus-z0ne`
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
- Levels 9, 10, 11, 12 ALL UNLOCKED 🎮

### Security
- Trivy scanner running ✅ (CI blocked — GitHub billing lock)
- Socket-proxy least privilege ✅ April 19
- Stripe keys rotated + scrubbed from 218 commits ✅
- Trivy CVE-2026-42215 + CVE-2026-42284 in GitPython 3.1.45 flagged → fix: upgrade to 3.1.47 ⚠️ May 7

### Celery
- `task_acks_late=True`, `worker_prefetch_multiplier=1` ✅
- `run_agent_task` with exponential backoff ✅
- Gordon Tier 3: soft/hard time limits, DLQ on max retries ✅ April 19
- Priority queues: high/normal/low + dlq (capped 10k) ✅ April 19
- Celery queue metrics — Counter + Histogram + Redis LLEN depth ✅ April 19

### HyperAgent-SDK
- `@w3lshdog/hyper-agent@0.1.7` published ✅
- CLI: validate, registry, studio, status, agents, tokens, graduate ✅
- v0.3.0 — `awardFromCourse` client — server-only, idempotency via sourceId ✅ April 30
- TypeScript + MCP starter templates + `init` command ✅ April 30
- 57 tests passing ✅
- **⚠️ SDK needs update** — Web3/dNFT types not yet in `hyper-agent-spec.json` — bump to v0.4.0

---

## 🔧 ONE-TIME MANUAL STEPS REMAINING

- [ ] Register Supabase DB Webhook: `token_transactions` → INSERT → `sync-tokens-to-v24`
- [ ] Fix GitHub Actions billing lock — github.com/settings/billing
- [ ] Add `env_file: .env` to `hypercode-core` in `docker-compose.yml` (tech debt)
- [ ] Set `VITE_STRIPE_PAYMENT_LINK_URL` in `.env.local` + Vercel env vars
- [ ] Add `DISCORD_USER_ID=<your_id>` to `.env` so `make calm` awards tokens correctly
- [ ] Add `GITHUB_PAT` to HyperCode-V2.4 `.env` + spin up `github-sync` Docker container
- [ ] Upgrade GitPython to 3.1.47 — fixes CVE-2026-42215 + CVE-2026-42284
- [ ] V2.4 check: does `mint_nonces` Supabase migration need a matching endpoint/hook in V2.4?
- [ ] SDK bump to v0.4.0 — add Web3/dNFT types to `hyper-agent-spec.json`

---

## 🚀 NEXT UP (in order)

1. **E2E checkout test** — card `4242 4242 4242 4242` — verify new webhook secret end-to-end
2. **BROskiPets Web3 E2E** — test mint on Base Sepolia testnet with real wallet
3. **First student invite** — `/welcome` is green 🎓
4. **HyperAgent-SDK v0.4.0** — Web3/dNFT types in spec
5. **Fix GitHub Actions billing lock**
6. **Level 13** — Morning Briefing live
7. **Level 14** — GitHub Webhooks real-time
8. **Level 15** — HyperAgent AI Daily Briefing

---

## 🔑 KEY FACTS (never re-look-up)

```
Start command:    docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
AI backend:       docker compose --profile ai up -d
Discord bot:      docker compose --profile discord up -d broski-bot
Tests:            pytest backend/tests -q  (241 passed, 6 skipped)
Prometheus live:  monitoring/prometheus/prometheus.yml
Redis DB split:   DB 1 = cache  |  DB 2 = rate limits
Stripe webhook:   ALWAYS rate-limit exempt
Alembic:          if missing → 'alembic stamp 008' then upgrade head (up to 009)
Supabase table:   courses uses price_pence (int) + is_active (bool)
Docker context:   must be 'desktop-linux' on Windows
Memory limits:    ALL services capped — agent-x=1G, core=1.5G, postgres=2G
healthcheck:      hypercode-core uses localhost not 127.0.0.1 (IPv6)
Pre-build check:  make build → auto-runs pre-build-check.sh
make focus:       stops 14 non-essential containers + 25-min timer
make calm:        restores all + awards 75 BROski$
broski-pets:      health → http://localhost:8098/health
Course path:      H:\Hyper-Vibe-Coding-Course
Course dev:       npm run dev:frontend
Brain repo:       H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne
Brain vault:      HYPERFOCUS_ZONE/ folder inside brain repo
GitHub sync:      python scripts/github_to_obsidian.py (needs GITHUB_PAT env var)
Obsidian Git:     auto-commits vault every 10 mins to brain repo
IDE:              Claude Code terminal + Perplexity AI (Windows)
Trae Pro:         expired May 2026 — Claude Code is agent brain this month
Stripe webhook:   secret updated May 5 ✅ — fresh whsec_ live in Supabase
BROskiPets Web3:  RainbowKit + wagmi + Base Sepolia — mint live May 7 🔥
Pets page:        three-step mint interface — SpeciesPicker → MintPetButton
Mint flow:        Edge Function auth → on-chain Base Sepolia tx
CSP headers:      updated for WalletConnect + blockchain RPC ✅ May 7
GitPython:        upgrade to 3.1.47 — CVE-2026-42215 + CVE-2026-42284 ⚠️
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
scripts/STRIPE_E2E_RUNBOOK.md         — Stripe E2E test steps
agents/                               — all agent code
secrets/                              — Docker secrets (.txt files, gitignored)
HYPER_ECOSYSTEM_PLAN_MAY4.md         — 4-repo master plan
BROski-Obsidian-Brain/scripts/        — github_to_obsidian.py + setup.ps1
BROski-Obsidian-Brain/docker/         — Dockerfile.github-sync + compose
```
