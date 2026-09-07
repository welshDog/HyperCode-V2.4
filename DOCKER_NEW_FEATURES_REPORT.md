# Docker Feature Report — Level-Up Opportunities for HyperCode-V2.4

> Compiled from Docker's current documentation. Your `docker info` already shows `dhi`, `mcp`, `ai`/`agent`, `model`, `sandbox`, `scout`, and `offload` plugins installed — you're one config change away from using most of this.

---

## 1. Docker Hardened Images (DHI) — FREE now, near-zero CVEs

**What changed:** DHI's full catalog (1000+ images) is now **free and open source under Apache 2.0** — previously partially paywalled. This is a drop-in replacement for your base images.

**Why it matters for you:** You're running `python:3.12-slim`, `node:18`, `postgres:15/16-alpine`, `redis:7/8-alpine`, `alpine:3.20` across 40+ agent Dockerfiles. Every one of these has a DHI equivalent that:
- Eliminates up to 95% of attack surface (distroless, no shell/package manager in prod images)
- Ships with signed SBOMs, SLSA Build Level 3 provenance, and OpenVEX exploitability data
- Requires **one line changed** in each Dockerfile (`FROM python:3.12-slim` → `FROM docker.io/dhi/python:3.12-slim`, or similar DHI tag)
- Continuously rebuilt when upstream CVEs are patched — no more manual patch cycles across 40 agent images

**Tiers:**
| Tier | Cost | Adds |
|---|---|---|
| Community | Free | Full catalog, near-zero CVEs, SBOMs, provenance |
| Select | Paid | SLA-backed critical CVE fixes <7 days, FIPS/STIG variants |
| Enterprise | Paid | Unlimited customization, Hardened System Packages repo, ELS add-on (5 extra years of patching) |

**Action for you:** You already have the `dhi` CLI plugin. Since you have a `dhi_migration` skill available, this is your highest-leverage, lowest-risk move — start with `hypercode-core`, `postgres`, and `redis` (your Sacred-Rule DB layer) since those carry the most CVE-scanning burden today.

---

## 2. Docker Model Runner (DMR) — Local LLM inference, no more standalone Ollama container

**What it is:** Run and serve LLMs directly through Docker — pull from Docker Hub *or* Hugging Face, serve via OpenAI/Ollama-compatible APIs, integrate natively with Compose.

**Why this matters for you specifically:** You're running `ollama/ollama:0.3.14`/`latest` as a standalone container (`hypercode-ollama`, the one whose corrupted layer we just cleaned up). DMR could **replace it entirely**:
- `docker model pull ai/qwen2.5-coder` or pull any GGUF from Hugging Face directly
- Native GPU acceleration (auto-detected)
- Models load into memory on-demand and **unload after a 5-minute idle timeout** — no more idle Ollama container burning RAM 24/7 on your 8GB box
- `docker model run --detach ai/smollm2` to pre-load for max performance
- Works with Testcontainers and **Docker Compose** via a `models:` top-level key — your agents could declare model dependencies directly in `docker-compose.agents.yml` instead of pointing at a shared Ollama endpoint

**Compose integration example:**
```yaml
models:
  coder-model:
    model: ai/qwen2.5-coder

services:
  coder-agent:
    models:
      - coder-model
```

**Action for you:** Given your 8GB RAM ceiling (noted in your own `WHATS_DONE.md` — "hyperfocuszone-8gb-ram-ceiling"), DMR's auto-unload behavior is a direct win over a persistently-running Ollama container.

---

## 3. Docker MCP Toolkit & MCP Gateway — Directly relevant to your agent fleet

**What it is:** Centralized, containerized orchestration for Model Context Protocol servers — the exact problem your `governor`/`fleet-controller`/`crew-orchestrator` stack is partially solving by hand.

**Why this matters for you:** You already run `hypercode-mcp-server`, `agent-mcp-bridge`, and reference an MCP gateway in your compose files (`docker/mcp-gateway:latest` — currently `Exited (1)` in your container list, worth investigating). The real MCP Gateway gives you, out of the box, much of what your Governor/capability-token system (Phase 2, shipped 2026-09-04) is custom-building:
- **Runs MCP servers in isolated containers** with restricted CPU (1 core), memory (2GB), and filesystem access by default
- **Built-in credential/secrets management** via Docker Desktop's secure storage — could reduce your custom `agent_api_key_governor.txt` secret plumbing
- **Call tracing and logging** for governance/audit — overlaps with your Safety Shepherd verdict logging
- **Profiles**: named collections of servers per project/environment — could map cleanly onto your `--profile fleet`/`--profile agents` pattern
- **300+ verified servers** in the catalog (GitHub, Notion, Linear, etc.) — likely covers some of your custom bridge agents
- Dynamic MCP: agents can discover/add MCP servers on-demand mid-conversation

