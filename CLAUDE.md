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

## 🚀 CURRENT STATE — 26-Agent Fleet (August 2026)

> 🎉 **LAUNCHED FOR REAL, 2026-08-20 late evening.** The full fleet below was composed
> up as one system for the first time ever this session (`docker compose --profile
> agents --profile hyper -f docker-compose.yml -f docker-compose.agents-full.yml up
> -d`) — previously every "Live" row in this table meant "already running under
> `agents.yml` independently of this file," never a real joint launch. Full writeup:
> `WHATS_DONE.md`'s 2026-08-20 (late evening, part 10) entry.

### ✅ Core Crew + Specialist Squad (13)

| Agent | Port | Status |
|---|---|---|
| `crew-orchestrator` | :8081 | ✅ Live |
| `brain-agent` | :8082 | ✅ Live — real code shipped 2026-08-20 (was a missing directory) |
| `coder` | — | 🟡 not running under this name (`coder-agent` live, likely same code) |
| `agent-x` | :8084 | ✅ Live — agents-full.yml's duplicate (:8083) deleted 2026-08-20, agents.yml's :8084 is the sole definition |
| `frontend-specialist` | :8012 | ✅ Live |
| `backend-specialist` | :8003 | ✅ Live |
| `database-architect` | :8004 | ✅ Live |
| `qa-engineer` | :8005 | ✅ Live |
| `devops-engineer` | :8006 | ✅ Live |
| `security-engineer` | :8007 | ✅ Live |
| `system-architect` | :8010 | ✅ Live — moved off :8008 2026-08-20 (was colliding with `healer-agent`) |
| `project-strategist` | :8001 | ✅ Live — context fixed 2026-08-20 (was pointing at a deleted directory), also missing `base_agent.py` (fixed); a stale cached image from before the fix crash-looped it once, `docker compose build project-strategist` fixed that too |
| `tips-tricks-writer` | :8018 | ✅ Live — moved off :8009 2026-08-20 (was colliding with `chroma`) |

### 🔨 12 Ghost Agents

| Agent | Port | Status |
|---|---|---|
| `hyper-architect` | :8091 | ✅ Live — needed a `.dockerignore` carve-out (found during launch) |
| `hyper-observer` | :8092 | ✅ Live — build-context path bug fixed 2026-08-20 |
| `hyper-worker` | :8093 | ✅ Live — build-context path bug fixed 2026-08-20 |
| `hyper-split-agent` | :8013 | ✅ Live — moved off :8096 2026-08-20 (was colliding with `safety-shepherd`) |
| `session-snapshot` | :8017 | ✅ Live — moved off :8097 2026-08-20 (was colliding with `evolve-relay`, `--profile pets`) |
| `throttle-agent` | :8014 | ✅ Live — Docker socket access fixed 2026-08-20 via `docker-socket-proxy-healer` (`"docker":"ok"` now); still logs `MemStream unreachable` — a separate, unbuilt dependency, see `NEXT_TASKS.md` item #2b |
| `super-hyper-broski-agent` | :8015 | ✅ Live |
| `test-agent` | :8019 (not :8080/:8100) | ✅ Live — moved off :8100 2026-08-20; build context also needed broadening to `./agents` (found during launch, `shared/` was unreachable) |
| `goal-keeper` | :8050 | ✅ Live |
| `business-agent` | :8020 | ✅ Live — real code built 2026-08-20 (was a mislabeled project-strategist clone) |
| `coderabbit-webhook` | :8024 | ✅ Live |

### 🛡️ Phase 0: Fleet Controller (1, behind `--profile fleet`)

| Agent | Port | Status |
|---|---|---|
| `fleet-controller` | :8094 | ✅ Live — new 2026-08-20 late night. First piece of a multi-phase mission-director/fleet-controller architecture (see `docs/superpowers/specs/2026-08-20-fleet-controller-phase0-design.md`). Structurally incapable of executing anything: no Docker socket, no `DOCKER_HOST`, no crew-orchestrator credential, no LLM client. Fails **closed** (not open, unlike `safety_gate.py`) if Safety Shepherd is unreachable. Behind its own `--profile fleet`, not `agents`/`hyper` — never launches with the standard fleet command above until that flag is added explicitly. |

