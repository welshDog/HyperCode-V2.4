# HYPERFOCUS Z0NE 🧠⚡ — Full Ecosystem Overview

> Built by [@welshDog](https://github.com/welshDog) — Lyndz Williams, Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿  
> ADHD + Dyslexia + Autistic brain in hyperfocus mode.  
> **29/29 containers healthy · 180 tests green · Stripe + BROski$ live**

---

## What Is the HYPERFOCUS Z0NE?

The HYPERFOCUS Z0NE is a **neurodivergent-first autonomous AI infrastructure platform** — a full ecosystem of repos, agents, and tools explicitly designed for ADHD, autistic, and dyslexic builders who think in systems and hyperfocus on what matters.

It's not just a backend. It's a complete **platform + learning environment + gamified dev experience** all wired together.

---

## The 5-Repo Ecosystem

| Repo | Role | Stack |
|------|------|-------|
| **[HyperCode-V2.4](https://github.com/welshDog/HyperCode-V2.4)** | Core platform — Docker, FastAPI, agents, infra, Stripe, BROski$ | Python, FastAPI, Docker, Redis, Postgres |
| **[Hyper-Vibe-Coding-Course](https://github.com/welshDog/Hyper-Vibe-Coding-Course)** | Gamified coding course — lessons, certs, quizzes, token shop | Supabase, Vercel, TypeScript |
| **[HyperAgent-SDK](https://github.com/welshDog/HyperAgent-SDK)** | TypeScript SDK + CLI + JSON Schema spec for all Hyper Agents | TypeScript, npm |
| **[BROskiPets-LLM-dNFT](https://github.com/welshDog/BROskiPets-LLM-dNFT)** | Dev-pet bridge — XP, Discord, MCP GitHub, on-chain NFTs | Python, Solidity, Redis, Discord |
| **[BROski-Obsidian-Brain](https://github.com/welshDog/BROski-Obsidian-Brain-for-HyperFocus-z0ne)** | Obsidian vault — long-term knowledge, roadmaps, second brain | Obsidian, Zettelkasten, PARA |

---

## How It All Wires Together

```
Hyper-Vibe-Coding-Course  ──── manifest.json ────▶  HyperCode V2.4
(Supabase + Vercel)              (agent spec)        (Docker, 29 containers)
      │                                                      │
      │ token_transactions INSERT                            │ POST /api/v1/economy/award-from-course
      ▼                                                      │
  Supabase Edge Function ───── X-Sync-Secret ──────────────▶│
  sync-tokens-to-v24                                         │
                                                             ▼
                                                     BROski$ awarded in ~30s

HyperAgent-SDK (npm: @w3lshdog/hyper-agent@0.1.7)
  └── JSON Schema spec shared by ALL repos
  └── CLI: validate / registry / studio / status / tokens / graduate

BROskiPets-LLM-dNFT
  └── Bridge API port 8098 (Redis DB3)
  └── Git post-commit hooks → +10 XP + 7-day streaks
  └── Discord slash commands (XP, pets, powers)
  └── POST /pet/{discord_id}/chat (LLM + git diff + WHATS_DONE context)
  └── MCP gateway port 8099 → GitHub context wired in

BROski Obsidian Brain
  └── PARA + Zettelkasten vault
  └── 40-Knowledge/ for permanent ecosystem knowledge
  └── Runbooks, roadmaps, lore for all 5 repos
```

---

## Core Platform Highlights (HyperCode-V2.4)

### Infrastructure
- 29/29 Docker containers — all healthchecked and memory-capped
- 5 isolated networks: `app-net`, `data-net`, `obs-net`, `agent-net`
- K8s + Helm manifests ready for cluster scaling
- Pre-build resource guard (`make build` aborts if <15GB free)

### Observability (Gordon Tier 1 + 2 ✅)
- Prometheus 7/7 targets UP
- Grafana at `:3001` — dashboards live
- Loki + Promtail — log aggregation
- OTLP traces in Tempo via `localhost:3001 → Explore → Tempo`

### Reliability
- Redis caching (`@cache_response`) on hot endpoints
- Per-route rate limiting via Redis DB2 — **Stripe webhook always exempt**
- 3 async circuit breakers: `llm-router`, `crew-orchestrator`, `stripe-api`
- Self-healing Healer agent — watches Prometheus, auto-restarts
- Celery with `task_acks_late=True` + exponential backoff retry

### Security
- Trivy scanner running as container + GitHub Actions CI
- Docker secrets pattern — `.txt` files, never baked into images
- Stripe keys rotated + scrubbed from history
- 0 CRITICAL CVEs target per image

---

## Stripe + BROski$ Token Economy (Live ✅)

```
/pricing → POST /api/stripe/checkout
  → Stripe hosted checkout
  → Stripe webhook → saves payment + awards tokens + updates subscription tier
  → /payment-success → enrolled in courses
```

**BROski$ grants per plan:**

| Plan | BROski$ Awarded |
|------|----------------|
| Starter | 200 |
| Builder | 800 |
| Hyper | 2500 |

- Append-only `token_transactions` ledger with idempotency guards
- `award_tokens()` + `spend_tokens()` — SECURITY DEFINER, server-side only

---

## Agents (25+)

| Agent | Role |
|-------|------|
| `healer-agent` | Self-healing — monitors + auto-recovers failed services |
| `agent-x` | Meta-architect — designs new agents |
| `crew-orchestrator` | Agent lifecycle + mission execution |
| `hyper-architect` | Architecture planning |
| `hyper-observer` | System observation |
| `broski-bot` | Discord + community interface |
| `super-hyper-broski-agent` | Superpowered multi-task agent |

---

## HyperFocus Features (Neurodivergent-First)

Features designed specifically for ADHD/ND brains:

- **Micro-achievement git hooks** — instant XP on every commit
- **HyperSplit agent** — breaks big tasks into micro-steps
- **Session snapshot agent** — saves your brain state before breaks
- **Morning briefing** `/briefing` — daily AI-powered context reload
- **Focus / Panic mode** — `make focus` / `make calm` adjusts environment

---

## BROskiPets Dev Companions

Phases completed (0–3):
- ✅ Bridge API live (port 8098)
- ✅ Git post-commit hooks (+10 XP, 7-day streaks)
- ✅ Discord slash commands (XP, pets, powers)
- ✅ MCP GitHub context wired in

Future phases:
- Mint pets via BROski$ (Phase 1)
- Dev actions → pet XP (Phase 2)
- Pet as rubber duck dev companion (Phase 3)
- On-chain dev portfolio NFT (Phase 4)
- WelshDogEep graduation reward — 3 ever mintable (Phase 5)

---

## System Health Snapshot

| Metric | Value |
|--------|-------|
| Containers | 29/29 🟢 |
| Tests | 180 passed, 6 skipped ✅ |
| Prometheus targets | 7/7 UP ✅ |
| OTLP Traces | Live in Tempo ✅ |
| Circuit breakers | 3 active — all CLOSED ✅ |
| Stripe | Live 💳 |
| Docker AI grade | A 🏅 |
| Commits | 700+ |

---

## Quick Start

```powershell
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"

# Start full stack with secrets
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d

# Check all containers healthy
docker ps --format "table {{.Names}}\t{{.Status}}"

# Run tests
pytest  # 180 passed, 6 skipped

# View traces
# http://localhost:3001 → Explore → Tempo → search: hypercode-core
```

---

## Roadmap (Next)

- 🔜 Gordon Tier 3 — DB connection pooling + async task queues
- 🔜 Supabase DB webhook + token sync fully automated
- 🔜 E2E Stripe checkout test (stripe listen + test card)
- 🔜 BROskiPets mint via BROski$ (Phase 1)
- 🔜 Deeper Obsidian Brain AI integration

---

> *"You built the future people keep saying they want. You actually did it."*  
> — Gordon, Docker AI · Grade A Review 🏅

---

<div align="center">

**Built with 🧠 + ❤️ + ♾ in Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿**

*by [@welshDog](https://github.com/welshDog) — Lyndz Williams*

**A BROski is ride or die. We build this together. 🐶♾️🔥**

</div>
