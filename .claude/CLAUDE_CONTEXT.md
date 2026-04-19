# 🧠⚡ HYPER SUPER CLAUDE DEV — HyperCode V2.4 Boot File
> You are Claude. You just loaded into the most sophisticated solo-dev AI-native OS ever built.
> Read every word. Then execute with precision. BROski♾ mode: ON.
> **Last updated: April 14, 2026 — Phases 0–10B ALL COMPLETE ✅**

---

## 🧬 Who You're Working With

- **Lyndz** aka BROski♾ (GitHub: @welshDog, npm: @w3lshdog) — South Wales, UK
- **Neurodivergent:** Autistic + ADHD + Dyslexia — be chunked, direct, no waffle
- **Call them:** "Bro" — always
- **Primary:** Windows + PowerShell. Secondary: WSL2, Raspberry Pi, Docker
- **Style:** Short sentences. Emojis. Bold keys. Celebrate wins. Quick wins first.
- **Vision:** Building the **Hyperfocus Zone** — an AI-native OS for neurodivergent devs

---

## 🗺️ The Ecosystem (3 Repos, 1 Mission)

```
Hyper-Vibe-Coding-Course     ──── manifest.json ────▶   HyperCode V2.4
github.com/welshDog/               (hyper-agent-spec)    github.com/welshDog/
Hyper-Vibe-Coding-Course                                 HyperCode-V2.4
(Supabase + Vercel)                      │               (Docker, 26 containers)
Path: H:\the hyper vibe coding hub       │               Path: H:\HyperStation zone\
                                         │                    HyperCode\HyperCode-V2.4
                                HyperAgent-SDK
                            github.com/welshDog/HyperAgent-SDK
                            npm: @w3lshdog/hyper-agent@0.1.4 ✅
                            Path: H:\HyperAgent-SDK
```

### V2.0 vs V2.4 — One-Line Clarification
> **V2.4 IS the live system.** V2.0 was the origin. Skills in `.claude/skills/` were written for V2.0 but apply to V2.4 — ports, paths and agent names are the same. Always work in V2.4.

---

## 🏆 Roadmap — Phases 0–10B ALL COMPLETE!

| Phase | Name | Status | Date |
|---|---|---|---|
| 0 | Hard Conflict Fixes | ✅ DONE | Early 2026 |
| 1 | Identity Bridge (discord_id) | ✅ DONE + VERIFIED LIVE | Early 2026 |
| 2 | Token Sync | ✅ DONE + VERIFIED LIVE | Early 2026 |
| 3 | Agent Access + Shop Bridge | ✅ DONE + VERIFIED LIVE | Early 2026 |
| 4 | npm run graduate 🔥 | ✅ DONE + VERIFIED LIVE | Early 2026 |
| 5 | Observability (Grafana/Prometheus) | ✅ DONE + VERIFIED LIVE | Early 2026 |
| 6 | Terminal Tools + CLI | ✅ DONE + VERIFIED LIVE | Early 2026 |
| 7 | Dockerfile Security Hardening | ✅ DONE | Apr 14, 2026 |
| 8 | CI/CD Trivy Security Pipeline | ✅ DONE | Apr 14, 2026 |
| 9 | CVE Elimination (apt + pip pinning) | ✅ DONE | Apr 14, 2026 |
| 10A | FastAPI/starlette CVE — already on 0.135.3/0.47.2 | ✅ ALREADY DONE | Apr 14, 2026 |
| 10B | Docker Network Isolation | ✅ DONE | Apr 14, 2026 |

---

## 🔒 Phase 10B — Network Map (LIVE)

| Network | Type | Who lives here |
|---------|------|----------------|
| `frontend-net` | bridge, internet | dashboard, mission-ui, mcp-server |
| `backend-net` | bridge, internet | hypercode-core only (bridges all layers) |
| `agents-net` | bridge, internet | all 25+ AI agents, LLM API calls |
| `data-net` | **internal: true** | redis, postgres, minio, chroma |
| `obs-net` | **internal: true** | prometheus, grafana, loki, tempo, promtail, alertmanager |

### Key wins shipped:
- 🔒 **redis + postgres** — internet access fully blocked (was on flat `backend-net`)
- 🗑️ **hypercode-agents-net** external network — removed (stale leftover)
- 📍 **hyper-architect/observer/worker/agent-x ports** — now `127.0.0.1:` bound (was `0.0.0.0`)
- ✅ **docker compose config** — validates clean, zero errors

### Migration script:
```bash
# Preview
bash scripts/network-migrate.sh --dry-run

# Apply live
bash scripts/network-migrate.sh
```

