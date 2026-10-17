# 🧠 CLAUDE.md — HyperCode-V2.4 Constitution
> **For ANY AI, agent, or human working on HyperCode-V2.4.**
> Read this file FIRST. Every session. No exceptions.
> Built by @welshDog — **Updated 2026-10-03 20:15 UTC** (HyperCrew + host-RAM-safety sections are current; the fleet roster lives in `docs/STATUS.md`)

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

## 🧠 HyperCrew — DEPLOYED 2026-10-03 (read `docs/NEXT_SESSION_HANDOVER_2026-10-03.md` first)

- Flow `hypercode.crew` (plan → approve → seal → build → verify → guard → settle → scribe → approve → publish) + Calm Mode,
  Panic/Focus, Quest Settler, Scribe, Morning Card. Branch `claude/focused-darwin-ljrs8k`, draft PR #547. Runbook: `docs/HYPERCREW_DOCKER_RUNBOOK.md`.
- **Proven on Docker:** migration `023`, `scripts/prove-crew.py` phases 0/1/2 across a real core restart, dashboard `/ide` 5/5.
  **🎉 Guard ALLOW → Quest Settler (20 XP/10 coins/achievement) → Scribe draft → handover gate PROVEN live 2026-10-03 12:50 UTC** (run `b01b22bc-…`; builder + verifier = `nemotron-3-ultra-550b-a55b` via `fcc-proxy`, opt-in
  `CREW_LLM_BASE_URL`, sends crew text to NVIDIA NIM). **Still unproven:** real GitHub publish (no GitHub token is configured, by design; every test run rejects the handover gate). **Proven since:** a FULL end-to-end run (guard ALLOW across a core restart, ~17:12 UTC); the verifier downgrades a PASS that lists problems (`d78fa0e3`) and uses one unambiguous two-format prompt (`29f20038`, fixing a live regression that made it return UNKNOWN). Earlier: first COMPLETED run (guard BLOCK) with the weak model.
  `qa-engineer` has a real fail-safe verifier (`agents/04-qa-engineer/crew_verifier.py`, `8043d355`: rules + model, never invents a PASS); live the guard fails only on `verifier_verdict: FAIL`
  because the only host model (`smollm2`) can't write a unified diff. Core was rebuilt at `79b5be99` (2026-10-03 02:05 UTC) so it includes the Guardian fix `34ba1667` and `a2ee4530`; after any backend commit, rebuild + swap core (`up -d --no-deps hypercode-core`) before trusting a live proof. `coder-agent`'s keyword mocks (health/metrics/deploy/docker/"todo list")
  are now flagged `mocked` and refused by core, and crew stage tasks skip them. Crew steps also fail closed if Shepherd is down.
- **Crew reliability (measured 2026-10-03, real model):** success rate **9 of 15 live runs ALLOW (60 %)** (first 3/5, then 6/10 with logging); every BLOCK explained from logs: 1 genuine verifier FAIL, 1 builder ReadTimeout reported as a build, 2 verifier reasoning-budget exhaustions (UNKNOWN). NVIDIA NIM's free tier is intermittently overloaded (503 -> 529 / bare 500) and its latency swings 3 s - 100+ s. **Hardened since (all deployed + live-verified):** verifier = two-format prompt, 105 s budget, one `crew_verify` log line per call, bounded 5xx retry (`b04b081c`); builder = a failed model call is now an ERROR status (it used to be a nested 'completed' build that core read as the diff), bounded 5xx retry, one `crew_build` log line (`1edf14c5`). Tools: `scripts/measure-crew-run.py`, `scripts/measure-crew-rate.sh` (always reject the handover gate: no PR can open). **Not yet measured after the hardening** (one ALLOW run since). **Recreating coder-agent/qa-engineer drops the opt-in proxy unless `CREW_LLM_BASE_URL=http://fcc-proxy:8083` is in the shell env.** Read the logs with `docker logs qa-engineer 2>&1 | grep crew_verify` / `docker logs coder-agent 2>&1 | grep crew_build`.
- **Stack launch reality:** the running stack comes from plain `docker-compose.yml` (it `include:`s core/observability/agents/registry/…),
  not the long `agents-full.yml` command below. Obs services are `profiles: ["observability"]`.
