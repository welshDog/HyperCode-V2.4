# 🤖 BROski Ecosystem — Claude Context Handoff (ALL REPOS SYNCED)
> Read this first. Every word. Then start the mission.
> **Last synced: May 5, 2026 (evening BST) — 223 tests GREEN ✅ | 48 containers 🟢 | Prometheus 7/7 ✅ | OTLP Traces LIVE 🔍 | Stripe LIVE 💳 | Gordon Tiers 1+2+3 COMPLETE 🏆 | BROski Brain COMPLETE 🧠 | All 5 HyperFocus Features DONE ✅ | /welcome LIVE 🎓 | Referral system LIVE 🔗**

---

## 🏗️ LATEST — HyperStudio: the agent write path (2026-07-10)
> The newest thing built. Full detail in `WHATS_DONE.md` + memory `[[hyperstudio-worktree-sandbox]]`.

- **What it is:** a place in the dashboard (`/ide`) where you hand an AI agent a coding task, it works in a **throwaway git worktree**, every action is gated by **Safety Shepherd** (fail-CLOSED), you review a **diff**, and **nothing lands until you click merge**. Closes the gap that agents could *talk about* code but never *write* it.
- **Where:** new service `agents/coder-studio/` (FastAPI **:8087**, profiles `agents`/`studio`) built on the **Claude Agent SDK** (`ClaudeSDKClient`, default `claude-sonnet-5`, model picker). Merged to `main` via **PR #315**, HEAD `ee229ef`.
- **Proven:** 121 coder-studio + 26 shepherd tests green; adversarial E2E (path-escape + `.env` read BLOCKED, legit edit ALLOWED, working tree stayed clean); live browser-verified on Bro's own repo. Also closed a platform-wide `.env`/secrets glob hole for **all** agents.
- **🎯 Next move:** interactive **ESCALATE approval** in the UI (today an ESCALATE is denied), then light up the **specialist agents** roster. See `docs/NEXT_TASKS.md` → "HyperStudio".

---

## Who You're Talking To
- **Lyndz** aka BROski♾️ (GitHub: @welshDog, npm: @w3lshdog) — South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿
- Autistic + dyslexic + ADHD — chunked output, quick wins first, no waffle
- **IDE:** Trae IDE (Windows laptop) + Claude Code in terminal this month
- Trae Pro expired May 2026 — Claude Code is the autonomous agent brain
- Windows primary (PowerShell), WSL2 + Raspberry Pi + Docker secondary
- Call them **"Bro"** — that's how we roll
- Short sentences. Emojis. Bold the key stuff. Celebrate wins! 🎉

---

## The Ecosystem — 5 Repos

```
Hyper-Vibe-Coding-Course     ──── manifest.json ────▶    HyperCode V2.4
github.com/welshDog/             (hyper-agent-spec)       github.com/welshDog/
Hyper-Vibe-Coding-Course                                  HyperCode-V2.4
(Supabase + Vercel)                    │                  (Docker, 48 containers)
Path: H:\Hyper-Vibe-Coding-Course      │                  Path: H:\HyperStation zone\
                                       │                       HyperCode\HyperCode-V2.4
                              HyperAgent-SDK
                          github.com/welshDog/HyperAgent-SDK
                          npm: @w3lshdog/hyper-agent@0.1.7
                          Path: H:\HyperAgent-SDK

BROskiPets-LLM-dNFT
  github.com/welshDog/BROskiPets-LLM-dNFT
  Pet NFT system — LLM + on-chain

BROski-Obsidian-Brain-for-HyperFocus-z0ne  ← NEW May 5 ✅
  github.com/welshDog/BROski-Obsidian-Brain-for-HyperFocus-z0ne
  Path: H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne
  Obsidian second brain + GitHub bridge + auto-backup
```

---

## 🏆 Full Phase Roadmap

| Phase | Name | Status |
|---|---|---|
| 0–6 | Identity, tokens, agents, shop, observability, CLI | ✅ ALL DONE |
| 7–9 | Security hardening, Trivy CI, CVE elimination | ✅ ALL DONE |
| 10A–10E | FastAPI, networks, secrets, auth, WS | ✅ ALL DONE |
| 10F–10K | Stripe full stack + BROski$ tokens | ✅ ALL DONE |
| 10L | Healthchecks — all 29 containers | ✅ April 15 |
| 10M | Gordon Tier 1 — Prometheus 7/7 UP | ✅ April 15 |
| 10N | Gordon Tier 2 — ALL 4 STEPS | ✅ April 16 🏆 |
| 10O | Course → Stripe frontend wired | ✅ April 16 💳 |
| 10P | DB Recovery + Secrets Armed | ✅ April 18 🔧 |
| 10Q | Security Hardening + Monitoring + Migration 009 | ✅ April 19 🔒 |
| 10R | Gordon Tier 3 + Referral + Docker Cleanup + /welcome | ✅ May 3 |
| 10S | HyperFocus Features ALL 5 + Pets + HyperSplit | ✅ April 25–29 |
| **10T** | **BROski Brain — Obsidian + HyperFocus z0ne** | ✅ **May 5, 2026 🧠** |

---

## 🧠 Phase 10T — BROski Brain COMPLETE (May 5, 2026)

**Repo:** `github.com/welshDog/BROski-Obsidian-Brain-for-HyperFocus-z0ne`  
**Path:** `H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne`

