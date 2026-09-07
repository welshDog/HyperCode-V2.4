# Docker Level-Up — Session Report (2026-09-07)

> One session, four phases: a first real CVE baseline, and the standalone Ollama
> container replaced by Docker Model Runner. All shipped to `main`, evo gate
> green, rollback in place.

---

## TL;DR

| | Before | After |
|---|---|---|
| Local CVE picture | "0 known vulns" (assumption from a June audit) | **24 CRITICAL / 224 HIGH** across 10 local images, per-image, with a ranked fix order and a re-runnable scan script |
| Local LLM runtime | `ollama/ollama:0.3.14` container, **1 GB reserved / 3 GB limit, always on** | `alpine/socat` shim (**944 KiB**) → Docker Model Runner; models load on demand, unload after 5 min idle |
| LLM app code | — | **unchanged** — shim keeps the `hypercode-ollama` service name |
| Compose YAML | — | net **−55 lines** (deleted the broken GPU-Ollama service) |
| Rollback | — | `-f docker-compose.hosted-llm.yml` (agents → Anthropic) |

**Commits on `main`:** `3c14cecf` (Scout baseline + Ollama tune), `e226d225`
(security quick-wins + DHI checklist), `b81b7950` (DMR spike), `588a57db`
(Phase 4 cutover).

---

## Why this happened

`DOCKER_NEW_FEATURES_REPORT.md` landed pitching eight Docker features (Hardened
Images, Model Runner, MCP Gateway/Toolkit, Sandboxes, Offload, Build Cloud,
Scout, Docker Agent). We triaged them against this box's real constraints —
**~4 GB WSL VM, solo operator, no paid Docker tier** — and kept only the two that
give something back without costing money or RAM:

- **Scout** — free, already installed, zero-change. We'd never actually measured
  our CVE position.
- **Docker Model Runner** — directly attacks the RAM ceiling that has repeatedly
  forced agents to be stopped to fit other work.

The rest were deferred with reasons: DHI-wholesale is a real project with
breakage risk (distroless = no shell/curl/ps), MCP Gateway's default 1 CPU / 2 GB
*per server* would make the RAM problem worse, Sandboxes/Offload/Build Cloud need
a paid Docker Business subscription and assume a team.

Full plan: `~/.claude/plans/…-hypercode-v2-4-parallel-lighthouse.md`.

---

## What was done

### Phase 1 — Scout CVE baseline

- New re-runnable script **`scripts/docker-scout-baseline.ps1`** — scans the
  images actually built/running on this box (the existing
  `docker-scout-audit.ps1` only hits the pushed `:v2.4.2` registry tags), skips
  anything not present locally instead of trying to pull it, records digests +
  Scout DB timestamp so a later re-scan is a clean diff.
- Output: **`docs/health-reports/scout-baseline-2026-09-07.md`** — per-image
  CRITICAL/HIGH/MEDIUM/LOW, an analysis section, and a ranked fix order.

| Image | CRIT | HIGH | Main driver |
|---|---:|---:|---|
| `postgres:16-alpine` | 5 | 38 | openssl + Go stdlib in the Alpine base |
| `hypercode-core` | 4 | 53 | `gitpython 3.1.50`, `chromadb`, `mcp 1.26.0`, openssl |
| `memstream` | 3 | 27 | base is still `python:3.9-slim` |
| `redis:8-alpine` | 3 | 18 | openssl in the Alpine base |
| `healer-agent` | 2 | 14 | `python:3.11` base + deps |
| `safety-shepherd` | 2 | 19 | `python:3.11` base + deps |
| `hyperhealth-worker` | 2 | 24 | `python:3.11` base + deps |
| `hypercode-mcp-server` | 2 | 20 | `python:3.11` base + `mcp 1.26.0` |
| `hyper-brain` | 1 | 9 | `python:3.11` base |
| `agent-mcp-bridge` | **0** | **2** | rebuilt days ago for the v5 bake |

The `agent-mcp-bridge` row is the tell: **it's mostly stale bases, not app
code.** A `docker pull` of current bases + `--no-cache` rebuild clears most of
the 224 highs. `gitpython 3.1.50` alone is 1 critical + ~20 high, fixed by a
one-line pin to 3.1.59.