- **Dashboard → core auth:** `/operator/*` needs a human JWT (Bearer) or agent key (X-Agent-Key), **never** the master API key. The dashboard
  reads a 30-day JWT from `secrets/dashboard_service_jwt.txt` (`DASHBOARD_SERVICE_JWT_FILE`; env var must stay unset). **Re-minted 2026-10-03 15:13 UTC; expires ~2026-11-02.**
- **throttle-agent (fixed 2026-10-03, DEPLOYED observe-only 13:30 UTC; debounce added 13:55 (AMBER must repeat in 3 consecutive NEW samples; RED acts at once) — DECIDED 2026-10-03 (Lyndz): stay in OBSERVE, do NOT set `enforce` (review: `WHATS_DONE.md` 16:10 UTC); the combined compose was broken by a wrong Pets-repo path until 2026-10-03 (now fixed via `BROSKIPETS_DIR`, see `WHATS_DONE.md`), so it was deployed via a temp single-service compose):** `THROTTLE_MODE=off|observe|enforce` (default off; a typo → observe, never enforce); signal = the host guard's JSON (`ram_guard.py --loop 30 --skip-docker --json --out ram-signal/ram.json`, mounted read-only); an UNKNOWN (missing/stale) signal never acts; `GET /signal` shows what it WOULD do. `docker pause` frees no RAM. Details: `WHATS_DONE.md` 13:20.
- **The host signal writer is a Task Scheduler job** (`\HyperCode\HyperCode RAM Guard Signal`, as you, at logon, hidden, no elevation, measure-only): `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ram-guard-task.ps1 -Action status|start|stop|uninstall`. If it stops, the signal goes stale → throttle-agent reads UNKNOWN → does nothing.
- **Before any build / start / restart run `python scripts/ram_guard.py --for build`** (host + WSL + Docker; GREEN needed for a build; `--wait 120` to poll). The Windows HOST running out of RAM (1 MB free, 2026-10-03) hung Docker while `wsl -e free -m` looked fine.
- **End of day 2026-10-03:** memory is tight (WSL available ~1.2 GB with `grafana` + `grafana-agent` running, 440 MiB, not started by the assistant: Lyndz decides). The healer (`docker logs healer-agent | grep docker_restart`) restarts the dashboard/core on latency anomalies: check it before calling a restart unexplained. Tomorrow's routine + next task: top of `docs/NEXT_SESSION_HANDOVER_2026-10-03.md`.
- **Session gotchas (cost real time):** `wsl -e free -m` (not `free -m`); `MSYS_NO_PATHCONV=1` in Git Bash; **never** print `docker compose config`
  (expands `.env` secrets — use `-q`); never `docker compose down` to stop obs (stop by name); core runs `alembic upgrade head` before uvicorn;
  `crew-orchestrator` source is bind-mounted (restart, no rebuild); WSL cap is 4 GB — obs stack + core build = under the 1.2 GB stop rule.
- **JWT signing secret ROTATED 2026-10-03 15:13 UTC** (the exposed 10-year admin JWT is dead: 403). Core signs with `HYPERCODE_JWT_SECRET` (= `secrets/jwt_secret.txt`; the `.env` `JWT_SECRET` line is a different, unused value). Rotate again with `MSYS_NO_PATHCONV=1 python scripts/rotate_jwt_secret.py` (preflight) then `--yes`; prints only hashes. Since 2026-10-17 it handles the file layout too (core reads `secrets/jwt_secret.txt`; holders found by mount, dashboard recreated not restarted). New 30-day dashboard token **expires ~2026-11-02** (re-run the script before then). All logins/tokens issued before the rotation need re-issuing.

---

## 🚀 CURRENT STATE — fleet roster

The agent roster (ports, profiles, which agents are live) changes often and is **not** kept in this file.
Read `docs/STATUS.md` (live fleet status) and the compose files (`docker-compose.agents.yml`,
`docker-compose.registry.yml`, `docker-compose.fleet.yml`) for ports and profiles. `fleet-controller`,
`mission-director` and `governor` run only behind `--profile fleet`; see the crew-orchestrator health-gate
exception below. Full history of the Aug 2026 27-agent launch: `WHATS_DONE.md`.

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

> Proven live 2026-08-20 (history: `WHATS_DONE.md`, 2026-08-20 parts 10-11).

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
