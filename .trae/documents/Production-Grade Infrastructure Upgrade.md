# Production-Grade Enhancement Plan 🚀

We will implement a comprehensive upgrade to HyperCode V2.0, focusing on observability, reliability, and security automation.

## 1. Continuous Load Monitoring (GitHub Actions)
**Agent**: `devops-engineer`
- **Workflow**: Create `.github/workflows/performance.yml`.
- **Logic**:
    1.  Boot `hypercode-core` & Redis services.
    2.  Install `locust`.
    3.  Execute `locust -f tests/load/locustfile.py` in headless mode.
    4.  **Threshold Enforcement**: Parse results; Fail build if `Avg Response > 200ms` or `Fail Rate > 1%`.
    5.  **Artifacts**: Upload HTML/CSV reports.

## 2. End-to-End Testing (CI Integration)
**Agent**: `qa-test-engineer`
- **Workflow**: Update `.github/workflows/ci-js.yml`.
- **Logic**:
    1.  Install Playwright Browsers (`npx playwright install --with-deps`).
    2.  Boot Full Stack (`docker-compose up -d`).
    3.  Run `npm run test:e2e` (Playwright).
    4.  **Artifacts**: Upload `playwright-report` (Traces/Videos) on failure.

## 3. Production Monitoring Stack
**Agent**: `backend-architect` & `frontend-craftsman`
- **Backend (`hypercode-core`)**:
    -   Install `prometheus-fastapi-instrumentator` & `sentry-sdk`.
    -   Initialize Sentry & Prometheus in `main.py`.
    -   Implement **Structured Logging** (JSON) in `app/core/logging.py`.
- **Frontend (`broski-terminal`)**:
    -   Install `@sentry/nextjs`.
    -   Configure `sentry.client.config.js` and `sentry.server.config.js`.
- **Infrastructure**:
    -   Verify `docker-compose.monitoring.yml` works with the instrumented app.

## 4. Zero-Downtime API Key Rotation
**Agent**: `security-auditor`
- **Architecture**: Move from single Env Var to **Redis-backed Key Store**.
- **Implementation**:
    -   Create `app/services/key_manager.py`.
    -   Update `app/core/auth.py` to validate against Redis Set (`api_keys:valid`).
    -   **Migration**: On startup, if Redis is empty, seed it with `env.API_KEY` (backward compatibility).
- **Endpoints**:
    -   `POST /admin/keys` (Generate new key).
    -   `DELETE /admin/keys/{key_id}` (Revoke key).
- **Runbook**: Document the rotation procedure (Generate New -> Distribute -> Revoke Old).

## Execution Order
1.  **Monitoring Core**: Instrument Backend (Prometheus/Sentry/Logging).
2.  **Key Rotation**: Implement Redis-based Auth.
3.  **CI/CD**: Create Performance & E2E Workflows.
