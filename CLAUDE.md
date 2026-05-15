# 🧠 HyperCode V2.4 — CLAUDE.md

> **This file is Claude's brain for this project.**
> Read this first. Every session. No exceptions.
> Last updated: **May 15, 2026 (08:13 BST)** — Env Preflight Checker LIVE ✅ + broski-bot Option A DONE 🤖🔥

---

## 🏴󠁧󠁢󠁷󠁬󠁳󠁥 Builder Context

**Lyndz Williams** (@welshDog) — Llanelli, South Wales
ADHD + Dyslexia + Autistic brain — hyperfocus mode is a superpower, not a bug ⚡
Building: The world's first neurodivergent-first autonomous AI infrastructure platform
Verdict from Gordon (Docker AI), April 15 2026:
> *"You built the future people keep saying they want. You actually did it."*

---

## ⚡ Communication Style (ALWAYS follow this)

- **Short sentences first** — then offer deeper explanation
- **Bullet points + headings** over walls of text
- **Why → How → Ready-to-use example** structure
- **Celebrate wins** — "Nice one BROski♾️!" is correct
- **Remind context** if there's been a pause between messages
- ADHD flow: break into steps, quick wins, no overwhelm
- If Lyndz goes quiet mid-task: check in, don't assume abandon

---

## 🔒 Sacred Rules (NEVER debate, NEVER change)

```
✔ docker-ce-cli          — NEVER docker.io for socket agents
✔ from app.X import Y    — NEVER from backend.app.X
✔ FastAPI public routes   — BEFORE auth-gated routes
✔ Stripe webhook          — rate-limit EXEMPT, always
✔ data-net + obs-net      — internal: true, never external
✔ .env files              — NEVER committed to git
✔ Commits                 — feat: fix: docs: chore: only
✔ Trivy target            — 0 CRITICAL per image
✔ Import style            — absolute imports, sys.path.insert at top
✔ Python indent           — 4 spaces, NEVER 3, NEVER mixed
✔ Stripe webhook          — NEVER add rate limiting to /api/stripe/webhook
✔ Redis DB split          — DB 1 = cache, DB 2 = rate limits. NEVER mix.
✔ hypercore healthcheck   — use localhost NOT 127.0.0.1 (IPv6 fix)
✔ Supabase ↔ V2.4         — NEVER merge schemas
```

---

## 📊 System Status (May 15, 2026 — 08:13 BST)

