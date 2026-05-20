# 🧠 HYPERFOCUS z0ne — MASTER CLAUDE.md
> **For ANY AI — Claude, Perplexity, GPT, Gemini, Cursor. Read this first. Every session.**
> Last updated: May 19, 2026 · Built by @welshDog + AI
> **This is the constitution. SESSION_SNAPSHOT is the living state.**

---

## 0. Read Order — Every Session, No Exceptions

1. **This file** — identity, rules, ecosystem map, philosophy
2. **Repo `CLAUDE.md`** — repo-specific sacred rules + key files
3. **`SESSION_SNAPSHOT_[latest date].md`** — current sprint state, what's live, what's next
4. **If touching DB** → check migrations first (`supabase/migrations/` or `alembic upgrade head`)
5. **Then build.** Not before.

> If this file and a SESSION_SNAPSHOT contradict — surface it. Correct the doc. Don't silently pick one.

---

## 1. Who You're Working With

- **Name:** Lyndz Williams — call them **"Bro"** or **"BROski"**
- **GitHub:** @welshDog · **npm:** @w3lshdog
- **Location:** Llanelli, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁧
- **Brain:** ADHD + Dyslexia + Autistic — hyperfocus is a SUPERPOWER ⚡
- **IDE:** Claude Code (terminal) + Perplexity AI — Trae Pro expired May 2026
- **OS:** Windows primary (PowerShell) · WSL2 · Raspberry Pi · Docker
- **Building:** The world's first neurodivergent-first autonomous AI infrastructure platform

> *"You built the future people keep saying they want. You actually did it."* — Gordon (Docker AI, April 15 2026)

### Communication Rules — Non-Negotiable

| ✅ DO | ❌ NEVER |
|---|---|
| Short sentences first → detail after if asked | Walls of text unprompted |
| Bullet points + bold for key info | Waffle or filler |
| Why → How → Ready-to-use example | Assume tasks are done without a commit |
| Celebrate every milestone ("Nice one BROski♾️!") | Debate sacred rules |
| Check in gently if Lyndz goes quiet | Say "human must test" when Playwright applies |
| Surface contradictions — correct the doc visibly | Quietly pick one side of a contradiction |
| Chunk it, quick wins first, no overwhelm | Suggest anything listed in WHATS_DONE.md |

---

## 2. 🌐 The 5-Repo Ecosystem

> ⚠️ **All repos share the same on-disk base: `H:\HYPERFOCUSZONE\HperCore\`** (verified May 19 2026 via `ls`)
> ⚠️ Course path is `H:\HYPERFOCUSZONE\HperCore\Hyper-Vibe-Coding-Course` — NOT `H:\the hyper vibe coding hub` (archived typo repo)

| Repo | Purpose | Local Path |
|---|---|---|
| `HyperCode-V2.4` | Core backend — ~30 Docker containers running (profile-dependent; 20 compose files), FastAPI, agents | `H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4` |
| `Hyper-Vibe-Coding-Course` | Course platform — Supabase + Vercel + Web3 | `H:\HYPERFOCUSZONE\HperCore\Hyper-Vibe-Coding-Course` |
| `HyperAgent-SDK` | npm agent framework (`@w3lshdog/hyper-agent`) | `H:\HYPERFOCUSZONE\HperCore\HyperAgent-SDK` |
| `BROskiPets-LLM-dNFT` | Web3 NFT pet game — dNFTs + LLM + port 8098 | `H:\HYPERFOCUSZONE\HperCore\BROskiPets-LLM-dNFT` |
| `BROski-Obsidian-Brain` | Second Brain — PARA vault + GitHub bridge | `H:\HYPERFOCUSZONE\HperCore\BROski-Obsidian-Brain-for-HyperFocus-z0ne` |

### How the repos connect

```
Hyper-Vibe-Coding-Course  ──── manifest.json (hyper-agent-spec) ────▶  HyperCode-V2.4
        │                                                                      │
        └─────────────────── HyperAgent-SDK ──────────────────────────────────┘
                              @w3lshdog/hyper-agent · graduate build DESIGNED May 15
                                       │
                          BROskiPets-LLM-dNFT (port 8098)
                                       │
                      BROski-Obsidian-Brain (cluster.json + 4 agent manifests)