> `fleet-controller` deliberately has no `crew-orchestrator: condition: service_healthy`
> dependency, unlike every other agent — a named, confirmed exception to the Sacred
> Rules table below (it holds no crew-orchestrator credential and has no dispatch
> path through it in Phase 0). Full smoke-test proof (valid plan → real Shepherd
> `ESCALATE` for the `docker` category, Shepherd killed mid-request → `BLOCK`
> fail-closed, denied profile → `422` before Shepherd is ever contacted, confirmed via
> Shepherd's own logs) in `WHATS_DONE.md`.

> `hypercode-mcp-server` removed from this roster 2026-08-20 — it was a phantom: the
> `agents-full.yml` block pointed at `./agents/hypercode-mcp-server`, which doesn't
> exist. It's not a distinct 25th agent — it's the already-live MCP gateway defined
> in `docker-compose.agents.yml` (`:8823`). The ghost duplicate was deleted, not
> renamed. See `docs/NEXT_TASKS.md`.

**Total:** 25 distinct agents in this roster (the real `hypercode-mcp-server` makes 26
counting it once, not as a ghost) — **25 live** (the 26th, `hypercode-mcp-server`,
also live), 0 not running except the intentionally-nonexistent `coder` alias. Item #9
(all 24 pre-existing agents build + bind `8080`) and item #0 (the
agents-full.yml/agents.yml same-name merge) are both fully closed. **The launch
itself surfaced 3 more real bugs** that no amount of `docker compose
config`/standalone `docker build` could have caught — see `docs/NEXT_TASKS.md` item
#0b (`.dockerignore` gaps for `agent-x`/`hyper-architect`, `test-agent`'s build
context, and — the big one — all 11 ghost agents referencing phantom networks
`app-net`/`agent-net` that were never created anywhere in the real stack). Swept the
whole box after launch: **zero unhealthy containers across all 67 running.**
`throttle-agent`'s Docker-socket gap is also now fixed (wired to the already-built
`docker-socket-proxy-healer`, which its own comment says was meant for exactly
this) — its separate, unbuilt `MemStream` dependency (`docs/NEXT_TASKS.md` item
#2b) remains the one loose end from the launch. `fleet-controller` (Phase 0, the
25th agent, built + smoke-tested 2026-08-20 late night) added zero risk to any of
this — it was verified in isolation and the rest of the fleet stayed at zero
unhealthy throughout.

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

- `.github/workflows/docker-push.yml` — Pushes **all 25 pre-existing agents + `fleet-controller`** to GHCR in parallel matrix (3 jobs, `fail-fast: false`)
- `.github/workflows/ghost-agents-build.yml` — Port validation + parallel ghost-agent builds on push to `main`
- `.github/workflows/health-check.yml` — All 25 agent ports + Sacred Rules lint on every PR

> ⚠️ **`health-check.yml` was never valid, executable GitHub Actions YAML until
> 2026-08-21 — confirmed via run history, not just inferred.** It embedded multi-line
> Python via `python -c "<heredoc>"` blocks whose code was indented *less* than the
> literal block scalar's established floor, terminating the `run:` block early and
> breaking the file's YAML parse from that point on (repro'd with a minimal
> `pyyaml.safe_load` test, then confirmed against the real file). `gh run list
> --workflow=health-check.yml` shows every run completing in **0s**, and `gh run view`
> on one reads **"This run likely failed because of a workflow file issue"** — every
> run since this file existed was rejected at parse time, zero checks ever actually
> ran. Fixed by extracting the embedded Python to real files under
> `.github/scripts/`; the file now parses cleanly and every extracted script was
> executed directly against the live repo state. **`ghost-agents-build.yml` did NOT
> have this problem** — its jobs register correctly (`gh run view` shows real job
> names); its actual, separate blocker is the known GitHub Actions billing lock
> (`docs/NEXT_TASKS.md` "This Week" list). See `docs/NEXT_TASKS.md` items
> #6/#7/#8/#8a for the full write-up.

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

All agents must depend on `crew-orchestrator` being healthy:

```yaml
depends_on:
  crew-orchestrator:
    condition: service_healthy
```

`crew-orchestrator` is the SPOF (single point of failure) — ensure it has `restart: unless-stopped` and a `/health` endpoint.

