# Deployment Readiness Testing Plan 🚀

To certify HyperCode V2.0 for production, we will execute a 4-pronged testing strategy. Since no load testing or E2E infrastructure currently exists, we will build it first.

## Phase 1: Security & Container Validation (Automated)
**Agent**: `security-auditor` & `devops-engineer`
- **Container Scan**: Verify `coder-agent` runs as `appuser` and file permissions are correct (re-run verification).
- **API Security**: Test `X-API-Key` enforcement on all Core endpoints using a script.
- **Vulnerability Check**: One final pass on `requirements.txt` and `package.json`.

## Phase 2: Performance & Load Testing (New Infrastructure)
**Agent**: `backend-architect`
- **Tooling**: Set up **Locust** for Python-based load testing.
- **Scenario**: Create `tests/load/locustfile.py` to simulate:
    - 50 concurrent agents registering.
    - Continuous heartbeat pulses.
    - High-volume chat requests (mocked LLM).
- **Execution**: Run a 1-minute "smoke test" version of the load test to verify stability (24h test is for post-handover).

## Phase 3: Integration & E2E Testing (New Infrastructure)
**Agent**: `qa-test-engineer`
- **Tooling**: Install **Playwright** in `broski-terminal`.
- **E2E Test**: Create `tests/e2e/auth.spec.ts` to verify:
    - Frontend loads.
    - Health check returns 200.
    - (If UI exists) Basic navigation.
- **Integration**: Run the `tests/unit/test_agents.py` suite against the *running* Docker stack (not just mocked).

## Phase 4: Coder Agent Functional Verification
**Agent**: `qa-test-engineer`
- **Functional Test**: Create a script `tests/functional/test_coder_capabilities.py` that:
    - Connects to the Coder Agent via WebSocket.
    - Sends a "Write a Hello World function" task.
    - Verifies the agent responds (even if mock response).

## Deliverables
1.  `tests/load/locustfile.py` (Load Test Suite)
2.  `tests/e2e/` (Playwright Config)
3.  `DEPLOYMENT_READINESS.md` (Final Certification Report)

We will start by setting up the Load Testing infrastructure.