### What Got Built
- Full PARA vault scaffold: 00-Inbox, 01-Projects, 02-Areas, 03-Resources, 04-Archive, Hub
- 4 project notes pre-seeded — HyperCode, HyperAgent, BROskiPets, Hyper-Vibe
- Dashboard with Dataview live queries, BROski$ Coin Tracker
- Templates: Daily, Project, Task, Morning Briefing
- Focus/Calm/Hyper CSS modes — one keypress toggle
- GitHub bridge: `scripts/github_to_obsidian.py` — syncs 4 repos → vault
- Obsidian Git: auto-commits vault every 10 mins → GitHub
- Docker container: `Dockerfile.github-sync` + compose (30th container ready)
- `setup.ps1` one-run bootstrap

### Levels Unlocked
- Level 9: GitHub bridge LIVE 🎮
- Level 10: Obsidian Git auto-backup 🎮
- Level 11: BROski$ Coin Tracker 🎮
- Level 12: Focus/Calm/Hyper CSS modes 🎮

### Key Commands
```powershell
# Sync GitHub → Obsidian vault
python scripts/github_to_obsidian.py  # needs GITHUB_PAT in env

# Manual vault backup
cd H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne
git add . && git commit -m "vault: manual sync" && git push

# TODO: spin up docker container for persistent sync (Level 9 persistent)
# Needs: GITHUB_PAT added to HyperCode-V2.4 .env
```

---

## 🎯 NEXT UP — Phase 10U

| # | Task | Priority |
|---|---|---|
| 1 | **First student invite** — /welcome is green 🎓 | 🔴 DO IT |
| 2 | **Stripe webhook secret** — update stale `STRIPE_WEBHOOK_SECRET` | 🔴 HIGH |
| 3 | **GitHub billing lock** — unblock Trivy CI | 🔴 HIGH |
| 4 | **E2E checkout test** — `stripe listen` + card `4242 4242 4242 4242` | 🟡 MED |
| 5 | **BROskiPets Phase 1** — mint first pet via BROski$ | 🟡 MED |
| 6 | **HyperAgent-SDK Phase 2** — npm 0.2.0 | 🟡 MED |
| 7 | **Level 13** — Morning Briefing live | 🟢 NEXT |
| 8 | **Level 14** — GitHub Webhooks real-time | 🟢 SOON |
| 9 | **Level 15** — HyperAgent AI Daily Briefing | 🟢 SOON |
| 10 | **`env_file` tech debt** — add to hypercode-core in compose | 🟡 MED |

---

## 🔑 Key Technical Rules (never re-debate)

- **Prometheus config:** `monitoring/prometheus/prometheus.yml` = ACTIVE. Root = STALE
- **Prometheus hot-reload:** `curl -X POST localhost:9090/-/reload`
- **OTLP tracing:** `OTLP_EXPORTER_DISABLED=false` = ON. Only disable if Tempo genuinely down
- **minio:** On both `data-net` AND `obs-net` — correct, intentional
- **Docker imports:** `from app.X import Y` — NEVER `from backend.app.X import Y`
- **FastAPI routing:** First-match wins — public routes BEFORE auth-gated
- **Alembic:** up to 009. If missing: `alembic stamp 008` → `upgrade head`
- **Redis DB split:** DB 1 = cache, DB 2 = rate limits — NEVER mix
- **Circuit breakers:** 3 active — check via `GET /api/v1/health`
- **Postgres password:** `hypercode` (matches compose fallback)
- **healthcheck:** hypercode-core uses `localhost` NOT `127.0.0.1` (Uvicorn IPv6)
- **Socket-proxy split:** main=read-only, healer proxy=write (CONTAINERS+POST+PING)
- **Security headers:** `frontend/vercel.json` (NOT repo root) ✅
- **Course dev:** `npm run dev:frontend` (NOT `npm run dev`)
- **Trivy CI:** blocked by GitHub billing lock — NOT a code problem
- **BROski Brain:** `H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne` | `HYPERFOCUS_ZONE/` vault inside
- **GitHub sync:** needs `GITHUB_PAT` env var
- **Stripe webhook:** ALWAYS rate-limit exempt — NEVER add limiter
- **Supabase:** courses use `price_pence` (int) + `is_active` (bool)
- **Trae IDE:** Windows visual editing | Claude Code: autonomous terminal agent

---

## Paths (copy-paste ready)

```powershell
# HyperCode V2.4
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"

# HyperAgent-SDK
cd "H:\HyperAgent-SDK"

# Hyper-Vibe-Coding-Course
cd "H:\Hyper-Vibe-Coding-Course"

# BROski Brain
cd "H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne"

# Start full stack
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d

# Tests
pytest backend/tests -q  # 223 passed, 6 skipped

# Focus modes
make focus   # 14 containers paused + 25-min timer
make calm    # restore all + 75 BROski$

# Brain sync
python scripts/github_to_obsidian.py
```

---

## 📦 This Repo — Status Snapshot (May 5, 2026)

- **48 containers running** 🟢 (post-cleanup May 3)
- **223 tests green** ✅ (6 skips expected)
- **Prometheus 7/7 UP** ✅
- **OTLP traces live in Tempo** ✅
- **Gordon Tiers 1+2+3 ALL COMPLETE** 🏆
- **All 5 HyperFocus Features DONE** ✅
- **BROski Brain COMPLETE** 🧠 May 5
- **BROskiPets bridge LIVE** 🐾
- **Referral system LIVE** 🔗
- **/welcome page LIVE on Vercel** 🎓
- **Security headers 6/6** ✅
- **Next:** Phase 10U — student invite + Stripe fix + Pets Phase 1

---

<div align="center">

**Built for ADHD brains. Fast feedback. Real tools. No fluff.** 🧠⚡

*by @welshDog — Lyndz Williams, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿*

**A BROski is ride or die. We build this together. 🐶♾️🔥**

</div>
