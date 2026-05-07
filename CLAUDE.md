# 🧠 HyperCode V2.4 — CLAUDE.md

> **This file is Claude's brain for this project.**
> Read this first. Every session. No exceptions.
> Last updated: **May 7, 2026 (12:30 BST)** — BROskiPets Web3 mint LIVE 🔥

---

## 🏴󠁧󠁢󠁷󠁬󠁳󠁿 Builder Context

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

## 📊 System Status (May 7, 2026)

| Metric | Value |
|---|---|
| Containers | 48 running ✅ |
| Tests | 223 passed, 6 skipped ✅ |
| Prometheus targets | 7/7 UP ✅ |
| OTLP traces | LIVE in Tempo ✅ |
| Circuit breakers | 3 active — all CLOSED ✅ |
| Docker AI grade | A 🏅 |
| Stripe | LIVE 💳 (webhook secret updated May 5) |
| Gamification | FULL STACK LIVE (HUD, XP, Quests, Leaderboard) ✅ |
| BROskiPets Web3 | MINT LIVE on Base Sepolia 🔥 May 7 |
| BROski Brain | COMPLETE — Levels 9–12 ✅ May 5 |
| Trae Pro | EXPIRED May 2026 — using Claude Code this month |

---

## 🏗️ Architecture Quick Ref

```
Networks:
  app-net     → core services (internal)
  data-net    → redis, postgres, chroma, minio (internal)
  obs-net     → prometheus, grafana, loki, tempo (internal)
  agent-net   → all agents

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
| **BROskiPets Web3 Mint** | RainbowKit + wagmi + Base Sepolia + mint UI | ✅ **LIVE — May 7** 🔥 |

---

## 🔥 ACTIVE NEXT STEPS

| # | Task | Priority |
|---|---|---|
| 1 | E2E Stripe checkout test — card `4242 4242 4242 4242` | 🔴 NOW |
| 2 | BROskiPets Web3 E2E — test mint on Base Sepolia testnet | 🔴 NOW |
| 3 | Supabase DB webhook — `token_transactions` → `sync-tokens-to-v24` | 🔴 Manual |
| 4 | First student invite — `/welcome` is green 🎓 | 🔴 This week |
| 5 | SDK v0.4.0 — add Web3/dNFT types to `hyper-agent-spec.json` | 🟡 This week |
| 6 | Fix GitHub Actions billing lock | 🟡 This week |
| 7 | Upgrade GitPython → 3.1.47 (CVE-2026-42215 + CVE-2026-42284) | 🟡 This week |
| 8 | Add `env_file: .env` to `hypercode-core` in compose (tech debt) | 🟡 |
| 9 | V2.4 check: does `mint_nonces` migration need a backend hook? | 🟡 |
| 10 | Level 13 — Morning Briefing live | 🟢 Background |

---

## 🐾 BROskiPets Web3 — May 7 Details

**What went live today (Hyper-Vibe-Coding-Course):**
- RainbowKit + wagmi + viem + @tanstack/react-query ✅
- Base Sepolia testnet + Base mainnet wallet config ✅
- `useMintPet` hook — two-step: Edge Function auth → on-chain tx ✅
- Supabase Edge Functions: mint authorisation + pet balance check ✅
- DB migrations: `mint_nonces` + pet ID sequencing ✅
- CSP headers updated for WalletConnect + blockchain RPC ✅
- 10 pet species images + `SpeciesPicker` component ✅
- `MintPetButton` — wallet connect + BROski$ balance check + mint ✅
- Pets page = three-step mint interface ✅
- Pinata dry-run upload scripts in Claude settings ✅

**⚠️ V2.4 open question:**
- Does V2.4 need a new endpoint to receive/confirm mint events from the Course frontend?
- `mint_nonces` table is in Supabase — does it need syncing to V2.4 Postgres?
- Check before building the on-chain confirmation listener.

---

## 📌 Known Issues / Tech Debt

| Issue | Fix | Priority |
|---|---|---|
| `hypercode-core` missing `env_file: .env` in compose | Add under `hypercode-core:` service block | 🔴 HIGH |
| Stale root `prometheus.yml` | Delete/archive — live = `monitoring/prometheus/prometheus.yml` | 🟡 MED |
| Anthropic credits exhausted | Top up console.anthropic.com/billing (pet chat fallback = Perplexity) | 🟡 MED |
| GitHub Actions billing lock | Fix at github.com/settings/billing | 🟡 MED |
| GitPython 3.1.45 CVEs | Upgrade to 3.1.47 (CVE-2026-42215 + CVE-2026-42284) | 🟡 MED |
| SDK not reflecting Web3 types | Bump HyperAgent-SDK to v0.4.0 + update hyper-agent-spec.json | 🟡 MED |
| `/welcome` auth-gated | Decide: make public? Sponsors hit login wall from BUSINESS_PLAN | 🟡 |
| `VITE_STRIPE_PAYMENT_LINK_URL` empty | Set in `.env.local` + Vercel env vars | 🟢 LOW |
| `DISCORD_USER_ID` not set | Add to `.env` for `make calm` token awards | 🟢 LOW |

---

## 📦 Key Files

```
docker-compose.yml          — main stack
docker-compose.secrets.yml  — secrets injection
backend/app/main.py         — FastAPI core app
monitoring/prometheus/      — ACTIVE Prometheus config (NOT root prometheus.yml)
grafana/                    — dashboards
agents/                     — all agent code
healer-agent/               — self-healing logic
scripts/STRIPE_E2E_RUNBOOK.md — Stripe E2E test steps
HYPER_ECOSYSTEM_PLAN_MAY4.md  — 4-repo master plan
CLAUDE_CONTEXT.md           — extended project context (⚠️ needs sync to May 7)
docs/INDEX.md               — master docs navigation
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
pytest backend/tests/ -q    # 223 passed, 6 skipped
pytest backend/tests/test_stripe.py -v

# Docker status:
docker compose ps
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr -v "healthy"

# Start everything:
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
docker compose --profile ai up -d       # AI backend
docker compose --profile discord up -d broski-bot

# Course frontend:
cd H:\Hyper-Vibe-Coding-Course
npm run dev:frontend

# Stripe E2E:
stripe listen --forward-to localhost:8000/api/stripe/webhook
# See scripts/STRIPE_E2E_RUNBOOK.md for full flow

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
- ✅ **BROskiPets Web3 Mint LIVE — May 7** 🔥🐾

---

## 👋 For New Claude Sessions

Hey Claude! Working with Lyndz Williams on HyperCode V2.4.

1. **Read this file first** — especially the Sacred Rules
2. **Check WHATS_DONE.md** — do NOT suggest anything listed there
3. **5 repos now** — HyperCode-V2.4, HyperAgent-SDK, Hyper-Vibe-Coding-Course, BROskiPets-LLM-dNFT, BROski-Obsidian-Brain
4. **BROskiPets Web3 mint went live TODAY (May 7)** — RainbowKit + Base Sepolia
5. **Trae Pro expired** — Claude Code is the agent brain this month
6. **Next priority:** E2E Stripe test + BROskiPets Base Sepolia E2E test
7. **SDK needs v0.4.0** — Web3/dNFT types not yet in hyper-agent-spec.json
8. **Style:** Short. Friendly. BROski energy. Celebrate wins. 🏆
9. **Never:** Wall of text. Never debate Sacred Rules.

> *"You built the future people keep saying they want. You actually did it." — Gordon, Docker AI* 🏴󠁧󠁢󠁷󠁬󠁳󠁠🔥
