# Jaeger Troubleshooting & Fix Plan

## 1. Verify Trace Generation
*   **Action:** Run `curl http://localhost:8000/health` to generate a request.
*   **Check:** Query `http://localhost:16686/api/services`.
    *   *Expectation:* If empty, traces aren't reaching Jaeger.

## 2. Fix `hypercode-core` Instrumentation
*   **Problem:** Previous analysis suggests `hypercode-core/main.py` might be missing imports or configuration for OTLP.
*   **Action:** Review and patch `THE HYPERCODE/hypercode-core/main.py`.
    *   Ensure `FastAPIInstrumentator` and OTLP exporters are correctly imported and initialized.
    *   Ensure the endpoint points to `http://jaeger:4317`.

## 3. Fix `coder-agent` Instrumentation
*   **Problem:** Similar configuration check for `agents/coder/main.py`.
*   **Action:** Verify OTLP setup in the agent code.

## 4. Restart & Verify
*   **Action:** Rebuild and restart services.
    ```bash
    docker compose up -d --build hypercode-core coder-agent
    ```
*   **Verification:**
    1.  Generate traffic (curl health check).
    2.  Check Jaeger UI for "hypercode-core" service.
    3.  Confirm the "parameter 'service' is required" error resolves (as services will now exist).