| Metric | Value |
|---|---|
| Containers | 48 running ✅ |
| Tests | 224 passed, 6 skipped ✅ (env_check tests added) |
| Prometheus targets | 7/7 UP ✅ |
| OTLP traces | LIVE in Tempo ✅ |
| Circuit breakers | 3 active — all CLOSED ✅ |
| Docker AI grade | A 🏅 |
| Stripe | LIVE 💳 (webhook secret updated May 5) |
| Gamification | FULL STACK LIVE (HUD, XP, Quests, Leaderboard) ✅ |
| BROskiPets Web3 | MINT LIVE on Base Sepolia 🔥 May 7 |
| BROski Brain | Levels 9–12 ✅ May 5 + Brain agents pushed May 15 ✅ |
| broski-bot | OPTION A LIVE 🤖 May 15 — `agents/broski-bot/` + profile:discord |
| discord-bot (legacy) | Reprofiled → `discord-lite` (won't auto-start) |
| Env Preflight Checker | LIVE ✅ May 15 — `scripts/env_check.py` + `scripts/env-check.sh` |
| HyperAgent-SDK | graduate build + trigger commands designed ✅ May 15 |
| Trae Pro | EXPIRED May 2026 — using Perplexity AI + Claude Code |

---

## 🏗️ Architecture Quick Ref

```
Networks:
  app-net     → core services (internal)
  data-net    → redis, postgres, chroma, minio (internal)
  obs-net     → prometheus, grafana, loki, tempo (internal)
  agent-net   → all agents
  agents-net  → broski-bot + hyper-agents

Key ports:
  8000  hypercode-core API
  8081  crew-orchestrator
  8088  hypercode-dashboard
  8095  hyperhealth-api
  8098  broski-pets-bridge
  9090  prometheus
  3001  grafana
  3100  loki
  3200  tempo
  6379  redis
  5432  postgres
```

---

## 🌐 The 5-Repo Ecosystem

```
Hyper-Vibe-Coding-Course     ──── manifest.json ────▶    HyperCode V2.4
github.com/welshDog/             (hyper-agent-spec)       github.com/welshDog/
Hyper-Vibe-Coding-Course                                  HyperCode-V2.4
(Supabase + Vercel + Web3)             │                  (Docker, 48 containers)
Path: H:\Hyper-Vibe-Coding-Course      │
⚠️ NOT H:\the hyper vibe coding hub    │
   (that = archived typo repo)         │
                              HyperAgent-SDK
                          github.com/welshDog/HyperAgent-SDK
                          npm: @w3lshdog/hyper-agent@0.1.7 (v0.3.0 code)
                          Path: H:\HyperAgent-SDK
                          graduate build + trigger commands = DESIGNED May 15
                                       │
                         BROskiPets-LLM-dNFT
                     github.com/welshDog/BROskiPets-LLM-dNFT
                     Path: H:\dNFTpet\BROskiPets-LLM-dNFT
                     (Pets · dNFT · port 8098)
                                       │
                      BROski-Obsidian-Brain-for-HyperFocus-z0ne
                     github.com/welshDog/BROski-Obsidian-Brain-for-HyperFocus-z0ne
                     Path: H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne
                     (Second Brain vault — PARA + Dataview + GitHub bridge)
                     cluster.json + 4 agent manifests PUSHED May 15 ✅
```

---

## 🏆 Full Phase Roadmap

| Phase | Name | Status |
|---|---|---|
| 0–9 | Identity, tokens, agents, shop, observability, security | ✅ ALL DONE |
| 10A–10P | FastAPI, Stripe, courses, DB recovery, secrets | ✅ ALL DONE |
| 11A–11F | Live HUD, Rift Events, Gamification schema, E2E | ✅ DONE — April 26 |
| 12A–12F | Leaderboard, Quests, Admin Rift Panel, Migrations | ✅ DONE — April 26 |
| Gordon Tier 1–3 | Prometheus, Grafana, Celery, DB pool, queues | ✅ ALL DONE — April 19 |
| Hyperfocus Features 1–5 | Git hook, HyperSplit, Snapshot, Briefing, Focus mode | ✅ DONE — April 25–26 |
| BROskiPets Phase 0–1 | Bridge live, XP, leaderboard | ✅ DONE — April 29 |
| BROski Brain Levels 9–12 | PARA vault, GitHub bridge, Obsidian Git, Dataview | ✅ DONE — May 5 |
| Edge Functions | All 4 Supabase edge functions fixed + deployed | ✅ DONE — May 1 |
| Vercel Hardening | Security headers, chunk split, env vars | ✅ DONE — May 3–5 |
| BUSINESS_PLAN v1.1 | Sponsor-ready plan + pricing align | ✅ DONE — May 5 |
| BROskiPets Web3 Mint | RainbowKit + wagmi + Base Sepolia + mint UI | ✅ LIVE — May 7 🔥 |
| **HyperAgent Graduate Build** | `graduate build` + `graduate trigger` CLI design | ✅ **DESIGNED — May 15** |
| **Brain Agent Cluster** | cluster.json + 4 agent manifests → Obsidian Brain repo | ✅ **PUSHED — May 15** |
| **Discord Bot Tier 1** | Economy + AI chat + Focus Tracker + Daily Missions | ✅ **LIVE — May 15** 🤖 |
| **broski-bot Option A** | Profile-gated `agents/broski-bot/` + bind mounts | ✅ **DONE — May 15** 🤖 |
| **Env Preflight Checker** | `scripts/env_check.py` + bash wrapper + tests | ✅ **DONE — May 15** 🛡️ |

---

## 🔥 ACTIVE NEXT STEPS

| # | Task | Priority |
|---|---|---|
| 1 | **Fill `agents/broski-bot/.env`** — TOKEN, SUPABASE keys, GUILD_ID, MISSIONS_CHANNEL_ID | 🔴 NOW |
| 2 | **Run supabase_schema.sql** in Supabase SQL editor | 🔴 NOW |
| 3 | **Run env-check** — `python scripts/env_check.py --core --secrets --profile discord` | 🔴 NOW |
| 4 | **Launch bot** — `docker compose --profile discord up -d` | 🔴 NOW |
| 5 | **HyperAgent graduate build** — implement CLI from May 15 design doc | 🔴 This week |
| 6 | **Discord Bot Tier 2** — Pets, XP Leaderboard, Morning Briefing, Health Alerts | 🟡 Next sprint |
| 7 | E2E Stripe checkout test — card `4242 4242 4242 4242` | 🟡 This week |
| 8 | BROskiPets Web3 E2E — test mint on Base Sepolia testnet | 🟡 This week |
| 9 | Supabase DB webhook — `token_transactions` → `sync-tokens-to-v24` | 🟡 Manual |
| 10 | First student invite — `/welcome` is green 🎓 | 🟡 This week |
| 11 | SDK v0.4.0 — add Web3/dNFT types to `hyper-agent-spec.json` | 🟡 This week |
| 12 | Fix GitHub Actions billing lock | 🟡 This week |
| 13 | Upgrade GitPython → 3.1.47 (CVE-2026-42215 + CVE-2026-42284) | 🟡 This week |
| 14 | Level 13 — Morning Briefing live (Discord Bot Tier 2) | 🟢 Background |

---

## 🤖 broski-bot — ONE TRUE BOT (May 15 2026)

**Location:** `agents/broski-bot/` — **NOT** `discord-bot/` (that is legacy, reprofiled to `discord-lite`)

### Run commands:
```bash
# Core only (no bot):
docker compose up -d

# Bot + core:
docker compose --profile discord up -d

# Bot only:
docker compose --profile discord up -d broski-bot

# Verify config:
docker compose config
docker compose --profile discord config
```

### ✅ Tier 1 DONE (May 15)
| Feature | Commands |
|---|---|
| 💰 BROski$ Economy | `/balance` `/earn` `/spend` `/give` |
| 🧠 AI Chat → FastAPI | `/broski` `/ask` |
| 🎯 Focus Tracker + XP | `/focus start` `/focus stop` `/focusstats` |
| 📋 Daily Missions | `/missions` + auto-post 8am UTC (9am BST) |

### 🟡 Tier 2 TODO
- 🐾 BROski Pets integration — `/pet` shows stats, feed with coins
- 🏆 XP Leaderboard — `/leaderboard` pulls from Supabase
- 🌅 Morning Briefing — auto-DM/post from Morning Briefing agent
- 🚨 System Health Alerts — bot posts when V2.4 containers go down

### 🔮 Tier 3 TODO
- 🎰 BROski$ Shop — buy roles, badges with coins
- 🤖 Agent Summoner — `/run-agent` triggers HyperAgent SDK agents
- 📸 NFT/Pet Showcase — auto-post minted pets to #showcase
- 📈 Stats Dashboard — `/stats` live embed with hyperfocus score

### Persistence (bind mounts survive rebuilds):
```
HC_DATA_ROOT/broski-bot/db
HC_DATA_ROOT/broski-bot/logs
HC_DATA_ROOT/broski-bot/backups
```

### FastAPI endpoints the bot calls:
- `POST /ai/chat` — BROski AI full chat
- `POST /ai/quick` — Quick Q&A

---

## 🛡️ Env Preflight Checker (May 15 2026)

**Files:**
- Engine: `scripts/env_check.py`
- Bash wrapper: `scripts/env-check.sh`
- Spec: `docs/superpowers/specs/2026-05-15-env-check-design.md`
- Plan: `docs/superpowers/plans/2026-05-15-env-check-implementation-plan.md`
- Tests: `backend/tests/unit/test_env_check_script.py` ✅ passing

**How to run (never prints values — keys only):**
```powershell
# PowerShell (recommended):
python scripts/env_check.py --core --secrets --profile discord

# Bash:
bash scripts/env-check.sh --core --secrets --profile discord

# Full stack check:
python scripts/env_check.py --core --secrets --profile discord --brain --grafana-cloud
```

**Current known issues it catches:**
- broski-bot `.env` missing: `BOT_*_PATH`, `FASTAPI_BASE`, `GUILD_ID`, `MISSIONS_CHANNEL_ID`, `SUPABASE_URL`, `SUPABASE_KEY`
- Root `.env` duplicate warnings: `BROSKIE_PETS_ENABLED`, `PETS_WEBHOOK_SECRET`

**Rule:** Always run env-check BEFORE `docker compose up` on a new machine or after `.env` changes.

---

## 🧠 HyperAgent Graduate Build — May 15 2026

**Design doc:** `2026-05-15-graduate-build-design.md`

### Commands designed:
```bash
hyper-agent graduate build <cluster.json> --out <dir> [--strict] [--json]
hyper-agent graduate trigger <discord_id> [--tokens 500] [--json]
```

### Build output:
```
out/
  docker-compose.agents.yml
  README.md
  Dockerfile.<agent-name>
  agents/<agent-name>/manifest.json
```

### Secret priority:
- `COURSE_SYNC_SECRET` first → fallback `SHOP_SYNC_SECRET`

### Status: **DESIGNED** ✅ — implementation TODO in HyperAgent-SDK

---

## 🧠 BROski Brain Agent Cluster — May 15 2026

**Repo:** BROski-Obsidian-Brain-for-HyperFocus-z0ne

**Pushed:**
- `cluster.json` — defines the 4-agent brain cluster
- `.agents/hyper-brain-core/manifest.json`
- `.agents/mcp-bridge/manifest.json`
- `.agents/focus-tracker/manifest.json`
- `.agents/morning-briefing/manifest.json`

**Next:** Run `hyper-agent graduate build cluster.json --out brain-bundle/ --strict` once SDK is implemented

---

## 📌 Known Issues / Tech Debt

| Issue | Fix | Priority |
|---|---|---|
| broski-bot `.env` not filled yet | Fill `agents/broski-bot/.env` with real values | 🔴 HIGH |
| Supabase schema not yet run | Run `discord-bot/supabase_schema.sql` in Supabase SQL editor | 🔴 HIGH |
| HyperAgent graduate build not yet implemented | Build CLI from May 15 design doc | 🟡 MED |
| Stale root `prometheus.yml` | Delete/archive — live = `monitoring/prometheus/prometheus.yml` | 🟡 MED |
| GitHub Actions billing lock | Fix at github.com/settings/billing | 🟡 MED |
| GitPython 3.1.45 CVEs | Upgrade to 3.1.47 (CVE-2026-42215 + CVE-2026-42284) | 🟡 MED |
| SDK not reflecting Web3 types | Bump HyperAgent-SDK to v0.4.0 + update hyper-agent-spec.json | 🟡 MED |
| `/welcome` auth-gated | Decide: make public? Sponsors hit login wall from BUSINESS_PLAN | 🟡 |
| `VITE_STRIPE_PAYMENT_LINK_URL` empty | Set in `.env.local` + Vercel env vars | 🟢 LOW |
| `DISCORD_USER_ID` not set | Add to `.env` for `make calm` token awards | 🟢 LOW |

---

## 📦 Key Files

```
docker-compose.yml              — main stack
docker-compose.secrets.yml      — secrets injection
docker-compose.core.yml         — core + broski-bot (profile:discord) + discord-bot (profile:discord-lite)
backend/app/main.py             — FastAPI core app
agents/broski-bot/main.py       — ONE TRUE BOT (May 15) ← use this
agents/broski-bot/.env.example  — bot env template (all 8 keys present)
discord-bot/                    — LEGACY — reprofiled discord-lite, do not use
discord-bot/supabase_schema.sql — DB tables for bot (still need to run in Supabase!)
scripts/env_check.py            — env preflight checker (NEW May 15)
scripts/env-check.sh            — bash wrapper for env_check.py
monitoring/prometheus/          — ACTIVE Prometheus config
grafana/                        — dashboards
agents/                         — all agent code
scripts/STRIPE_E2E_RUNBOOK.md   — Stripe E2E test steps
CLAUDE_CONTEXT.md               — extended project context
docs/INDEX.md                   — master docs navigation
docs/superpowers/specs/         — feature spec docs
docs/superpowers/plans/         — implementation plans
```

---

## 🧪 Testing Commands

```powershell
# Health checks:
curl http://localhost:8000/health
curl http://localhost:8081/health
curl http://localhost:8095/health
curl http://localhost:8098/health    # broski-pets-bridge

# Run tests:
pytest backend/tests/ -q    # 224 passed, 6 skipped
pytest backend/tests/unit/test_env_check_script.py -v   # NEW May 15

# Env preflight (run before any docker compose up!):
python scripts/env_check.py --core --secrets --profile discord

# Docker status:
docker compose ps
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr -v "healthy"

# Start everything — FULL STACK:
docker compose -f docker-compose.yml -f docker-compose.secrets.yml -f docker-compose.brain.yml -f docker-compose.grafana-cloud.yml --profile discord up -d

# Core only:
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d

# Core + bot:
docker compose -f docker-compose.yml -f docker-compose.secrets.yml --profile discord up -d

# Course frontend:
cd H:\Hyper-Vibe-Coding-Course
npm run dev:frontend

# Stripe E2E:
stripe listen --forward-to localhost:8000/api/stripe/webhook

# Circuit breakers:
curl localhost:8000/api/v1/health | jq .circuit_breakers

# DB recovery (if auth breaks):
docker exec -it postgres psql -U postgres
# ALTER USER postgres WITH PASSWORD 'hypercode';
```

---

## 🏆 Achievements Unlocked

- ✅ Gordon Docker AI: **Grade A** — *"world-class infrastructure"*
- ✅ 29/29 → 48 containers healthy
- ✅ Self-healing closed loop (Healer → Prometheus → Alertmanager → recovery)
- ✅ Neurodivergent-first design recognised as *rare* by Docker AI
- ✅ Gordon Tier 1 + 2 + 3 ALL COMPLETE
- ✅ Full Gamification Stack — HUD, XP, Quests, Leaderboard, Rifts
- ✅ All 5 Hyperfocus Features LIVE
- ✅ BROski Brain v2.2 — Levels 9–12 unlocked
- ✅ MCP-GitHub LIVE — 26 tools via Docker MCP gateway
- ✅ Stripe LIVE — E2E proven April 25
- ✅ Course frontend → Stripe → enrolled: full money path
- ✅ BUSINESS_PLAN.md v1.1 — sponsor-ready
- ✅ BROskiPets Web3 Mint LIVE — May 7 🔥🐾
- ✅ **HyperAgent Graduate Build DESIGNED — May 15** 📐
- ✅ **Brain Agent Cluster PUSHED — May 15** 🧠
- ✅ **BROski Discord Bot Tier 1 LIVE — May 15** 🤖🎉
- ✅ **broski-bot Option A wired — May 15** 🐳 (profile:discord, bind mounts, ONE TRUE BOT)
- ✅ **Env Preflight Checker LIVE — May 15** 🛡️ (env_check.py + tests passing)

---

## 👋 For New Claude/Perplexity Sessions

Hey! Working with Lyndz Williams on HyperCode V2.4.

1. **Read this file first** — especially the Sacred Rules
2. **Check WHATS_DONE.md** — do NOT suggest anything listed there
3. **5 repos** — HyperCode-V2.4, HyperAgent-SDK, Hyper-Vibe-Coding-Course, BROskiPets-LLM-dNFT, BROski-Obsidian-Brain
4. **ONE TRUE BOT** = `agents/broski-bot/` (profile:discord) — NOT `discord-bot/` (legacy, discord-lite only)
5. **Env checker** = `python scripts/env_check.py --core --secrets --profile discord` — run before any `docker compose up`
6. **Graduate build designed** (May 15) — needs implementing in HyperAgent-SDK
7. **Brain agents pushed** (May 15) — cluster.json + 4 manifests in Obsidian Brain repo
8. **Next priorities** — Fill broski-bot .env → run Supabase schema → `docker compose --profile discord up -d`
9. **Style:** Short. Friendly. BROski energy. Celebrate wins. 🏆
10. **Never:** Wall of text. Never debate Sacred Rules.

> *"You built the future people keep saying they want. You actually did it." — Gordon, Docker AI* 🏴󠁧󠁢󠁷󠁬󠁳󠁥🔥
