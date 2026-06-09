# 🧠 HYPERFOCUS z0ne — Ecosystem Constitution (root CLAUDE.md)
> **For ANY AI assistant — Claude, Perplexity, GPT, Gemini — read this first.**
> Last updated: **June 9, 2026**
> Lean rewrite: status, tasks, roadmap, achievements moved to `docs/` (see §0 for links).

---

## 0. 📖 Read Order — Every Session

1. **This file** — sacred rules, ecosystem map, architecture, commands
2. **Live state** → `docs/STATUS.md` — current container/service health
3. **Next tasks** → `docs/NEXT_TASKS.md` — what to build next
4. **Working in the Course?** → `Hyper-Vibe-Coding-Course/CLAUDE.md` + `rewrites/NEXT_SESSION_HANDOVER_[latest].md`
5. **Working in V2.4?** → `HyperCode-V2.4/CLAUDE.md` (this file IS that)
6. **Check `WHATS_DONE.md`** — NEVER suggest anything already listed there
7. **Touching DB?** → check `supabase/migrations/` for the latest migration number first
8. **Then build.** Not before.

> Repo-level SESSION_SNAPSHOT = living state. This file = constitution.
> If they contradict, **surface it — don't silently pick one.**

**Other docs:**
- `docs/TECH_DEBT.md` — known issues + priorities
- `docs/ROADMAP.md` — full phase history
- `docs/ACHIEVEMENTS.md` — all-time wins log

---

## 1. ⚡ Communication Rules (ALWAYS follow these)