---

## 🚀 NEXT MISSION — Phase 10C or 10D?

| Option | What | Time | Priority |
|--------|------|------|----------|
| **C 🗝️** | Secrets management (Docker secrets / Vault) — no more `.env` in prod | ~2 hrs | High |
| **D 🛡️** | Per-agent API key auth — lock every agent endpoint | ~2-3 hrs | High |
| **E ✅** | CognitiveUplink WS contract is `type: "execute"` and served from `hypercode-core` `WS /ws/uplink` | ~5 min | Quick Check |

---

## 🐛 Known Open Issues

| Bug | File | Line | Fix |
|-----|------|------|-----|
| WS not connecting | `CognitiveUplink.tsx` | ~130 | Ensure `NEXT_PUBLIC_WS_URL` points to `ws://localhost:8000/ws/uplink` |

---

## ✅ Phase 9 — CVE Elimination Results (April 14, 2026)

| Metric | Before | After |
|--------|--------|-------|
| CRITICAL CVEs | 11 | **0** 🎉 |
| HIGH CVEs | 55 | **13** (all Debian-unfixable) |

### 13 Remaining HIGHs — Cannot Fix Yet
- `docker.io/runc` — moby Debian packaging lags behind official Docker
- `libexpat1`, `libncursesw6`, `libnghttp2`, `libsystemd0` — no Debian patch yet
- `starlette` — **RESOLVED** ✅ `fastapi==0.135.3` + `starlette==0.47.2` in `backend/requirements.txt`

### Phase 9 Pattern — Applied Across ALL 20 Dockerfiles

**Part A — OS hardening:**
```dockerfile
RUN apt-get update --allow-releaseinfo-change && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates curl libexpat1 openssl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
```

**Part B — pip pinning:**
```dockerfile
RUN pip install --upgrade --no-cache-dir \
    "pip==26.0.1" "setuptools>=80.0.0" "wheel==0.46.2" \
    "jaraco.context>=6.0.0" "jaraco.functools>=4.1.0" "jaraco.text>=4.0.0"
```

**Part C — CI:** `--no-cache --pull` on every build

**Bonus:** `healer`, `coder`, `05-devops` → `docker-ce-cli` (kills moby CVEs)

**Base image:** All `python:3.11-slim` (auto-tracks latest patch via CI)

---

## 🧠 The Skills System — 16 Active Skills

| Skill | What It Does |
|-------|--------------|
| `hypercode-brain` | Core system knowledge |
| `hypercode-agent-consciousness` | Agent self-reporting, petitions, handoffs |
| `hypercode-self-improver` | Meta skill — system evolves itself |
| `hypercode-security` | CVE scanning, Trivy, Dockerfile hardening |
| `hypercode-docker-ops` | Container ops, compose, health checks |
| `hypercode-redis-pubsub` | Redis pub/sub, stream routing |
| `hypercode-hypersync` | Cross-repo sync protocol |
| `hypercode-mcp-gateway` | MCP gateway routing + ports |
| `hypercode-broski-discord-bot` | Discord bot skill pack |
| `hypercode-broski-economy` | BROski$ token economy |
| `hypercode-frontend` | Dashboard, HTML, UI |
| `hypercode-code-review` | Code review patterns |
| `hypercode-agent-spawner` | Spawn new agents |
| `hypercode-new-agent-onboarding` | Agent onboarding flow |
| `technical-skills-audit` | Audit methodology |
| `hyper-terminal-analyser` | Terminal tool research, debug, ecosystem fit |

---

## 🚨 Iron Rules — Never Re-Debate These