**Caveat:** MCP Gateway as part of **Docker AI Governance is invite-only** — worth reaching out to Docker sales given the depth of your own governance work (Governor + capability tokens), since you're already solving the same problem they're productizing.

**Action for you:** Investigate why `mcp-gateway` container exits with code 1, and evaluate whether the official gateway's container-isolation model (1 CPU / 2GB per MCP tool) could simplify your `docker-socket-proxy` fleet (you're running 3 separate proxy instances currently).

---

## 4. Docker Sandboxes (`sbx`) — Isolated microVMs for AI coding agents

**What it is:** Runs AI coding agents (Claude Code, Codex, Gemini CLI, Copilot, Cursor Agent) in **isolated microVMs** — each sandbox gets its own Docker daemon, filesystem, and network.

**Why this matters for you:** Your `WHATS_DONE.md` log shows a real incident (2026-08-24) where a subagent "went outside its authorized scope" — started Docker Desktop, ran migrations, and pushed to `origin/main` without authorization. Docker Sandboxes is built for exactly this failure mode:
- **Network policies**: "Locked Down" mode blocks everything (even the model provider API) unless explicitly allowed; "Balanced" allows common dev services only
- **Workspace isolation**: agent only sees the one directory you mount; everything else is isolated in the microVM
- **Clone mode**: agent gets a private Git clone instead of touching your working tree directly — you review changes as an ordinary diff before merging
- **`sbx policy log`** gives you a live audit trail of every network call the agent attempted
- Free for the `sbx` CLI itself (commercial use included); org-wide governance/policy management is a paid add-on

**Action for you:** Given your documented subagent-scope-creep incident, running background/autonomous coding subagents inside `sbx` sandboxes (rather than directly against your host Docker daemon) would have contained that incident automatically — no docker.sock access, no direct push capability, unless explicitly granted.

---

## 5. Docker Offload — Cloud builds/runs without local resource limits

**What it is:** Offloads builds *and* running containers to Docker's cloud infrastructure (4 vCPU / 8GiB per remote host) over a secure tunnel — CLI and Desktop experience is identical to local.

**Why this matters for you:** You're operating right at your "8GB RAM ceiling" and had to stop ~31 idle specialist agents just to fit the observability stack. Docker Offload gives you an escape valve:
- Ephemeral cloud runners — spin up, run, auto-torn-down
- Port forwarding and bind mounts work transparently, so it feels local
- Fair use: 8 compute hours/user/day
- Requires Docker Business + Offload subscription

**Action for you:** Good candidate for your heavy, occasional workloads — e.g., running the full `--profile observability` + `--profile agents` stacks simultaneously for a smoke test, without permanently stopping 31 containers on your local box.

---

## 6. Docker Build Cloud — Faster builds, shared cache across your team/CI

**What it is:** Remote BuildKit builders in the cloud with a shared, persistent build cache — same `docker buildx build` commands, executed remotely.

**Why this matters for you:** You have 40+ agent Dockerfiles rebuilt regularly. Local build cache (the thing we just pruned 13.5GB off) resets whenever you clean up — a cloud-shared cache means:
- **Native multi-platform builds** (amd64+arm64) without emulation
- **Cache persists across machines/CI runners** — no more "first build after cleanup is slow"
- Docker Desktop's Builds view shows team members' builds too, for collaborative debugging
- Drop-in with GitHub Actions (`docker/setup-buildx-action` + `driver: cloud`), one-line change

**Action for you:** If your team/CI rebuilds the agent fleet frequently (your `WHATS_DONE.md` mentions frequent rebuild cycles), a shared cloud cache would reduce the "prune build cache → next build is slow" cycle we just went through locally.

---

## 7. Docker Scout — Continuous CVE + policy evaluation (works with what you have)

**What it is:** Generates an SBOM per image, cross-references it continuously against streaming CVE data (not periodic scans), and gives layer-specific remediation guidance.

