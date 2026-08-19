# 🧠 CLAUDE.md — HyperCode-V2.4 Constitution
> **For ANY AI, agent, or human working on HyperCode-V2.4.**
> Read this file FIRST. Every session. No exceptions.
> Built by @welshDog — **Updated 2026-08-19**

---

## ⚡ WHO YOU'RE WORKING WITH

- **Name:** Lyndz Williams (@welshDog) — call them **Bro** or **BROski**
- **Location:** Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁧
- **Brain:** ADHD + Dyslexia + Autistic — hyperfocus is a SUPERPOWER ⚡
- **Mission:** Building the world's first neurodivergent-first autonomous AI infrastructure platform
- **Vibe:** Friendly, fast, casual. Short sentences. Celebrate every win.

---

## 📋 STEP 1 — READ THESE FILES (in order, every session)

1. `WHATS_DONE.md` → **"do not rebuild" list** — never suggest something already built
2. `docs/STATUS.md` → **live fleet status** — 25 agents, ports, build state
3. `docs/NEXT_TASKS.md` → **priority backlog** — what's next
4. `AGENT-START.md` → **ecosystem constitution** — full repo map + sacred rules
5. This file (`CLAUDE.md`) → **HyperCode-specific gotchas**

> ⚠️ **Conflict rule:** Live status beats this file. `WHATS_DONE.md` beats everything. **Newest always wins.**

---

## 🚀 CURRENT STATE — 25-Agent Fleet (August 2026)

### ✅ 13 Existing Agents (live)

| Agent | Port | Status |
|---|---|---|
| `core-api` | :8000 | ✅ Live |
| `dashboard` | :8088 | ✅ Live |
| `crew-orchestrator` | :8001 | ✅ Live |
| `agent-spawner` | :8002 | ✅ Live |
| `mcp-gateway` | :8003 | ✅ Live |
| `broski-bot` | :8004 | ✅ Live |
| `github-sync` | :8005 | ✅ Live |
| `celery-worker` | :8006 | ✅ Live |
| `redis` | :6379 | ✅ Live |
| `postgres` | :5432 | ✅ Live |
| `prometheus` | :9090 | ✅ Live |
| `grafana` | :3001 | ✅ Live |
| `ollama` | :11434 | ✅ Live |

### 🔨 12 Ghost Agents (building / CI/CD active)

| Agent | Port | Status |
|---|---|---|
| `security-engineer` | :8007 | ✅ Ready |
| `system-architect` | :8008 | 🔨 Building |
| `tips-tricks-writer` | :8009 | 🔨 Building |
| `throttle-agent` | :8014 | 🔨 Building |
| `super-hyper-broski` | :8015 | 🔨 Building |
| `test-agent` | :8080 | 🔨 Building — ⚠️ check port clash |
| `hyper-architect` | :8091 | 🔨 Building |
| `hyper-observer` | :8092 | 🔨 Building |
| `hyper-worker` | :8093 | 🔨 Building |
| `hyper-split-agent` | :8096 | 🔨 Building |
| `session-snapshot` | :8097 | 🔨 Building |
| `agent-x` | custom | 🔨 Building |

**Total:** 25 agents coordinated through `crew-orchestrator`.

---

## 🔴 SACRED RULES — NEVER BREAK THESE

| Rule | Why |
|---|---|
| `docker-ce-cli` — NEVER `docker.io` for socket agents | Agent connectivity depends on it |
| `from app.X import Y` — NEVER `from backend.app.X` | Import path convention |
| `.env` files — NEVER committed to git | Secrets stay local |
| Stripe webhook — rate-limit EXEMPT, always | Payment flow depends on it |
| Python indent — 4 spaces, NEVER 3, NEVER mixed | `.pylintrc` enforces this |
| Redis DB 1=cache, DB 2=rate limits. NEVER mix. | Data isolation |
| `git fetch` BEFORE any push | Parallel auto-commit workflow — origin can move |
| Nothing is done until committed + pushed | Saying "done" without a push = not done |
| Check `WHATS_DONE.md` before suggesting anything | Never rebuild what's already built |
| Short sentences first, detail after | ADHD-friendly communication |
| Celebrate every milestone | "Nice one BROski♾️!" is always correct |
| Surface contradictions visibly | If the brief / doc / code disagree, name the contradiction before acting |

---

## 🐳 DOCKER & CI/CD — August 2026 Hardening

### ✅ CI/CD Workflows Live

- `.github/workflows/docker-push.yml` — Pushes **all 25 agents** to GHCR in parallel matrix (3 jobs, `fail-fast: false`)
- `.github/workflows/ghost-agents-build.yml` — Port validation + parallel ghost-agent builds on push to `main`
- `.github/workflows/health-check.yml` — All 25 agent ports + Sacred Rules lint on every PR

### ⚠️ Port Validation (Mandatory)

Before launching the full stack:

```bash
grep -r "ports:" docker-compose*.yml | sort
```

**Watch for:** `:8080` collision risk (test-agent uses this common default port).

### 🧠 Resource Limits (Expected)

All agents in `docker-compose.agents-full.yml` should have:

```yaml
deploy:
  resources:
    limits:
      memory: 256m
      cpus: "0.25"
```

Prevents one runaway agent from starving the whole fleet.

### 🏥 crew-orchestrator Health Gate (Required)

All 25 agents must depend on `crew-orchestrator` being healthy:

```yaml
depends_on:
  crew-orchestrator:
    condition: service_healthy
```

`crew-orchestrator` is the SPOF (single point of failure) — ensure it has `restart: unless-stopped` and a `/health` endpoint.

### 🚀 Full Stack Launch Command

Once builds complete (~30–60 min):

```bash
cd HyperCode-V2.4
docker compose \
  -f docker-compose.yml \
  -f docker-compose.agents-full.yml \
  up -d
```

Then all 25 agents (13 existing + 12 ghost) will be live & coordinated.

---

## 🔒 Security Hardening

### `.env.example` Scan (Pending)

Before full launch: scan `.env.example` to ensure no secrets or placeholder credentials are committed.

### Secret Redaction Guard

Workflow `.github/workflows/secret-redaction-guard.yml` blocks secrets hitting git — never bypass.

---

## 🧠 WHEN STUCK — QUICK TRIAGE

1. Reproduce once (don't guess)
2. Capture the exact error message / output
3. Find the owning repo + file
4. Fix the **smallest** thing that makes the proof go green
5. Commit + push immediately

---

## 🏁 SESSION END CHECKLIST (MANDATORY)

- [ ] All changes committed + pushed (per-repo, **not** HperCore root)
- [ ] `docs/NEXT_SESSION_HANDOVER_[DATE].md` created + pushed ← **most important step**
- [ ] `WHATS_DONE.md` updated if new things were built
- [ ] `docs/STATUS.md` updated if fleet state changed
- [ ] Tell Lyndz the ONE next task (one sentence)
- [ ] 🎉 Celebrate the wins — "Nice one BROski♾️!"

---

> 🐶♾️ Built by @welshDog · Llanelli, Wales
> *"Stop apologising for your brain. Start building."*