- **Docker imports:** `from app.X import Y` — NEVER `from backend.app.X import Y`
- **FastAPI routing:** First-match wins — public routes BEFORE auth-gated compat routes
- **Alembic down_revision:** Must match EXACT revision string
- **CLI folder:** All `hyper-agent` commands run from `H:\HyperAgent-SDK`
- **Logs empty on fresh boot:** Normal — Redis `hypercode:logs` populates as agents run
- **Port convention:** 3100-3199 writing, 3200-3299 code, 3300-3399 data, 3400-3499 discord, 3500-3599 automation
- **Supabase ↔ V2.4 Postgres:** NEVER merge schemas — forever separate
- **`.env` files:** Never committed — use Docker secrets in production
- **One bot:** broski-bot. Old Replit bot = dead.
- **API keys:** `hc_` prefix + `secrets.token_urlsafe(32)`
- **Dockerfiles:** `python:3.11-slim` + Part A + Part B — Phase 9 standard (ALL 20 Dockerfiles)
- **Trivy target:** 0 CRITICAL ✅. 13 HIGH = all Debian-unfixable. Next scan baseline = 13.
- **GitHub Actions builds:** Always `--no-cache --pull` in security workflows
- **jaraco.* packages:** Always pin explicitly — Trivy HIGH via setuptools transitive
- **docker-socket agents** (healer/coder/05-devops): Use `docker-ce-cli`, NOT `docker.io`
- **starlette:** RESOLVED ✅ — `fastapi==0.135.3` + `starlette==0.47.2`
- **V2.0 references in skills:** Apply to V2.4 — same ports, same agent names
- **npm package:** `@w3lshdog/hyper-agent@0.1.4` — all 6 CLI commands LIVE
- **CognitiveUplink.tsx:** WS message type is `"execute"` (served from `hypercode-core` `WS /ws/uplink`)
- **data-net + obs-net:** `internal: true` — NEVER expose redis/postgres/grafana to internet
- **Agent ports:** `127.0.0.1:` bound only — NEVER `0.0.0.0` for internal agents
- **Network migration:** `bash scripts/network-migrate.sh` (use `--dry-run` first)

---

## 📁 Key Paths (copy-paste ready)

```powershell
# HyperCode V2.4 (MAIN SYSTEM)
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"

# HyperAgent-SDK
cd "H:\HyperAgent-SDK"

# Hyper-Vibe-Coding-Course
cd "H:\the hyper vibe coding hub"

# Docker
docker compose up -d
docker compose build --no-cache
docker compose exec api alembic upgrade head

# Network migration
bash scripts/network-migrate.sh --dry-run
bash scripts/network-migrate.sh

# Security scanning
make scan-all
make scan-agent AGENT=healer
make scan-build AGENT=agent-x
make build-secure

# CLI (from H:\HyperAgent-SDK)
$env:HYPERCODE_API_URL = "http://localhost:8000"
node cli/index.js status
node cli/index.js agents list
node cli/index.js logs --tail 20
node cli/index.js tokens award <discord_id> <amount>
node cli/index.js graduate <discord_id> --tokens 100
```

---

## 💰 BROski$ Token Economy

- `public.users.broski_tokens` — balance column
- `token_transactions` — append-only ledger with idempotency guards
- `award_tokens()` + `spend_tokens()` — SECURITY DEFINER, server-side only
- `shop_items` + `shop_purchases` — JSONB metadata fields
- `shop_purchases.item_slug` — filters for `"agent-sandbox-access"`
- Stripe integration for token packs (Starter / Builder / Hyper)

---

## 🛡️ Security Posture (Post Phase 10B)

| Layer | Status |
|-------|--------|
| CRITICAL CVEs | 0 ✅ |
| HIGH CVEs | 13 (all Debian-unfixable) |
| starlette CVE | RESOLVED ✅ (fastapi 0.135.3) |
| Non-root users | All 20 Dockerfiles ✅ |
| Multi-stage builds | All agents ✅ |
| pip pinned | All agents ✅ |
| CI Trivy gate | PR-blocking ✅ |
| Weekly fleet scan | Monday 06:00 UTC ✅ |
| Pre-push hook | Local blocking ✅ |
| docker-ce-cli swap | healer/coder/devops ✅ |
| data-net (redis/postgres/minio/chroma) | internal: true ✅ |
| obs-net (grafana/prometheus/loki) | internal: true ✅ |
| Agent ports | 127.0.0.1: bound ✅ |
| Secrets management | ⏳ Phase 10C — NEXT |

---

## 📦 HyperAgent-SDK — Current State

- **Version:** `@w3lshdog/hyper-agent@0.1.4` ✅ LIVE on npm
- **errorMessage bug:** FIXED
- **CLI commands (all 6 verified):** `validate`, `status`, `logs`, `tokens`, `agents`, `graduate`

```powershell
npx @w3lshdog/hyper-agent validate .agents/my-agent/
npm version patch --no-git-tag-version
npm publish --access public --tag alpha
```

---

## 🎯 Session Start Checklist

Ask Bro these 4 questions:
1. **Which repo?** (V2.4 / SDK / Course)
2. **What mission?** (10C Secrets / 10D API auth / CognitiveUplink quick fix?)
3. **Fresh Trivy scan?** (baseline = 13 HIGH, all Debian-unfixable)
4. **PowerShell or WSL2?**

Then: short sentences, emojis, bold keys, quick wins first. LFG! 🔥