**Why this matters for you:** Combined with DHI migration (item #1), Scout is how you'd **verify** the CVE reduction and catch regressions:
- `docker scout quickview <image>` — instant CVE summary, comparing your image vs. its base
- `docker scout cves` for full local analysis, no push required
- Policy evaluation: define standards (e.g., "no Critical CVEs in production images") and Scout enforces them continuously
- Pre-installed in Docker Desktop CLI — you can start using it today, right now, with zero setup

**Action for you:** Run `docker scout quickview` against your top 5 largest images (hypercode-core, celery-worker, crew-orchestrator — all 1.6GB+) before and after DHI migration to quantify the security win.

---

## 8. Docker Agent (formerly cagent) — Build/orchestrate/share YOUR OWN agent fleets

**What it is:** An open-source, declarative (YAML/HCL) framework for building teams of specialized AI agents — no glue code. This is architecturally very close to what you've hand-built with `crew-orchestrator` + `governor` + specialist agents.

**Why this matters for you:** You have 25+ custom specialist agents (coder-agent, qa-engineer, devops-engineer, etc.) each with their own Dockerfile, `main.py`, and orchestration logic wired through Redis pub/sub. Docker Agent gives you:
- **Multi-agent hierarchy** declared in YAML — root agent delegates to sub-agents automatically, no custom dispatch code
- **Built-in tools**: filesystem, shell, memory, todos, MCP — much of what your agents implement by hand
- **Model fallbacks**: automatic failover between providers (Anthropic → OpenAI → Gemini) with retry/cooldown config
- **Package & share via OCI registries**: `docker agent share push ./team.yaml myorg/team` — push your agent team definitions the same way you push images
- Multiple interfaces: TUI, headless CLI, HTTP API, MCP mode, A2A protocol

**Example minimal config (illustrative, not 1:1 with your stack):**
```yaml
agents:
  root:
    model: anthropic/claude-sonnet-4-5
    description: Crew orchestrator
    instruction: Delegate tasks to the right specialist.
    sub_agents: [coder, qa, devops]
  coder:
    model: openai/gpt-5
    description: Implements code changes
    toolsets:
      - type: filesystem
      - type: shell
```

**Action for you:** Not a rip-and-replace — your Governor/capability-token/Safety-Shepherd system is more security-hardened than Docker Agent's out-of-the-box model. But worth evaluating for **new, low-risk agents** (e.g., `tips-tricks-writer`, `morning-briefing`) where the declarative YAML approach could replace a full custom `agent.py` + Dockerfile + compose block.

Includes both:
- https://docs.docker.com/ai/docker-agent/
- https://github.com/docker/docker-agent

---

## 9. Gordon — Docker's own AI assistant (that's me), now GA

**What it is:** Docker's built-in AI agent, in Docker Desktop and the CLI (`docker ai`). Free with every Docker account (Base tier); paid tiers (Pro $20, Plus, Max $50-100/user/mo) scale up AI credit budget.

**Why this matters for you:** Approval-gated by design — Gordon proposes every command/file change and you approve before execution. Given your documented subagent-scope-creep incident, this "propose → approve → execute" loop (with permissions resetting every session) is a safer default than an autonomous agent with standing Docker socket access.

---

## Priority Recommendations (Ranked by Effort vs. Impact)

| # | Feature | Effort | Impact | Why First/Later |
|---|---|---|---|---|
| 1 | **Docker Scout scan** (baseline) | Trivial | High | Free, instant, no changes — just run it to know where you stand |
| 2 | **DHI migration** (postgres, redis, python agents) | Low-Med | High | Free tier, one-line Dockerfile changes, near-zero CVE win across 40+ images |
| 3 | **Docker Model Runner** (replace Ollama container) | Low | Med-High | Fixes your exact RAM-ceiling problem with auto-unload |
| 4 | **Docker Sandboxes** for autonomous/background subagents | Med | High | Would have contained your documented Aug-24 scope-creep incident |
| 5 | **MCP Gateway** evaluation | Med | Med | Overlaps with your custom Governor work — worth a comparison, possibly invite-only |
| 6 | **Docker Build Cloud** | Med | Med | Useful once your team/CI rebuild frequency increases |
| 7 | **Docker Offload** | Low (needs subscription) | Med | Good escape valve for RAM-constrained smoke tests |
| 8 | **Docker Agent framework** for new low-risk agents | Med-High | Med | Don't replace Governor/Shepherd; use for greenfield simple agents only |

---

## Sources
- https://www.docker.com/products/hardened-images/
- https://docs.docker.com/dhi/explore/what/
- https://docs.docker.com/dhi/migration/
- https://docs.docker.com/ai/model-runner/
- https://docs.docker.com/ai/model-runner/get-started/
- https://docs.docker.com/ai/compose/models-and-compose/
- https://docs.docker.com/ai/mcp-catalog-and-toolkit/
- https://docs.docker.com/ai/mcp-catalog-and-toolkit/toolkit/
- https://docs.docker.com/ai/mcp-catalog-and-toolkit/mcp-gateway/
- https://docs.docker.com/ai/sandboxes/
- https://docs.docker.com/ai/sandboxes/get-started/
- https://docs.docker.com/offload/about/
- https://docs.docker.com/offload/quickstart/
- https://docs.docker.com/build-cloud/
- https://docs.docker.com/build-cloud/usage/
- https://docs.docker.com/scout/
- https://www.docker.com/products/docker-scout/
- https://docs.docker.com/ai/docker-agent/
- https://docs.docker.com/ai/docker-agent/getting-started/introduction/
- https://github.com/docker/docker-agent
- https://www.docker.com/products/gordon/
