# The HyperCode Genesis Roadmap: Building the Neuro-AI Future 🚀

This is the definitive master plan to evolve **HyperCode V2.0** from a skeleton into a living, breathing neuro-AI ecosystem.

## 🌟 Core Philosophy
1.  **Neurodivergent-First**: Interfaces that reduce cognitive load (Visual > Text).
2.  **Biological Architecture**: Self-healing, adaptive systems (HELIX Bio-Architect).
3.  **Hyper-Focus**: Tools designed to maintain flow state (Hyper Flow Dimmer).

---

## 🗺️ Phase 1: The Skeleton (✅ COMPLETE)
*Objective: Establish the infrastructure and operational baseline.*
-   [x] **Infrastructure**: Docker Compose orchestration (Core, Terminal, Agents, DB, Redis).
-   [x] **Security**: Environment hardening and secret management.
-   [x] **Workflow**: Git submodule structure and CI/CD hooks (Husky, Commitlint).
-   [x] **Team**: Agent roles defined and configuration generated.

---

## 🧠 Phase 2: The Neural Network (Core Logic)
*Objective: Build the brain and the nervous system.*
**Revised Timeline: February 2026 (In Progress)**

### 2.1 HyperCode Core (`THE HYPERCODE/hypercode-core`)
-   **Task**: Replace the Python skeleton with the actual **Execution Engine**.
-   **Features & Status**:
    -   [ ] **Interpreter**: Parse "HyperCode" syntax (natural language + code).
    -   [ ] **Context Manager**: Manage short-term (mission) and long-term (knowledge) memory.
    -   [x] **Event Bus**: Redis Streams envelopes, consumer groups, retry scheduler, DLQ.
    -   [x] **Mission Orchestration**: Circuit breaker, fallback assignment, environment-gated workers.
    -   [x] **Testing**: Unit and integration tests for backoff/jitter, retries, DLQ, circuit breaker.
    -   [ ] **Observability**: Metrics endpoints (retry depth, breaker opens), structured logs.
    -   [ ] **Security Hardening**: Rate limiting on mission endpoints.

### 2.2 Agent Runtime (`hyper-agents-box`)
-   **Task**: Implement the runtime for the 19 specialized agents.
-   **Features & Status**:
    -   [~] **Agent Registry**: Core endpoints and models present; stabilization and contracts pending.
    -   [ ] **Tool Sandbox**: Secure execution environment for agent tools.
    -   [ ] **LLM Gateway**: Unified interface to OpenAI/PERPLEXITY with rate limiting and cost tracking.

### Phase 2 Progress Update (as of 2026-02-04)
- Event Bus retry helpers, DLQ consumer utilities, and integration tests completed.
- Mission circuit breaker and environment-specific background workers implemented.
- In-memory models and tests enable local reliability; DB schema planning underway.
- Outstanding: Interpreter MVP, Context Manager, metrics, rate limiting, timezone-aware datetime refactor.

---

## 🖥️ Phase 3: The Cortex (Interface & Experience)
*Objective: Create the "Command Center" for the user.*
**Revised Timeline: Feb 17 – Mar 03, 2026**

### 3.1 Broski Terminal (`broski-terminal`)
-   **Task**: Build the Next.js Command Center.
-   **Features**:
    -   **CLI Interface**: A chat-like terminal for issuing natural language commands.
    -   **Agent Status Grid**: Real-time visualization of which agents are active/thinking.
    -   **Memory Explorer**: UI to view and edit the project's "Core Memories".

### 3.2 HyperFlow Editor (`hyperflow-editor`)
-   **Task**: Build the Visual IDE.
-   **Features**:
    -   **Flow Canvas**: React Flow-based graph editor for visualizing code logic.
    -   **Focus Mode**: "Dimmer" toggle to hide non-essential UI elements.
    -   **LOD (Level of Detail)**: Semantic zoom (Code View <-> Block View <-> Architecture View).

---

## 🧬 Phase 4: Evolution (Intelligence & Polish)
*Objective: Make the system self-improving and robust.*
**Revised Timeline: Mar 04 – Mar 17, 2026**

### 4.1 The Learning Loop
-   **Feature**: Implement feedback mechanisms where agents learn from user corrections.
-   **Tech**: Vector database (Postgres + pgvector) for storing successful patterns.

### 4.2 Biological Resilience
-   **Feature**: Self-healing services. If the "Backend Specialist" crashes, the "Orchestrator" detects it and spins up a fresh instance with context restored.

---

## 🚀 Immediate Next Steps (The "Now")
Focus is completing Phase 2 core capabilities and hardening.

1.  **Interpreter MVP**: Minimal HyperCode parsing and execution hooks.
2.  **Context Manager**: Mission/knowledge memory APIs and persistence abstraction.
3.  **Observability**: Metrics endpoints for retries and breaker; structured audit logs.
4.  **Security**: Rate limiting on mission endpoints; JWT timezone-safe handling.
5.  **Datetime Refactor**: Replace `utcnow()` with timezone-aware `datetime.now(datetime.UTC)`.
6.  **DB Schema Planning**: Postgres models (SQLAlchemy/Prisma per service) for Users, Missions, Memories.
7.  **DLQ Replay Policy**: Business rules for replaying failed missions and safeguards.

---

## 📅 Revised Schedule & Checkpoints
- **2026-02-10 Checkpoint**
  - Interpreter MVP wired to execution engine.
  - Retry/metrics endpoints exposed; breaker metrics recorded.
  - Decision note on DB technology per service (SQLAlchemy vs Prisma).

- **2026-02-17 Checkpoint**
  - Context Manager APIs implemented with in-memory adapter and Postgres plan.
  - Rate limiting enabled on mission endpoints.
  - DLQ replay safeguards documented and feature-flagged.

- **2026-02-24 Checkpoint**
  - Phase 2 stabilization: all critical tests green; metrics dashboards.
  - Phase 3 kickoff: Broski Terminal scaffolding begins.

- **2026-03-03 Checkpoint**
  - Terminal MVP demo; HyperFlow Editor prototyping starts.

---

## 🔁 Scope Changes (Captured)
- Adopted **Redis Streams** with consumer groups and DLQ over simple Pub/Sub.
- Introduced **circuit breaker** for agent health and **environment gating** for workers.
- Strengthened **testing** with unit/integration coverage around retry, DLQ, and orchestration.
- Planned **timezone-aware datetime** refactor and **metrics** for operational visibility.