Follow-on docs (Bro): **`SECURITY_QUICK_WINS.md`** (verified pins —
`gitpython>=3.1.59`, `mcp>=1.28.1,<2` with the SDK-v2 breaking-change trap
called out) and **`DHI_PILOT_CHECKLIST.md`** (4-phase pilot, Phase 0 = this
baseline).

### Phase 2 — Ollama idle-unload (interim)

`OLLAMA_KEEP_ALIVE=24h → 5m` in `docker-compose.core.yml` /
`.mcp-gateway.yml`. `24h` pinned the model in RAM permanently; `5m` lets Ollama
drop idle models itself. This captured most of the RAM benefit as a one-line
change while Phase 3/4 were verified — and was then superseded by the cutover.

### Phase 3 — Docker Model Runner verification spike

Enabled Model Runner (`docker desktop enable model-runner --tcp=12434` — no
Docker Desktop restart, 37 running containers untouched) and probed it.
Recorded in **`docs/health-reports/dmr-spike-2026-09-07.md`**.

**The decisive finding:** DMR v1.2.8 serves the **Ollama-native API**
(`/api/tags`, `/api/generate`, `/api/chat`) with the exact response shapes
`backend/app/llm/ollama.py` and `brain.py` already parse — plus the
OpenAI-compatible `/engines/v1/…`. Reachable as
`http://model-runner.docker.internal` from every non-internal compose network
and verified from `hypercode-core`, `hyper-brain`, and `agent-mcp-bridge`
themselves.

→ **Gate decision: config swap, not the pre-approved code migration.** Native
5 min idle-unload TTL. CPU-only backend (`llama.cpp b9879-cpu`).

### Phase 4 — the cutover (config swap)

The compose service **still called `hypercode-ollama`** is now a ~1 MB
`alpine/socat:1.8.0.1` shim:

```yaml
command: >-
  TCP-LISTEN:11434,fork,reuseaddr
  TCP:model-runner.docker.internal:80
```

Because the service name and port are unchanged, **every consumer and every
`depends_on: hypercode-ollama` is untouched** — no edits to
`backend/app/llm/ollama.py`, `brain.py`, or the ~6 agents that call the LLM.

| Area | Change |
|---|---|
| `docker-compose.core.yml` | ollama image → socat shim + a real health check; `OLLAMA_MODEL_PREFERRED` → `smollm2,qwen2.5-coder,qwen2.5` |
| `docker-compose.agents.yml` | per-agent model defaults → `ai/smollm2`; **deleted `hypercode-ollama-gpu`** (image was pruned in the Sept cleanup; GPU DMR is a backend toggle, not a service) |
| `.brain.yml` / `.registry.yml` / `.mcp-gateway.yml` | model names → `ai/smollm2`; mcp-gateway's own `ollama` → same shim; registry `LLM_API_BASE` → DMR `/engines/v1` |
| `.env` | model names (machine-local, gitignored) |
| `scripts/boot.ps1` | STEP 12 warm-up → `docker model pull ai/smollm2` |
| `docs/DOCKER_MODEL_RUNNER.md` | rewritten — it previously documented Ollama relabelled, not the real feature |

**Verified live after the swap:**

- shim `Up (healthy)`, **944 KiB RSS**
- `/api/tags` + `/api/generate` through the shim from `hypercode-core`,
  `hyper-brain`, `agent-mcp-bridge`, and the host — all HTTP 200
- the **running `OllamaModelResolver`** inside `hypercode-core` resolves
  `DEFAULT_LLM_MODEL=auto` → `docker.io/ai/smollm2:latest`, and DMR accepts that
  fully-qualified name in `/api/generate`
- `docker model ps` shows the 5 min idle-unload countdown
- no unhealthy containers anywhere — nothing else moved

The `/api/tags` `"size":0` concern from the spike turned out to be a non-issue:
`select_best_ollama_model()` treats a 0 size as "unknown" and skips the
`OLLAMA_MAX_MODEL_SIZE_MB` cap — no code change needed.

---

## How it helps

### 1. RAM — the constraint that actually bites

This box is a ~4 GB WSL VM. The recurring operational pain all year has been
stopping agents to fit other work (31 agents stopped to run the observability
stack). The Ollama container reserved **1 GB and capped at 3 GB, 24/7**, whether
any agent was using a model or not.

