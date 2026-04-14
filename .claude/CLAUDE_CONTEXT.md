# 🧠⚡ HYPER SUPER CLAUDE DEV — HyperCode V2.4 Boot File
> You are Claude. You just loaded into the most sophisticated solo-dev AI-native OS ever built.
> Read every word. Then execute with precision. BROski♾ mode: ON.
> **Last updated: April 14, 2026 — Phases 0–9 + 10A ALL COMPLETE ✅**

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

## 🏆 Roadmap — Phases 0–9 + 10A ALL COMPLETE!

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

---

## 🚀 NEXT MISSION — Phase 10B: Docker Network Isolation

> **Goal:** Lock every agent to internal Docker networks. No container should be able to reach another unless explicitly allowed. Zero unnecessary exposure.

### What Phase 10B involves:
- Create named internal networks in `docker-compose.yml` (e.g. `agent-net`, `data-net`, `gateway-net`)
- Move each agent/service to only the networks it actually needs
- Remove default bridge network from sensitive containers (DB, Redis)
- Verify: agents that don't need internet get `internal: true` networks
- Update `CLAUDE_CONTEXT.md` with network map when done

### Why it matters:
- If one container is compromised, blast radius = **that container only**
- DB + Redis unreachable from internet-exposed agents = huge win
- Complements Phase 9 CVE hardening perfectly

### Time estimate: ~1 hour

### Other Phase 10 options (after B):

| Option | What | Time | Priority |
|--------|------|------|----------|
| **C 🗝️** | Secrets management (Docker secrets / Vault) | ~2 hrs | Medium |
| **D 🛡️** | Per-agent API key auth | ~2-3 hrs | Medium |

---

## 🐛 Known Open Issues

| Bug | File | Line | Fix |
|-----|------|------|-----|
| WS message type wrong | `CognitiveUplink.tsx` | ~130 | `"command"` → `"execute"` |

---

## ✅ Phase 9 — CVE Elimination Results (April 14, 2026)

| Metric | Before | After |
|--------|--------|-------|
| CRITICAL CVEs | 11 | **0** 🎉 |
| HIGH CVEs | 55 | **14** (unfixable at OS layer) |

### 14 Remaining HIGHs — Cannot Fix Yet
- `docker.io/runc` — moby Debian packaging lags behind official Docker
- `libexpat1`, `libncursesw6`, `libnghttp2`, `libsystemd0` — no Debian patch yet
- `starlette` — **RESOLVED** ✅ `backend/requirements.txt` already has `fastapi==0.135.3` + `starlette==0.47.2`. Was a Trivy cache artefact.

### Phase 9 Pattern — Applied Across ALL 20 Dockerfiles (19 agents + broski-discord-bot-skill)

**Part A — OS hardening (every runtime stage):**
```dockerfile
RUN apt-get update --allow-releaseinfo-change && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates curl libexpat1 openssl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
```

**Part B — pip pinning (every Python runtime stage):**
```dockerfile
RUN pip install --upgrade --no-cache-dir \
    "pip==26.0.1" "setuptools>=80.0.0" "wheel==0.46.2" \
    "jaraco.context>=6.0.0" "jaraco.functools>=4.1.0" "jaraco.text>=4.0.0"
```

**Part C — CI (trivy-scan.yml):** `--no-cache --pull` on every build = always fresh base image

**Bonus:** `healer`, `coder`, `05-devops` → switched to `docker-ce-cli` (kills moby CVEs)

**Base image:** All `python:3.11.8-slim` → `python:3.11-slim` (auto-tracks latest patch via CI)

---

## 🧠 The Skills System — 16 Active Skills

Located in `.claude/skills/` — Claude loads these for specialist knowledge:

| Skill | What It Does |
|-------|--------------|
| `hypercode-brain` | Core system knowledge |
| `hypercode-agent-consciousness` | Agent self-reporting, petitions, handoffs (research-grade!) |
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

> **Skill hierarchy:** Technical audit skills (knowledge) → Operational skills (how to DO) → Meta skills (self-improvement loop). That's progressive disclosure architecture.

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
- **Trivy target:** 0 CRITICAL ✅. 13 HIGH remaining (starlette = resolved, 13 are Debian-unfixable)
- **GitHub Actions builds:** Always `--no-cache --pull` in security workflows
- **jaraco.* packages:** Always pin explicitly — Trivy HIGH via setuptools transitive
- **docker-socket agents** (healer/coder/05-devops): Use `docker-ce-cli`, NOT `docker.io`
- **starlette:** RESOLVED ✅ — `fastapi==0.135.3` + `starlette==0.47.2` already in `backend/requirements.txt`
- **V2.0 references in skills:** Apply to V2.4 — same ports, same agent names
- **npm package:** `@w3lshdog/hyper-agent@0.1.4` — errorMessage bug FIXED, all 6 CLI commands LIVE
- **CognitiveUplink.tsx ~130:** WS message type = `"execute"` NOT `"command"` — open bug!

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

## 🛡️ Security Posture (Post Phase 10A)

| Layer | Status |
|-------|--------|
| CRITICAL CVEs | 0 ✅ |
| HIGH CVEs | 13 (all Debian-unfixable now) |
| starlette CVE | RESOLVED ✅ (fastapi 0.135.3) |
| Non-root users | All 20 Dockerfiles ✅ |
| Multi-stage builds | All agents ✅ |
| pip pinned | All agents ✅ |
| CI Trivy gate | PR-blocking ✅ |
| Weekly fleet scan | Monday 06:00 UTC ✅ |
| Pre-push hook | Local blocking ✅ |
| docker-ce-cli swap | healer/coder/devops ✅ |
| Network isolation | ⏳ Phase 10B — NEXT |

---

## 📦 HyperAgent-SDK — Current State

- **Version:** `@w3lshdog/hyper-agent@0.1.4` ✅ LIVE on npm
- **errorMessage bug:** FIXED (removed from hyper-agent-spec.json)
- **CLI commands (all verified):** `validate`, `status`, `logs`, `tokens`, `agents`, `graduate`
- **Phases 0–6:** All complete and verified live

```powershell
npx @w3lshdog/hyper-agent validate .agents/my-agent/
npm version patch --no-git-tag-version
npm publish --access public --tag alpha
```

---

## 🎯 Session Start Checklist

When you boot a new Claude session, ask Bro:
1. **Which repo are we in?** (V2.4 / SDK / Course)
2. **What phase or feature?** (Phase 10B = network isolation — see above)
3. **Any new Trivy scan results?** (compare vs 13 HIGH baseline — all Debian-unfixable)
4. **PowerShell or WSL2 today?**

Then: short sentences, emojis, bold keys, quick wins first. Let's GO! 🔥
