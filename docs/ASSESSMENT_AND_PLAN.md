# HyperCode-V2.0 Detailed Assessment & Implementation Plan

## 1. Comprehensive Analysis

### 1.1 Architecture & Structure
The project utilizes a **Modular Cognitive Architecture** designed for a distributed agent system.
- **Core Components:**
  - **Backend:** FastAPI (Central Hub, Memory, Task Routing).
  - **Orchestrator:** Python-based service managing agent lifecycles and task delegation.
  - **Agents:** Independent Dockerized services (Frontend, Backend, Healer, etc.) sharing a common `BaseAgent`.
  - **Frontend:** Next.js Dashboard for visualization and control.
  - **Infrastructure:** Docker Compose, PostgreSQL (Data), Redis (Bus), ChromaDB (RAG), MinIO (Storage).

### 1.2 Current Status & Gaps
| Component | Status | Critical Gaps |
|-----------|--------|---------------|
| **Infrastructure** | 🟢 100% | None. All containers (33+) are operational. |
| **Orchestration** | 🟡 Partial | Relies on **mocked logic** for RAG, Planning, and System Stats. Hardcoded service URLs. |
| **Agents** | 🟡 Partial | Logic exists but lacks unit tests. Some agents (DB Architect) use hardcoded responses. |
| **API Gateway** | 🟠 Issue | Frontend bypasses Core API to call Orchestrator directly (Port 8081). |
| **Testing** | 🔴 Critical | **0% coverage** for core business logic. Tests are scattered or purely "smoke" tests. |

### 1.3 Technical Debt
- **`agents/crew-orchestrator/main.py`**:
  - Hardcoded `AGENTS` URLs prevent flexible deployment/testing.
  - Duplicated "Approval Flow" logic.
  - Mocked RAG/Planning prevents real intelligence.
  - WebSocket is an echo server, not connected to the command processor.
- **`agents/dashboard/lib/api.ts`**: Frontend directly calls Orchestrator (TODO: Unify under Core API).
- **`tests/framework/evaluator.py`**: `LLM_EVAL` is unimplemented.

---

## 2. Testing Strategy

We will implement a **Pyramid Testing Strategy**:

1.  **Unit Tests (60%)**:
    -   **Framework**: `pytest` (Backend/Agents), `Vitest` (Frontend).
    -   **Focus**: Individual agent logic, parsing utilities, orchestration state machine.
    -   **Mocking**: Use `unittest.mock` to isolate agents from network/DB.

2.  **Integration Tests (30%)**:
    -   **Framework**: `pytest` + `testcontainers` (or Docker Compose).
    -   **Focus**: Database interactions, Redis messaging, MinIO uploads.
    -   **Critical Path**: Task Creation -> DB Persistence -> Orchestrator Pickup.

3.  **End-to-End (E2E) Tests (10%)**:
    -   **Framework**: `Playwright`.
    -   **Focus**: Full user journey (Dashboard -> Backend -> Agent -> Result).

---

## 3. Implementation Plan (Next Steps)

### Phase 1: Refactoring & Preparation (High Priority)
1.  **Centralize Configuration**: Move hardcoded agent URLs from `orchestrator/main.py` to `config.py` or environment variables.
2.  **Unify API Access**: Update Frontend to use Core API Gateway; create proxy in Backend.
3.  **Consolidate Tests**: Move scattered tests (`tests/`, `agents/shared/tests/`) into a unified `backend/tests/` structure.

### Phase 2: Core Testing Framework
1.  **Configure Pytest**: Create `conftest.py` with fixtures for DB, Redis, and Client.
2.  **Mocking Strategy**: Create shared mocks for LLM responses to avoid API costs during testing.

### Phase 3: Critical Logic Implementation
1.  **Orchestrator Logic**: Replace mocked RAG/Planning with actual calls to `shared/rag_memory.py`.
2.  **Evaluator**: Implement `LLM_EVAL` in `evaluator.py`.

### Phase 4: Test Suite Creation
1.  **Unit**: Write tests for `BaseAgent`, `Orchestrator`, and `TaskParser`.
2.  **Integration**: Test the `Redis` communication layer.
3.  **E2E**: Expand Playwright tests to cover Task Creation flow.