Now: a **944 KiB** shim, and model memory lives in Docker Desktop's shared
Model Runner process — loaded only when something infers, **freed automatically
5 minutes after the last call**. That's roughly a gigabyte of reservation handed
back to the compose scheduler, and one fewer always-on multi-GB process
competing with the agent fleet.

### 2. Security — we can now see, and prove progress

Before today the working assumption was "0 known vulns" from a June audit. Now
there's a **concrete, per-image, re-runnable baseline** (24C / 224H) with a
ranked fix order. Concretely this unlocks:

- **Cheap wins are now visible and pinned** — `gitpython>=3.1.59` and
  `mcp>=1.28.1,<2` (`SECURITY_QUICK_WINS.md`) clear a critical + ~20 highs for a
  two-line `requirements.txt` change.
- **The DHI pilot can prove its value** — `DHI_PILOT_CHECKLIST.md` Phase 0 is
  this baseline; run the same script after a base-image change and the delta is
  the evidence.
- **Regressions become measurable** — digests are recorded, so a future scan is
  a clean before/after.

### 3. Low blast radius, easy exit

The socat-shim approach means the cutover touched **config only** — no
application code, no consumer edits, no test changes. If DMR misbehaves,
`-f docker-compose.hosted-llm.yml` routes every agent to Anthropic and takes the
shim out of the path. The old Ollama image is gone, but that path was already
the documented fallback for this RAM-constrained box.

### 4. Cleaner surface

Net **−55 lines** of compose YAML. The `hypercode-ollama-gpu` service — broken
since the image was pruned, `--profile gpu` only, never used — is gone. One LLM
runtime concept instead of "core Ollama vs GPU Ollama vs a container literally
named `model-runner` running Ollama."

### 5. Honest scope

Eight features → two acted on, six deferred **with documented reasons**. No
money spent, no RAM-negative changes shipped, no distroless base-image project
started on a fragile fleet. The deferred list is written down for when the
constraints change.

---

## Trade-offs (stated plainly)

- **No speed gain.** DMR's backend here is CPU-only (`llama.cpp b9879-cpu`) —
  inference is exactly as fast (or slow) as Ollama was. The local LLM is a
  fallback path anyway; agents prefer Anthropic when the key is set.
- **Cold start.** First request after 5 min idle reloads the model from disk
  before the first token. Bursty agent traffic will occasionally see a slow
  first response — same characteristic as the Phase 2 `KEEP_ALIVE=5m` interim.
- **Coder agents temporarily downgraded.** They ran `qwen2.5-coder:3b`; they now
  run `ai/smollm2` (much smaller) until the real model is pulled — the catalog
  name `ai/qwen2.5-coder` returns `insufficient_scope` (likely wrong name). Next
  step: `docker model pull hf.co/qwen/qwen2.5-coder-3b-instruct-gguf:q4_k_m`,
  then match `OLLAMA_MODEL_PREFERRED` to whatever `docker model ps` reports.
- **One extra network hop** through socat — negligible for LLM latency.
- **Model Runner is now a persistent enabled feature** on this Docker Desktop
  (lightweight; idle-unloads).

---

## Artifacts produced

| File | What |
|---|---|
| `scripts/docker-scout-baseline.ps1` | re-runnable local CVE scan |
| `docs/health-reports/scout-baseline-2026-09-07.md` | the baseline + analysis + fix order |
| `docs/health-reports/dmr-spike-2026-09-07.md` | DMR probes, gate decision, config-swap scope |
| `SECURITY_QUICK_WINS.md` | verified dependency pins |
| `DHI_PILOT_CHECKLIST.md` | 4-phase Hardened Images pilot |
| `docs/DOCKER_MODEL_RUNNER.md` | rewritten for the real feature |
| `docs/reports/DOCKER_LEVELUP_2026-09-07.md` | this report |
| 6 compose files + `scripts/boot.ps1` + `WHATS_DONE.md` | the cutover |

---

## Next session

1. `qwen2.5-coder` via HF-GGUF pull → repoint the coder agents
2. Security quick wins — `gitpython` + capped `mcp` pin + `memstream` base bump
3. `--no-cache` rebuild of `hypercode-core` → re-run the Scout script for the
   after-numbers
4. DHI pilot on the clean rebuilt baseline
5. `mcp-gateway` `Exited (1)` — 15 minutes of logs before it becomes a mystery
6. `chromadb` 2-critical recheck against the latest release, or write the
   accepted-risk note
