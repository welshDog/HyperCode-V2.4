# HyperCode as an Agentic AI Operating System

> **Status:** Living document — updated as the system evolves.  
> **Owner:** @welshDog (BROski♾️)  
> **Related:** [ARCHITECTURE.md](ARCHITECTURE.md), [ai/brain-architecture.md](ai/brain-architecture.md), [mcp/BROSKI_ECONOMY_MCP.md](mcp/BROSKI_ECONOMY_MCP.md)

---

## Why This Doc Exists

HyperCode has grown from "cool agent stack" into something bigger: a **neurodivergent‑first Agentic AI Operating System** (Agentic AI OS).

This doc:

- Names the OS abstraction explicitly.
- Maps HyperCode components to OS concepts (kernel, processes, drivers, security, observability).
- Anchors the evolution tracks (MCP integration, policy‑aware orchestration, island routing, temporal workflows).
- Gives new humans (and agents) a stable mental model to reason about the system.

---

## What Is an Agentic AI OS?

An **Agentic AI Operating System** is a software infrastructure layer that manages the full lifecycle of autonomous AI agents, including:

- Scheduling and resource management.
- Memory and state management.
- Tool orchestration and capability discovery.
- Governance policy enforcement (security, privacy, compliance).
- Observability (metrics, logs, traces).

Unlike traditional automation (rigid, pre‑scripted rules) or basic LLM APIs (single‑prompt responses), an Agentic AI OS provides what a conventional OS provides to applications: **resource management, process isolation, and security controls — but at the cognitive layer**.[web:15][web:18][web:24]

HyperCode already implements most of these capabilities. This doc makes that explicit.

---

## HyperCode OS: Component Map

This section maps HyperCode components to OS concepts.

### Kernel: `hypercode-core` + Data Layer

**Components:**

- `backend/app/main.py` — FastAPI core.
- PostgreSQL database (`postgres` service).
- Redis caches (`redis` service, DB 1 = cache, DB 2 = rate limits).
- Celery task queue + workers.

**Responsibilities:**

- HTTP + WebSocket API for agents and clients.
- Persistent storage for:
  - Users, subscriptions, BROski$ balances.
  - Token transactions (append‑only ledger).
  - Agent state, workflow state, audit logs (future).
- Caching and rate limiting.
- Background task execution (Celery).
- DB migrations (Alembic).

**OS analogy:**

- **Kernel** — core system services, resource arbitration, system calls (APIs).
- **Memory manager** — Postgres + Redis manage persistent and short‑term state.
- **Scheduler** — Celery + queues schedule background work.

---

### Process Manager: Crew Orchestrator + Celery

**Components:**

- Crew Orchestrator agent (in `agents/`).
- Celery workers (`celery-worker` services).
- Priority queues: `hypercode-{high,normal,low}` + DLQ (`hypercode-dlq`).

**Responsibilities:**

- Agent lifecycle management (spawn, monitor, recover).
- Task dispatch to specialized agents.
- Queue management with priority and dead‑letter handling.
- Metrics on queue depth, task duration, failure rates (exposed to Prometheus).

**OS analogy:**

- **Process manager** — creates, schedules, and monitors processes (agents).
- **Init system** — ensures critical services are restarted on failure.
- **Job scheduler** — Celery queues + priority semantics.

---

### Device Drivers: MCP Servers

**Components:**

- `agents/broski-economy-mcp` — BROski$ token economy MCP server.
- Future MCP servers:
  - Stripe MCP (checkout, subscriptions, webhooks).
  - Course stats MCP (enrollment, completion, token sync events).
  - Agent orchestrator MCP (task dispatch, registry access).

**Responsibilities:**

- Wrap domain services behind a standard protocol (MCP).
- Expose **tools** (actions) and **resources** (data views) to agents and external MCP clients.
- Provide discovery via `/.well-known/mcp`.

**OS analogy:**

- **Device drivers** — abstract hardware/devices; here, they abstract domain capabilities.
- **System buses** — MCP is the "USB‑C for AI", a standard connector for capabilities.[web:28]

This is where **Track 1: Deep MCP Integration** lives. Each MCP server is a driver for a subsystem (economy, payments, courses, orchestration).

---

### Security Module: Auth, Rate Limits, Circuit Breakers, Policy Engine (future)

**Current components:**

- Auth middleware on core API routes.
- Rate limiting (Redis‑backed, Stripe webhook exempt).
- Circuit breakers on critical paths (`llm-router`, `crew-orchestrator`, `stripe-api`).
- Docker socket proxy split (read‑only for most agents, restricted POST for healer/throttle).
- Non‑root containers, Phase 9 Dockerfile hardening.

**Future components (Track 2):**

- **Agent Registry** — table of agents with roles, locations, trust scores, allowed data domains.
- **Policy Engine** — rules like:
  - "No PII leaves Local Island."
  - "Pet chat can only read X tables."
  - "Focus mode = no non‑critical notifications."
- **Audit Log** — append‑only log of task routing decisions and policy evaluations.

**OS analogy:**

- **Security module** — access control, capability enforcement, auditing.
- **Mandatory access control** — policy engine + registry.
- **System call filtering** — circuit breakers + rate limits.

---

### Observability: Prometheus, Grafana, Loki, Tempo

**Components:**

- Prometheus (`prometheus` service) — metrics collection.
- Grafana (`grafana` service) — dashboards (Mission Control, Tier 3 pools/queues).
- Loki (`loki`) + Promtail — log aggregation.
- Tempo (`tempo`) — distributed tracing (OTLP).

**Responsibilities:**

- Collect metrics from:
  - HyperCode core (`/metrics`).
  - Agents (health, task counts, durations).
  - DB pools, Celery queues, DLQ depth.