> **One named exception, confirmed 2026-08-20 late night**: `fleet-controller`
> (Phase 0 of the mission-director/fleet-controller architecture) deliberately does
> **not** depend on `crew-orchestrator`. It holds no crew-orchestrator credential and
> has no dispatch path through it — the only thing it depends on is `safety-shepherd:
> condition: service_started`. Gating it on crew-orchestrator's health would only
> couple a service whose entire job is proving a containment boundary to a second
> SPOF, for zero safety benefit. This exception was asked and confirmed explicitly
> before building — not a silent violation. See
> `docs/superpowers/specs/2026-08-20-fleet-controller-phase0-design.md` §7.

### 🚀 Full Stack Launch Command

> 🎉 **LAUNCHED FOR REAL, 2026-08-20 late evening — this is now a proven command, not
> just a verified-safe one.** Item #0 (13 duplicate agent names between
> `agents-full.yml` and `agents.yml`) was resolved earlier the same session — `agents.yml`'s
> versions (real, live, hardened: volume-mounted code, HYPER-SILLs loadout,
> `security_opt`) stayed canonical, `agents-full.yml`'s 13 duplicate blocks were
> deleted for good. `docker compose config` came back clean — but **actually running
> it surfaced 3 more bugs that config validation can't catch**, because they only
> matter once containers try to start together, not while parsing YAML:
>
> 1. `agent-x`/`hyper-architect` (both `context: .`) hit the same `.dockerignore` gap
>    `hyper-observer`/`hyper-worker` needed earlier — added `architect/`/`agent-x/`
>    carve-outs.
> 2. `agents-full.yml`'s `test-agent` used too narrow a build context
>    (`./agents/test-agent`) to reach the sibling `agents/shared/agent_utils.py` its
>    code directly imports — broadened to `context: ./agents`.
> 3. **The big one**: all 11 of `agents-full.yml`'s own ghost agents referenced
>    networks `app-net`/`agent-net` that were never created *anywhere* in the real
>    stack — only `agents-net`/`data-net` (defined for real in `docker-compose.core.yml`)
>    actually exist. Every one of these 11 could build a perfectly good image but
>    could never start a container. Fixed via `replace_all`:
>    `[app-net, agent-net, agents-net]` → `[agents-net, data-net]` across all 11.
>
> Also hit mid-launch: one transient `hypercode-core` restart under the heavy
> concurrent build/startup load (confirmed not OOM — `OOMKilled=false` — just a
> blip) cascaded a batch of "dependency failed to start" errors; re-ran `up -d` once
> it stabilized. `project-strategist` came up crash-looping on a **stale cached
> image** left from before the item #0 context repoint — `up -d` doesn't rebuild on
> a changed `build.context` automatically, needed an explicit `docker compose build
> project-strategist` first.
>
> **Final state, verified not claimed**: polled every previously-blocked agent until
> none reported `health: starting` — all 16 came back `healthy`. Swept the *entire*
> box: zero unhealthy containers across all 67 running. `throttle-agent`'s Docker
> socket gap (found right after launch) is fixed too — wired to
> `docker-socket-proxy-healer`, an already-built proxy whose own comment names
> throttle-agent as an intended consumer that was just never wired up; `curl /health`
> now shows `"docker":"ok"`. Its separate `MemStream` dependency is still unbuilt —
> `docs/NEXT_TASKS.md` item #2b, needs a decision not a wiring fix. Full writeup:
> `WHATS_DONE.md`'s 2026-08-20 (late evening, part 10/11) entries.

```bash
cd HyperCode-V2.4
docker compose \
  --profile agents \
  --profile hyper \
  -f docker-compose.yml \
  -f docker-compose.agents-full.yml \
  up -d
```

`--profile hyper` is required alongside `--profile agents`: `agents.yml` gates
`agent-x`/`hyper-architect`/`hyper-observer`/`hyper-worker` behind it. All 25 of
these agents (13 existing + 12 ghost, `hypercode-mcp-server` counted once) are live
& coordinated right now. `fleet-controller` (the 26th, Phase 0) is intentionally
**not** part of this command — it needs a separate `--profile fleet` flag added
explicitly, so the standard launch never accidentally brings it up. See the
"Phase 0: Fleet Controller" section above.

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
