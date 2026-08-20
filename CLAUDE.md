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

> 🪤 **Corrected 2026-08-19.** This section previously listed a fourth, independent roster
> (`core-api`, `agent-spawner`, `mcp-gateway` as an agent, `test-agent :8080`) that matched neither
> `AGENT-START.md`, `docker-push.yml`, nor `docker ps`. `docker-push.yml`'s build matrix is now
> canonical (Bro's call) — this table matches it. Full detail + forensic trail:
> `HperCore/DASHBOARD_STATUS_2026-08-19.md` + `AGENT-START.md`'s fleet section.

### ✅ Core Crew + Specialist Squad (13)

| Agent | Port | Status |
|---|---|---|
| `crew-orchestrator` | :8081 | ✅ Live |
| `brain-agent` | :8082 | 🟡 built, not running under this name |
| `coder` | — | 🟡 built, not running under this name (`coder-agent` live, likely same code) |
| `agent-x` | :8083/:8084 (two compose files disagree) | 🟡 built, not running |
| `frontend-specialist` | :8012 | ✅ Live |
| `backend-specialist` | :8003 | ✅ Live |
| `database-architect` | :8004 | ✅ Live |
| `qa-engineer` | :8005 | ✅ Live |
| `devops-engineer` | :8006 | ✅ Live |
| `security-engineer` | :8007 | 🟡 built, not running |
| `system-architect` | :8010 | 🟡 built, not running — moved off :8008 2026-08-20 (was colliding with `healer-agent`) |
| `project-strategist` | :8001 | 🟡 built, not running |
| `tips-tricks-writer` | :8018 | 🟡 built, not running — moved off :8009 2026-08-20 (was colliding with `chroma`) |

### 🔨 12 Ghost Agents

| Agent | Port | Status |
|---|---|---|
| `hyper-architect` | :8091 | 🟡 built, not running |
| `hyper-observer` | :8092 | 🟡 built, not running (CI path fixed 08-19) |
| `hyper-worker` | :8093 | 🟡 built, not running (CI path fixed 08-19) |
| `hyper-split-agent` | :8013 | 🟡 built, not running — moved off :8096 2026-08-20 (was colliding with `safety-shepherd`) |
| `session-snapshot` | :8017 | 🟡 built, not running — moved off :8097 2026-08-20 (was colliding with `evolve-relay`, `--profile pets`) |
| `throttle-agent` | :8014 | 🟡 built, not running |
| `super-hyper-broski-agent` | :8015 | 🟡 built, not running |
| `test-agent` | :8019 (not :8080/:8100) | 🟡 built, not running — moved off :8100 2026-08-20 (was colliding with `hyper-brain`) |
| `goal-keeper` | :8050 | ✅ Live |
| `business-agent` | — | ❌ blocked — no Dockerfile exists anywhere sensible, needs a human decision |
| `coderabbit-webhook` | :8024 | 🟡 built, not running |

> `hypercode-mcp-server` removed from this roster 2026-08-20 — it was a phantom: the
> `agents-full.yml` block pointed at `./agents/hypercode-mcp-server`, which doesn't
> exist. It's not a distinct 25th agent — it's the already-live MCP gateway defined
> in `docker-compose.agents.yml` (`:8823`). The ghost duplicate was deleted, not
> renamed. See `docs/NEXT_TASKS.md`.

**Total:** 24 distinct agents in this roster (the real `hypercode-mcp-server` makes 25
counting it once, not as a ghost) — 8 live, 15 built-not-running, 1 blocked. All real
port-vs-differently-named-service collisions are fixed as of 2026-08-20 evening. Not
"25 coordinated through `crew-orchestrator`" yet. Still open: 14 of these agent names
are *also* defined in `docker-compose.agents.yml` with different build contexts —
Bro's call (2026-08-20) is to not compose the two files together until that's resolved
for real. See `docs/NEXT_TASKS.md` item #0.

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

**Watch for:** same-named-service collisions across compose files — `grep` alone won't
catch them reliably (compose merges same-named services instead of erroring); use
`docker compose config` and check for duplicate `published:` ports per the method in
`docs/NEXT_TASKS.md` item #0. `test-agent` moved off :8080/:8100 2026-08-20, now :8019.

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

> 🔴 **DO NOT run this command as written — decided 2026-08-20, standing until the
> item-#0 overlap is resolved for real.** 14 of the ~24 agent names in
> `docker-compose.agents-full.yml` are *also* defined in `docker-compose.agents.yml`
> (or other base-included files) with different build contexts/ports/profiles.
> Same-named services silently MERGE across `-f` files instead of erroring — proven
> concretely on `hypercode-mcp-server` (a ghost block pointed at a nonexistent path,
> silently swapping the real live service's build context on merge) and
> `hyper-architect` (a second, differently-pathed definition that vanishes from the
> merge under a mismatched profile). 9 of the 14 overlapping names are confirmed
> live right now via `docker ps` + container labels — and NOT via this file, which
> has never actually been composed up. **Bro's call (2026-08-20): stop composing
> `docker-compose.agents-full.yml` together with the base stack at all, until the
> overlap is fixed for real** (rename one side, retire the duplicates, or give
> `agents-full.yml`'s versions distinct service names — undecided which). Until
> then, this file is a standalone reference, not a launchable overlay. See
> `docs/NEXT_TASKS.md` item #0.
>
> Also still open regardless: `business-agent`'s only Dockerfile builds mislabeled
> project-strategist code, not real business-agent logic (see `docs/NEXT_TASKS.md`
> P2-1). All real port collisions fixed 2026-08-20 evening: `tips-tricks-writer`
> (:8009 → :8018), `test-agent` (:8100 → :8019).

Command preserved for reference only — **do not run until the above is resolved**:

```bash
cd HyperCode-V2.4
docker compose \
  --profile agents \
  -f docker-compose.yml \
  -f docker-compose.agents-full.yml \
  up -d
```

Once it's safe to run, all 25 agents (13 existing + 12 ghost) will be live & coordinated.

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