- Visualize system health, agent uptime, request rates, error rates.
- Correlate logs, metrics, and traces for incident investigation.

**OS analogy:**

- **System monitor** — performance counters, resource usage.
- **Debugger / profiler** — traces + logs for root cause analysis.

---

### User Space: Agents, Workflows, Applications

**Components:**

- Specialist agents (frontend, backend, database, QA, etc.).
- Healer agent (self‑healing, MAPE‑K loop).
- DevOps engineer agent (CI/CD, autonomous evolution).
- BROskiPets agents (pet chat, XP, dNFT logic).
- Hyper‑Vibe course frontend + Supabase backend.
- External MCP clients (Claude Desktop, VS Code, Cursor — future).

**Responsibilities:**

- Implement domain logic (code generation, testing, healing, pet interactions).
- Execute workflows (multi‑step pipelines, e.g., code → test → deploy).
- Interact with users (Discord, web UI, future MCP clients).

**OS analogy:**

- **User applications** — run on top of the OS, using its services.
- **Daemons / services** — long‑running background agents (healer, devops).

---

## Islands: Deployment Topology

HyperCode is designed to run across multiple "islands" with different trust, cost, and performance profiles.

### Island Types

- **Local Island**
  - Your main HyperCode box (Windows/WSL, Docker Desktop).
  - Runs `hypercode-core`, Postgres, Redis, most agents.
  - Highest trust, lowest latency for local data.

- **Edge Island**
  - Raspberry Pi or similar edge device.
  - Can run lightweight agents, local Ollama models, pet chat.
  - Medium trust, constrained resources.

- **Cloud Island**
  - Vercel (Hyper‑Vibe frontend), Supabase (course DB), Railway, managed services.
  - Public‑facing services, managed databases, serverless functions.
  - Lower trust for sensitive data, higher scalability.

### Island Routing (Track 3)

Future work will introduce **island‑aware routing**:

- Classify tasks by:
  - Sensitivity (PII, financial, token ops).
  - Compute intensity (LLM inference, video processing).
  - Latency requirements.
- Route tasks to islands based on:
  - Policy rules (e.g., "token ops must stay on Local Island").
  - Resource availability (GPU, CPU, memory).
  - Cost constraints.

This is inspired by the **IslandRun** model of privacy‑aware, multi‑objective orchestration across heterogeneous personal computing ecosystems.[web:11]

---

## Workflows: Temporal‑Style Pipelines (Track 4)

HyperCode already has:

- Celery queues with priority and DLQ.
- DB pool + queue depth metrics.
- Idempotency guards (e.g., `CourseSyncEvent` for token sync).

Next evolution:

- **Workflow definitions** (YAML/JSON) for multi‑step agent pipelines:
  - Example: `code_review.yml` → [agent-x: write code] → [qa-agent: test] → [healer: validate] → [deploy].
- **Checkpointing** — persist workflow state in Postgres at each step.
- **Replay API** — re‑run a workflow from a given step on demand.
- **Deadline‑aware scheduling** — prioritize tasks based on urgency, dependencies, and user impact.

This moves HyperCode toward **Temporal‑style** exactly‑once, deterministic workflows while keeping the existing Celery + Redis infrastructure.[web:12]

---

## Evolution Tracks Recap

These tracks are the roadmap for evolving HyperCode OS:

1. **Track 1: Deep MCP Integration**
   - Wrap domain services as MCP servers (BROski economy ✅, Stripe, courses, orchestrator).
   - Standardize tool + resource discovery for agents and external clients.

2. **Track 2: Policy‑Aware Crew Orchestrator**
   - Add Agent Registry + Policy Engine.
   - Enforce data‑flow policies and trust boundaries.
   - Implement tamper‑evident audit logging.

3. **Track 3: Island‑Style Routing**
   - Define Local, Edge, and Cloud islands.
   - Implement routing policies based on sensitivity, cost, and performance.

4. **Track 4: Temporal‑Style Workflows**
   - Add workflow definitions, checkpointing, and replay.
   - Introduce deadline‑aware, priority scheduling on top of Celery.

---

## Neurodivergent‑First Design

HyperCode OS is explicitly designed for neurodivergent creators (ADHD, dyslexia, autism).

Design principles:

- **Chunked capabilities** — MCP servers expose small, focused tools/resources.
- **Observable state** — dashboards and logs make system behavior visible and predictable.
- **Forgiving failure** — healer agent + circuit breakers + DLQ prevent cascading crashes.
- **User‑controlled policies** — future policy engine lets users encode their comfort zones (e.g., focus mode, panic mode).
- **Gamified progress** — BROski$ tokens, pet XP, and achievements turn dev work into a game.

This is not just an OS for agents — it's a **cognitive architecture** that honors how neurodivergent brains actually work.

---

## Glossary

- **Agentic AI OS** — Operating system for autonomous AI agents.
- **MCP** — Model Context Protocol, an open standard for connecting AI models to tools and data.[web:16][web:19]
- **Island** — A deployment environment (Local, Edge, Cloud) with distinct trust/cost/performance characteristics.
- **Workflow** — A multi‑step, possibly long‑running pipeline of agent tasks with checkpointing and replay.
- **Policy Engine** — Rules that govern agent behavior, data flow, and resource access.

---

## References

- Model Context Protocol (MCP) docs and guides.[web:16][web:19][web:25][web:28]
- Agentic AI OS buyer guides and comparisons.[web:15][web:18][web:24]
- Multi‑Agent Orchestration Protocol research.[web:7]
- IslandRun privacy‑aware orchestration.[web:11]
- Temporal‑style workflow architectures.[web:12]
