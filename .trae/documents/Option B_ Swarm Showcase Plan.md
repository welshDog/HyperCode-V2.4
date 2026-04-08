# Option B: Swarm Showcase Implementation Plan

## 1. Load Test Suite (QA/Performance)
**Goal:** Simulate 50 concurrent agents with specific request mix and SLAs.
- **Action:** Create a **K6** load test script.
    - **File:** `tests/load/swarm_load_test.js`
    - **Logic:**
        - **Stages:** Ramp up (30s) -> Stay (10m) -> Ramp down (10s).
        - **Scenarios:**
            - `submit_task` (70%): POST `/api/v1/execution/execute`
            - `query_status` (20%): GET `/api/v1/execution/{id}`
            - `kill_agent` (10%): DELETE `/api/v1/agents/{id}` (simulated)
        - **Thresholds (SLAs):**
            - `http_req_duration`: p(95) < 500
            - `http_req_failed`: rate < 0.01
- **Reporting:** Script will output summary to stdout.

## 2. Distributed Tracing (Backend/DevOps)
**Goal:** End-to-end tracing with OpenTelemetry and Jaeger.
- **Infrastructure:**
    - **Modify:** `docker-compose.monitoring.yml` to add `jaeger` service (all-in-one).
    - **Config:** Expose ports 16686 (UI) and 4317 (OTLP gRPC).
- **Backend Instrumentation (`hypercode-core`):**
    - **Dependencies:** Add `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `opentelemetry-instrumentation-fastapi`.
    - **Code:** Update `main.py` to initialize `OpenTelemetryInstrumentator`.
- **Agent Instrumentation (`coder-agent`):**
    - **Dependencies:** Add `opentelemetry-distro` to `agents/coder/requirements.txt`.
    - **Code:** Update `agents/coder/main.py` to propagate trace context in MCP and API calls.

## 3. CI/CD Automation (DevOps)
**Goal:** Automate testing, deployment, and verification.
- **Workflow:** Create `.github/workflows/swarm-pipeline.yml`.
    - **Triggers:** Push to `main`, PRs.
    - **Jobs:**
        1.  **Build & Test:** Run unit tests, linting, SAST (Bandit/Trivy).
        2.  **Deploy Staging:** Build Docker images, push (mock), and deploy to staging (mock `kubectl apply`).
        3.  **Load Test:** Run the K6 script against staging.
        4.  **Production Gate:** Manual approval step.
        5.  **Rollback:** Job to revert changes if smoke tests fail.

## Execution Order
1.  **Infrastructure:** Add Jaeger to docker-compose.
2.  **Backend:** Instrument Core with OpenTelemetry.
3.  **Load Test:** Create K6 script.
4.  **CI/CD:** Create GitHub workflow.