```

---

## 3. 🔴 Sacred Rules — HyperCode V2.4

> Break these = OOM crashes, security holes, or infra cascade failures.

| # | Rule | Why | Consequence if broken |
|---|---|---|---|
| 1 | **`docker-ce-cli` NEVER `docker.io`** for socket agents | Socket agent auth depends on it | Agent connectivity breaks |
| 2 | **`from app.X import Y` NEVER `from backend.app.X`** | Absolute import path is `app.*` | Import errors across all agents |
| 3 | **FastAPI public routes BEFORE auth-gated routes** | Route ordering matters in FastAPI | Auth-gated routes shadow public ones |
| 4 | **Stripe webhook ALWAYS rate-limit exempt** | Stripe retries have strict timing | Webhook drops, payments fail |
| 5 | **`data-net` + `obs-net` = `internal: true` always** | Security boundary — never expose to internet | Data layer exposed publicly |
| 6 | **`.env` files NEVER committed to git** | Secrets via Docker `.txt` files only | Credential leak |
| 7 | **Commits: `feat:` `fix:` `docs:` `chore:` only** | Conventional commits, enforced by hooks | CI breaks, changelog corrupted |
| 8 | **Trivy target: 0 CRITICAL per image** | Security gate | Vulnerable images ship to prod |
| 9 | **Python indent: 4 spaces, NEVER 3, NEVER mixed** | Enforced by linter | Silent IndentationError crashes |
| 10 | **Redis: DB 1 = cache, DB 2 = rate limits — NEVER mix** | Rate limiter reads wrong DB | Rate limits silently disabled |
| 11 | **`hypercore` healthcheck uses `localhost` NOT `127.0.0.1`** | IPv6 resolution bug in container | Health check fails, container restarts loop |
| 12 | **Supabase ↔ V2.4 schemas NEVER merged** | Two separate DB concerns | Schema drift, migration conflicts |
| 13 | **Guardian moderation: ban/kick NEVER fully autonomous** | Phase 3c = veto-gated only — Lyndz must approve | Innocent user banned without review |
| 14 | **NemoClaw/Guardian: bot detects, Core decides + persists, bot renders (One Door)** | Single source of truth for all actions | Duplicate actions, split state |
| 15 | **`monitoring/prometheus/prometheus.yml` = ACTIVE. Repo root = STALE** | Two files exist — only one is live | Prometheus scrapes wrong targets |
| 16 | **`minio` on BOTH `data-net` AND `obs-net` — intentional, never "fix" it** | Minio serves both data and observability layers | Breaks minio connectivity to obs stack |
| 17 | **Alembic: if `alembic_version` missing → `stamp <prev>` then `upgrade head`** | `create_all` built schema without Alembic state | Migration state corrupts, double-apply |
| 18 | **Two socket proxies — NEVER merge** | Main = read-only · `healer` = CONTAINERS/POST/PING only | LLM code gains write access to containers |
| 19 | **Memory limits on ALL services** | Agent X caused OOM crash Apr 17 building 30 images uncapped | OOM cascade kills entire stack |
| 20 | **`make build` runs `pre-build-check.sh` first** | Aborts if <15GB free disk | OOM during build |

---

## 4. 🔴 Sacred Rules — Hyper-Vibe-Coding-Course

> Break these = deploys revert, money-path logic corrupts, or perf wins get lost.

| # | Rule | Why | Consequence if broken |
|---|---|---|---|
| 1 | **NEVER `supabase db push`** | Local migration filenames desynced from remote `schema_migrations` | Replays shop/pet migrations DB already has |
| 2 | **NEVER import `wagmi`/`rainbowkit` outside `/pets`** | Re-bloats cold funnel load by ~900 kB | Reverts Sprint 2 perf win (61 kB → 1,270 kB) |
| 3 | **NEVER `--no-verify` on commits** | Husky + lint-staged catches real ESLint errors | Broken code enters `main` |
| 4 | **NO orange anywhere in UI** | Sacred HFZ brand rule | Off-brand, gets reverted |
| 5 | **Three chrome systems — no global shell** | Funnel `TopNav` · course `Navbar` · `VibeLabShell` are separate | Layout breaks across routes |
| 6 | **`award_tokens()` always needs stable `p_source_id`** | Ledger dedup = partial unique index on `(user_id, reason, source_id) WHERE source_id IS NOT NULL` | Duplicate token grants |
| 7 | **Don't chase `Pets.tsx` `@ts-nocheck`** | Pre-existing, non-blocking, money-path file | Wasted time, no gain |
| 8 | **`setState` synchronously in `useEffect` = ERROR** | Enforced by ESLint `react-hooks/set-state-in-effect` | Commit blocked by husky |
| 9 | **Lab pages = `hfz-*` Tailwind tokens. Landing page = inline styles + CSS vars** | Two different idioms by design | Wrong token overrides, visual breakage |
| 10 | **No `framer-motion` in this repo** | Not installed — CSS-only motion, reduced-motion gated | Broken build |
| 11 | **Course dev from repo root = `npm run dev:frontend` NOT `npm run dev`** | Wrong script from root = wrong server. Note: inside `frontend/` the package's own `dev` script IS vite — that's what `playwright.config.ts` launches and is correct. Do NOT "fix" the playwright config. | Dev server broken from root; false "fix" breaks test config |

---

## 5. 🔴 Sacred Rules — BROski$ Shop

> Break these = wrong prices charged, duplicate grants, or fulfillment silently breaks.

| # | Rule | Why | Consequence if broken |
|---|---|---|---|
| 1 | **`TIER_DISCOUNT_PCT` lives in TWO places — keep both in sync** | `ShopPage.tsx` (UI preview) + `supabase/functions/shop-purchase/index.ts` (server truth) | UI shows wrong price vs what server charges |
| 2 | **Server is ALWAYS the discount source of truth** | Client discount is preview-only — server re-derives from real tier | Tampered client tier gets unearned discount |
| 3 | **`metadata.image_url` is inside JSONB `metadata` — NOT a top-level column** | Schema design: `item.metadata?.image_url` | Direct column access → `undefined`, image gone |
| 4 | **`metadata.consumable = true` = re-buyable, never locks to "Owned"** | Consumables use count-based ownership | Blocks re-purchase, breaks economy |
| 5 | **`shop-purchase` Edge Function: `verify_jwt: ON` always** | All spend is authenticated | Unauthenticated users drain real token balances |
| 6 | **Auto-refund is server-side via `award_tokens`** — never add a client-side refund path | Server refunds if purchase row fails after spend | Client refund = double-grant + balance corruption |
| 7 | **Agent access polls `provision_status` every 6s, max 10 attempts** — don't change cadence without updating both poll logic and V2.4 provisioner | Race between frontend poll and async V2.4 provisioning | Too fast = hammers DB; too slow = looks broken |
| 8 | **`price_gbp` is nullable** — always use `price_gbp != null` before rendering | Some items are token-only | Renders `£undefined` or crashes `toFixed()` |

---

## 6. 🏗️ Architecture Quick Ref — V2.4

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

## 7. 🤖 ONE TRUE BOT — broski-bot

**Location:** `agents/broski-bot/` — profile: `discord`
> ⚠️ `discord-bot/` = LEGACY (reprofiled to `discord-lite`) — do NOT use
> ⚠️ `agents/broski-bot/main.py` is ORPHANED — entrypoint is `python -u -m cogs.bot`

### Active cogs (loaded by `cogs/bot.py`)

| Cog | Commands |
|---|---|
| `economy` | `/balance` `/daily` `/give` `/rich` |
| `leaderboard` | `/top` `/rank` |
| `ai` | `/ask` (→ Core orchestrator) |
| `focus` | `/focus start\|stop` `/focusstats` (→ NemoClaw delta → BROski$) |
| `missions` | `/missions` `/missions-claim` (focus-verified) |
| `health_check` | `/health` (NemoClaw grade scan) |
| `digest` | `/digest` (admin) + weekly auto-DM |
| `moderation` | passive auto-mod (spam → reversible timeout, audited) |
| `welcome` | passive on-join welcome + auto-role |

### Run commands
```bash
docker compose --profile discord up -d            # bot + core
docker compose --profile discord up -d broski-bot # bot only
.\scripts\launch-bot.ps1                          # preflight → up (recommended)
```

### Guardian phases
- **P1** auto-role on join + `/hyperfocus_setup` ✅ LIVE
- **P2** weekly digest DM ✅ LIVE
- **P3a** spam → reversible timeout, `mod_actions` audit ✅ LIVE
- **P3b** raid auto-lockdown → reversible channel lock ✅ LIVE
- **P3c** 3-strike → veto buttons → ban ONLY on explicit APPROVE click ✅ BUILT (smoke pending)

---

## 8. 🎯 Mission + Teaching Philosophy

> **"Stop apologising for your brain. Start building."**

- For ADHD, dyslexic, autistic, and neurodivergent builders
- No previous experience needed
- **Build first, learn second. Speed of thought. Dopamine momentum.**

### Every Module/Lab — 7-Beat Structure

1. **STOP** — plain English context BEFORE any tech
2. **WHY** — real-world use case (Netflix, Uber, Stripe refs)
3. **HOW** — step-by-step with ⏱️ time estimates
4. **WIN** — clear celebratable moment
5. **NEXT** — warm bridge to next module
6. **HELP** — troubleshooting that normalises problems
7. **REWARD** — BROski$ XP claim

### Analogy Arsenal

| Concept | Analogy |
|---|---|
| Docker stack | Your AI Brain 🧠 |
| `docker-compose up` | Flip the switch on your house 🏠 |
| Stripe webhook | Tap on the shoulder 👆 |
| Dynamic NFT | Live passport 🛂 |
| Smart contract | Database nobody can delete 🔒 |
| Grafana | CCTV for your server 📹 |
| Alertmanager | Alarm that calls you 🚨 |
| Prompt injection | Con artist at the door 🥸 |
| Agent swarm | Your crew of specialists 👥 |
| Session snapshot | Your brain's save file 💾 |
| NemoClaw | The doctor who reads your code's pulse 🩺 |
| Guardian | The bouncer who never sleeps 🛡️ |
| Claude | The crane — you're the architect |

---

## 9. AI Behaviour Rules

### Tools to use — don't improvise

| Task | Correct tool |
|---|---|
| DB changes (course) | Supabase MCP `apply_migration` — NEVER `db push` |
| DB queries / safe prod testing | Supabase MCP `execute_sql` — wrap in `BEGIN / ROLLBACK` |
| V2.4 DB changes | `docker compose exec hypercode-core alembic upgrade head` |
| Auth + browser testing | **Playwright** — installed (`npm run test:e2e`), badges have `data-auth-status` |
| Deploy verification (course) | **Vercel MCP `get_deployment`/`list_deployments`** (team `team_Uy6hGYD4AZqclHqUeEsmZuDP`). ⚠️ NEVER curl-poll prod — trips Vercel Attack Challenge Mode (403 `X-Vercel-Mitigated`); looks down, isn't |
| Perf claims | `npm run build` chunk sizes = real evidence. Never assert CWV without Vercel dashboard |
| Before claiming done (course) | `npx tsc --noEmit` + `npx eslint` + `npm run build` — all three green |
| Before `docker compose up` | `python scripts/env_check.py --core --secrets --profile discord` |

### Human-only gates — be honest, don't pretend otherwise

- MetaMask / wallet popups (browser extension)
- Real Core Web Vitals (needs Vercel Speed Insights dashboard)
- Visual QA on physical devices
- Discord server manual smoke tests (P3c veto-ban)

### General behaviour

- **NEVER suggest anything in `WHATS_DONE.md`** — check it before every suggestion
- Surface contradictions — correct the doc, don't silently proceed
- **Lyndz runs a PARALLEL git workflow** — tooling auto-commits/pushes out-of-band. ALWAYS `git fetch` + check `origin/main` before pushing; NEVER force-push; align a duplicate commit with `git reset --hard origin/main`
- Quick wins first — momentum > perfection
- Nothing is done until committed and pushed
- Update SESSION_SNAPSHOT at end of every session

---

## 10. 🏆 Achievements Unlocked

- ✅ Gordon Docker AI: **Grade A** — *"world-class infrastructure"*
- ✅ ~30 containers running, self-healing closed loop (profile-dependent across 20 compose files)
- ✅ Full Gamification Stack — HUD, XP, Quests, Leaderboard, Rifts
- ✅ BROski Brain v2.2 — Levels 9–12 unlocked
- ✅ MCP-GitHub LIVE — 26 tools via Docker MCP gateway
- ✅ Stripe LIVE + E2E proven · Course → Stripe → enrolled: full money path
- ✅ BUSINESS_PLAN.md v1.1 — sponsor-ready
- ✅ BROskiPets Web3 Mint LIVE — May 7 🔥🐾
- ✅ HyperAgent Graduate Build DESIGNED — May 15 📐
- ✅ Brain Agent Cluster PUSHED — May 15 🧠
- ✅ BROski Discord Bot Tier 1 LIVE — May 15 🤖
- ✅ Env Preflight Checker LIVE — May 15 🛡️
- ✅ NemoClaw "Alive" L1–L3.5 LIVE — May 15–16 🧠
- ✅ Focus → code-delta → BROski$ loop PROVEN end-to-end — May 15 🏆
- ✅ Server Guardian P1–P3b LIVE · P3c built — May 16 🛡️
- ✅ BROski$ Shop Fulfillment v2 BUILT — May 17 🛒
- ✅ CLAUDE.md constitution merged + AI-optimised — May 19 📜
- ✅ CLAUDE.md §2 paths corrected + Rule #11 clarified — May 19 🗺️

---

## 11. Session End Checklist

- [ ] All code: lint + type-check + build green
- [ ] All changes pushed to GitHub — nothing is done until committed
- [ ] New `SESSION_SNAPSHOT_[DATE].md` created + pushed
- [ ] `NEXT_SESSION_HANDOVER_[DATE].md` written — open gates + first task
- [ ] Tell Lyndz the first task for next session (one sentence)
- [ ] Celebrate the wins 🎉

---

> 🐶♾️ Built by @welshDog · Llanelli, Wales
> *"Stop apologising for your brain. Start building."*
> Hyperfocus z0ne — Keep it weird, keep it Welsh. ♾️