- **Short sentences first** — offer deeper explanation only if asked
- **Why → How → Ready-to-use example** structure
- **Bullet points + headings** over walls of text
- **Celebrate wins** — "Nice one BROski♾️!" is correct and encouraged
- ADHD flow: chunk it, quick wins first, no overwhelm
- If Lyndz goes quiet mid-task — check in gently, don't assume abandoned
- **Surface contradictions** — correct the doc visibly, never silently pick a side
- **Never say "human must test"** when Playwright applies (it's installed — use it)
- **NEVER** produce walls of text unprompted

---

## 2. 🌐 The 5-Repo Ecosystem

```
Hyper-Vibe-Coding-Course     ──── manifest.json ────▶    HyperCode V2.4
github.com/welshDog/             (hyper-agent-spec)       github.com/welshDog/
Hyper-Vibe-Coding-Course                                  HyperCode-V2.4
(Supabase + Vercel + Web3)             │                  (Docker, ~30 containers)
Path: H:\Hyper-Vibe-Coding-Course      │
⚠️ NOT H:\the hyper vibe coding hub    │
   (that = archived typo repo)         │
                              HyperAgent-SDK
                          github.com/welshDog/HyperAgent-SDK
                          npm: @w3lshdog/hyper-agent@0.1.7
                          Path: H:\HyperAgent-SDK
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
```

> Aggregator root: `H:\HYPERFOCUSZONE\HperCore` — all 5 repos cloned as subdirectories.

| Repo | Purpose | Local Path |
|---|---|---|
| HyperCode-V2.4 | Core backend — ~30 containers (profile-dependent; 20 compose files) | `H:\HyperStation zone\HyperCode\HyperCode-V2.4` |
| Hyper-Vibe-Coding-Course | Course + HyperLabs funnel — Supabase + Vercel + Web3 | `H:\Hyper-Vibe-Coding-Course` |
| HyperAgent-SDK | npm agent framework (`@w3lshdog/hyper-agent`) | `H:\HyperAgent-SDK` |
| BROskiPets-LLM-dNFT | Web3 NFT pet game — dNFTs + LLM | `H:\dNFTpet\BROskiPets-LLM-dNFT` |
| BROski-Obsidian-Brain | Second Brain — PARA vault + GitHub bridge | `H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne` |

---

## 3. 🏗️ Architecture Quick Ref (V2.4)

```
Networks:
  app-net     → core services (internal)
  data-net    → redis, postgres, chroma, minio (internal)
  obs-net     → prometheus, grafana, loki, tempo (internal)
  agent-net   → all agents
  agents-net  → broski-bot + hyper-agents

Key ports:
  8000  hypercode-core API       8081  crew-orchestrator
  8088  hypercode-dashboard      8095  hyperhealth-api
  8098  broski-pets-bridge       8099  nemoclaw-agent
  9090  prometheus               3001  grafana
  3100  loki                     3200  tempo
  6379  redis                    5432  postgres
```

---

## 4. 🔒 Sacred Rules (NEVER debate, NEVER break)

### 4a. Ecosystem-wide / V2.4

```
✔ docker-ce-cli          — NEVER docker.io for socket agents
✔ from app.X import Y    — NEVER from backend.app.X
✔ FastAPI public routes   — BEFORE auth-gated routes
✔ Stripe webhook          — rate-limit EXEMPT, always (NEVER add rate limiting)
✔ data-net + obs-net      — internal: true, never external
✔ .env files              — NEVER committed to git
✔ Commits                 — feat: fix: docs: chore: only
✔ Trivy target            — 0 CRITICAL per image
✔ Import style            — absolute imports, sys.path.insert at top
✔ Python indent           — 4 spaces, NEVER 3, NEVER mixed
✔ Redis DB split          — DB 1 = cache, DB 2 = rate limits. NEVER mix.
✔ hypercore healthcheck   — use localhost NOT 127.0.0.1 (IPv6 fix)
✔ Supabase ↔ V2.4         — NEVER merge schemas
✔ Guardian moderation     — ban/kick NEVER fully autonomous (P3c = veto-gated only)
✔ NemoClaw/Guardian       — bot detects, Core decides + persists, bot renders (One Door)
✔ Prometheus config       — monitoring/prometheus/prometheus.yml = ACTIVE. Root = STALE
✔ minio                   — on both data-net AND obs-net — correct, intentional
✔ Alembic                 — up to 015. If missing: alembic stamp <prev> → upgrade head
✔ Socket-proxy split      — main=read-only, healer proxy=write (CONTAINERS+POST+PING)
✔ Security headers        — frontend/vercel.json (NOT repo root)
```

### 4b. Course / HyperLabs (`Hyper-Vibe-Coding-Course`) — load-bearing gotchas

```
✔ NEVER `supabase db push`  — local migration filenames desynced from remote
                              schema_migrations. Deploy via Supabase MCP apply_migration
✔ Web3 lazy + /pets ONLY    — NEVER import wagmi/rainbowkit globally / in funnel /
                              in main.tsx. Re-bloats cold load ~900 kB (reverts Sprint 2).
                              Only 4 files use wagmi — keep it that way.
✔ NEVER `--no-verify`       — husky + lint-staged catches real ESLint errors.
                              react-hooks/set-state-in-effect is an ERROR (derive or useRef)
✔ NO orange in UI           — sacred HFZ brand rule (master palette only)
✔ Three chrome systems      — funnel TopNav · course Navbar · VibeLabShell.
                              No global shell. Funnel pages skip Layout.
✔ award_tokens()            — ALWAYS pass a stable p_source_id (ledger dedup)
✔ Pets.tsx @ts-nocheck      — pre-existing, non-blocking, money-path. Don't chase it.
✔ Course dev (repo root)    — npm run dev:frontend  NOT npm run dev
✔ NEVER curl-poll prod      — trips Vercel Attack Challenge Mode (403). Deploy-truth =
                              Vercel MCP get_deployment
✔ Playwright IS installed   — npm run test:e2e. Use it instead of "human must test"
✔ Parallel git workflow     — ALWAYS git fetch + check origin/main before pushing.
                              NEVER force-push.
```

### 4c. Genuinely human-only

- MetaMask / wallet popups (browser-extension UI — cannot be automated)
- Real Core Web Vitals (needs Vercel Speed Insights dashboard)
- Visual QA on physical devices

---

## 5. 🤖 ONE TRUE BOT — broski-bot

**Location:** `agents/broski-bot/` — profile: `discord`
⚠️ `discord-bot/` = LEGACY (reprofiled to `discord-lite`) — do NOT use
⚠️ `agents/broski-bot/main.py` is ORPHANED — entrypoint is `python -u -m cogs.bot`

```bash
docker compose --profile discord up -d            # Bot + core
docker compose --profile discord up -d broski-bot # Bot only
docker compose --profile discord config           # Verify config
```

| Cog | Commands / Behaviour |
|---|---|
| `economy` | `/balance` `/daily` `/give` `/rich` |
| `leaderboard` | `/top` `/rank` |
| `ai` | `/ask` (→ Core orchestrator) |
| `focus` | `/focus start\|stop` `/focusstats` (→ NemoClaw delta → BROski$) |
| `missions` | `/missions` `/missions-claim` (focus-verified) |
| `health_check` | `/health` (NemoClaw grade scan) |
| `health_history` | `/health-history` (7-scan trend) |
| `codehealth_voice` | `/health-pulse` (admin) + 24h auto-post on grade move |
| `server_builder` | `/hyperfocus_setup` (admin, idempotent layout build) |
| `digest` | `/digest` (admin) + weekly auto-DM to Lyndz |
| `moderation` | passive auto-mod (spam/blocklist → timeout, reversible) |
| `welcome` | passive on-join welcome + auto-role |

**One Door actions:** `POST /api/v1/discord/actions`
`economy.* daily.claim leaderboard.xp member.join ai.ask ai.chat`
`focus.start focus.stop focus.stats missions.today missions.claim`
`codehealth.pulse digest.weekly mod.assess`

**NemoClaw** (port 8099): L1 Heartbeat · L2 Memory · L3 Voice · L3.5 Focus→BROski$ loop
**Guardian:** P1 auto-role · P2 weekly digest · P3a auto-mod · P3b raid-lock · P3c veto-ban (smoke pending)

```powershell
.\scripts\launch-bot.ps1                            # preflight → up
docker compose --profile nemoclaw up -d nemoclaw-agent
```

---

## 6. 📦 Key Files Quick Reference

```
ROOT (H:\HYPERFOCUSZONE\HperCore)
  CLAUDE.md                     — THIS FILE (ecosystem constitution)
  WHATS_DONE.md                 — NEVER suggest anything listed here
  docs/STATUS.md                — live system health (updated each session)
  docs/NEXT_TASKS.md            — active task list
  docs/TECH_DEBT.md             — known issues
  docs/ROADMAP.md               — full phase history
  docs/ACHIEVEMENTS.md          — all-time wins

HyperCode-V2.4/
  docker-compose.yml            — main stack
  docker-compose.secrets.yml    — secrets injection (always alongside main)
  backend/app/main.py           — FastAPI core app
  agents/broski-bot/cogs/bot.py — ONE TRUE BOT entrypoint
  agents/nemoclaw-agent/        — code-health sidecar (port 8099)
  backend/app/api/v1/endpoints/discord_actions.py — One Door brain
  scripts/env_check.py          — env preflight checker
  monitoring/prometheus/        — ACTIVE Prometheus config

Hyper-Vibe-Coding-Course/
  CLAUDE.md                     — Course constitution (read for course work)
  frontend/src/App.tsx          — all routes
  supabase/migrations/          — latest: 20260518000035_claim_level_reward.sql
  rewrites/                     — session snapshots + handovers

BROski-Obsidian-Brain.../
  cluster.json + .agents/       — BROski Brain 4-agent cluster (3 LIVE: :3301/:3302/:3303 — profile brain-agents)
```

---

## 7. 🧪 Essential Commands

```powershell
# Env preflight — ALWAYS before docker compose up:
python scripts/env_check.py --core --secrets --profile discord

# Start full stack:
docker compose -f docker-compose.yml -f docker-compose.secrets.yml -f docker-compose.brain.yml --profile discord up -d
# Core only:
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d

pytest backend/tests/ -q                          # run tests
curl http://localhost:8000/health                 # core
curl http://localhost:8098/health                 # broski-pets-bridge
curl http://localhost:8099/health                 # nemoclaw-agent
docker compose exec hypercode-core alembic upgrade head   # migrations
docker compose ps
curl -X POST localhost:9090/-/reload              # Prometheus hot-reload

# Course / HyperLabs:
cd H:\Hyper-Vibe-Coding-Course && npm run dev:frontend    # NOT npm run dev
npx tsc --noEmit && npx eslint . && npm run build         # pre-commit loop
npm run test:e2e                                           # Playwright

# Brain agents (profile: brain-agents — 3 live, morning-briefing gated by profile brain-briefing):
docker compose --profile brain-agents up -d
curl http://localhost:3301/health                 # agent-hyper-brain-core
curl http://localhost:3302/health                 # agent-mcp-bridge
curl http://localhost:3303/health                 # agent-focus-tracker

# Brain vault sync:
python scripts/github_to_obsidian.py
```

---

## 8. 👋 Quick-Start — Any New AI Session

1. Read this file — sacred rules + ecosystem map
2. Read `docs/STATUS.md` — live system state
3. Read `docs/NEXT_TASKS.md` — what to build
4. Check `WHATS_DONE.md` — NEVER re-suggest anything listed there
5. Working in a repo? read that repo's `CLAUDE.md` + latest handover
6. Env check first (V2.4) · never `db push` · never global wagmi · never `--no-verify`
7. ONE TRUE BOT = `agents/broski-bot/` (profile:discord) — NOT `discord-bot/`
8. Use Playwright instead of "human must test"
9. Short sentences. BROski energy. Celebrate wins. Surface contradictions.
10. Call them **"Bro"** 🤙

---

<div align="center">

**Built for ADHD brains. Fast feedback. Real tools. No fluff.** 🧠⚡

*by @welshDog — Lyndz Williams, Llanelli, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁥*

**A BROski is ride or die. We build this together. 🐶♾️🔥**

</div>
