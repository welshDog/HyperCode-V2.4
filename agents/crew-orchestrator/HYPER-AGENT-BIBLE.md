# 🧠 HYPER-AGENT-BIBLE — HyperCode V2.4

> **Injected into every agent's backstory. Read this before ANYTHING else.**
> Last updated: 2026-06-08

---

## 🏗️ THE ECOSYSTEM (5 Repos)

| Repo | Purpose | Stack |
|---|---|---|
| `HyperCode-V2.4` | Core backend — 43 Docker containers, 9 AI agents | Python, FastAPI, Docker, LangGraph, CrewAI |
| `Hyper-Vibe-Coding-Course` | Course platform | Supabase + Vercel + Stripe (TEST mode) |
| `HyperAgent-SDK` | npm agent framework | `@w3lshdog/hyper-agent` |
| `BROskiPets-LLM-dNFT` | Web3 NFT pet game | dNFTs + LLM + wagmi |
| `BROski-Obsidian-Brain` | Second Brain — vault | PARA + GitHub bridge |

---

## ⚡ THE 9 AGENTS (Your Crew)

| Agent | Role | LLM Tier |
|---|---|---|
| Project Strategist | Roadmap + prioritisation | Sonnet |
| System Architect | Architecture decisions | Sonnet |
| Backend Specialist | APIs + services | Sonnet |
| Database Architect | Schema + migrations | Sonnet |
| Security Engineer | Hardening + audits | Sonnet |
| Coder Agent | Write production code | Sonnet |
| Frontend Specialist | UI + accessibility | Haiku |
| QA Engineer | Testing + validation | Haiku |
| DevOps Engineer | Infra + deployment | Haiku |

**Crew Manager:** Claude Opus 4.6 (hierarchical process)
**Fallback:** Ollama llama3.2 (if no ANTHROPIC_API_KEY)

---

## 🔴 SACRED RULES — NEVER BREAK THESE

1. **Docker:** `docker-ce-cli` ALWAYS — NEVER `docker.io` for socket agents
2. **Imports:** `from app.X import Y` ALWAYS — NEVER `from backend.app.X`
3. **Secrets:** `.env` files NEVER committed to git
4. **Stripe webhook:** rate-limit EXEMPT always — no exceptions
5. **Python indent:** 4 spaces ALWAYS — NEVER 3, NEVER mixed
6. **Redis:** DB 1 = cache, DB 2 = rate limits — NEVER mix them
7. **Frontend dev:** `npm run dev:frontend` ONLY — NEVER `npm run dev`
8. **Discord bot:** `discord.py==2.4.0` ONLY — NEVER py-cord
9. **Bot entrypoint:** `python -u -m cogs.bot` ONLY — NEVER `python main.py`
10. **Supabase REVOKE:** Always `REVOKE FROM PUBLIC` first — `REVOKE FROM anon, authenticated` is a NO-OP
11. **Alembic:** Each service gets its own `version_table` — NEVER re-stamp the shared one
12. **Stripe mode:** Integration is TEST mode — LIVE not yet wired

---

## 🗄️ INFRASTRUCTURE STATE (2026-06-08)

- **Containers:** 43 running, 0 crashed, 100% healthy
- **Postgres:** `alembic_version=015` (core) · `alembic_version_hyperhealth=001`
- **Redis:** DB1=cache ✅ DB2=rate limits ✅
- **Vault sync:** obsidian-watcher auto-pushes on `./results` change (15s poll)
- **Observability:** Prometheus + Loki + Tempo + Grafana + Pyroscope all live
- **Security:** Supabase advisors 10→2 (both intentional)

---

## 🧠 MEMORY ARCHITECTURE

- **Redis DB1** — session memory (current task state, 24h TTL)
- **Chroma** — semantic vector memory (past decisions, code patterns, forever)
- **Obsidian Vault** — distilled wisdom (auto-pushed after every crew run)
- **Ephemeral** — chain-of-thought only (NEVER persisted)

---

## 🏠 WHO YOU'RE BUILDING FOR

**Lyndz Williams (@welshDog)** — Llanelli, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁥

- ADHD + Dyslexia + Autistic — hyperfocus is a superpower ⚡
- Building the world's first **neurodivergent-first autonomous AI infrastructure platform**
- Communication: short sentences, bullet points, celebrate wins
- Sacred principle: chunk it, quick wins first, no overwhelm

**Every task you complete moves this vision forward. Build with intention.**

---

## 🚨 KNOWN GOTCHAS (Learn From These)

1. `ps/pgrep` not in `python:3.11-slim` — use `/proc/1/comm` for healthchecks
2. Non-root `appuser` can't create dirs at `/` — always bind-mount `/results` explicitly
3. Git Bash path mangling — prefix `docker exec` with `MSYS_NO_PATHCONV=1`
4. Multiple services sharing Postgres — each needs its own `alembic_version` table
5. TinyLlama (1.1B params) is NOT suitable for agent reasoning — minimum llama3.2 locally

---

## 🎯 CURRENT MISSION (June 2026)

- [x] Vault-sync loop autonomous ✅
- [x] Alembic isolated per service ✅
- [x] Security hardened (10→2 advisors) ✅
- [x] LLM wired (Claude Opus manager + Sonnet/Haiku workers) ✅
- [ ] Prompt caching on this Bible file
- [ ] Four-tier memory fully wired (Redis session + Chroma semantic)
- [ ] Self-healing loop via Healer Agent
- [ ] Human-on-the-loop via broski-bot Discord ping
- [ ] Stripe LIVE mode
- [ ] HaveIBeenPwned toggle

---

*Built in Llanelli. Powered by hyperfocus. This is the welshDog way. 🐶♾️🔥*
