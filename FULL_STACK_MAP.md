# 📡 HyperFocus Z0ne — Full Stack Map
> Last updated: June 2026 | Maintained by @welshDog

A complete overview of every service, tool, and platform used across the 5-repo ecosystem.

---

## 🏗️ The 5 Repos
| Repo | Purpose |
|---|---|
| **HyperCode-V2.4** | Core backend — 48 Docker containers |
| **Hyper-Vibe-Course** | Course platform — Supabase + Vercel + Web3 |
| **HyperAgent-SDK** | npm agent framework (`@w3lshdog/hyper-agent`) |
| **BROskiPets-LLM-dNFT** | Web3 NFT pet game — dNFTs + LLM |
| **BROski-Obsidian-Brain** | Second Brain — PARA vault + GitHub bridge |

---

## 🌐 External Services

### Always-On / Free Tier
| Service | What for | Cost |
|---|---|---|
| **GitHub** | All 5 repos, CI/CD, Actions | Free (public repos) |
| **Cloudflare** | Tunnel for Stripe webhooks + DNS | ✅ Free forever |
| **Discord** | broski-bot, briefing agent, community | ✅ Free forever |
| **Ollama** | Local LLM inference (self-hosted) | ✅ Free — your machine |
| **Redis** | Cache (DB 1) + rate limits (DB 2) — Docker | ✅ Self-hosted |

### Paid / Scale-Up Services
| Service | What for | Free Tier | Paid |
|---|---|---|---|
| **Vercel** | Hyper-Vibe-Course frontend | Hobby = free | Pro = $20/mo |
| **Supabase** | DB + auth for course platform | 500MB free | $25/mo |
| **Stripe** | Payments + webhooks | No monthly fee | % per transaction |
| **Render** | Backend hosting (API services) | Free (spins down) | $7/mo always-on |

### ⚠️ Check These!
| Service | Status | Action |
|---|---|---|
| **Railway** | `RAILWAY_VARS.md` exists — may be active | Login & check billing |
| **Grafana Cloud** | `docker-compose.grafana-cloud.yml` | Free tier = 10k metrics |

---

## 🐳 Docker Stack (HyperCode-V2.4)
- **48 containers** across multiple compose files
- Key compose files:
  - `docker-compose.core.yml` — core backend
  - `docker-compose.agents.yml` — full agent swarm
  - `docker-compose.observability.yml` — Prometheus + Grafana
  - `docker-compose.mcp-gateway.yml` — MCP gateway
  - `docker-compose.brain.yml` — Obsidian brain sync
  - `docker-compose.bropets.yml` — BROski Pets services

---

## 🤖 AI / LLM Stack
| Tool | Where used |
|---|---|
| **Ollama** (local) | Self-hosted LLM for agents |
| **OpenAI API** | Fallback / GPT agents |
| **Claude (Anthropic)** | `.claude/` config present in HyperCode-V2.4 |
| **Perplexity AI** | `.perplexity/` config — search + research agent |

---

## 🔐 Sacred Rules (Never Break)
```
✔ docker-ce-cli          — NEVER docker.io for socket agents
✔ from app.X import Y    — NEVER from backend.app.X
✔ .env files             — NEVER committed to git
✔ Stripe webhook         — rate-limit EXEMPT, always
✔ Python indent          — 4 spaces, NEVER 3, NEVER mixed
✔ Redis DB 1=cache, DB 2=rate limits. NEVER mix.
✔ npm run dev:frontend   — NOT npm run dev
✔ discord.py==2.4.0      — NEVER py-cord
✔ Bot entrypoint         — python -u -m cogs.bot. NEVER python main.py
```

---

## 💰 Real Monthly Cost Estimate
```
Vercel Pro    = $20  ← only when live commercially
Render        = $7   ← per always-on service
Railway       = $5?  ← CHECK if still active
Supabase      = $0   ← until scale
Everything else = $0
─────────────────────────
Worst case now = ~$32/mo
Best case      = ~$7/mo
```

---

## 📎 Related Docs
- [`WHATS_DONE.md`](./WHATS_DONE.md) — completed work log
- [`PORT_MAP_COMPLETE.md`](./PORT_MAP_COMPLETE.md) — all Docker port mappings
- [`AGENT-START.md`](./AGENT-START.md) — agent onboarding guide
- [`OPERATIONS.md`](./OPERATIONS.md) — ops runbook
