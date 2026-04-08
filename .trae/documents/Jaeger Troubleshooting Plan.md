# Jaeger Troubleshooting Plan

## 1. Verify Service Status
*   **Command:** `docker compose -f docker-compose.monitoring.yml ps`
*   **Goal:** Determine if the container is running, exited, or never started.

## 2. Port Availability Check
*   **Command:** `netstat -ano | findstr 16686` (Windows)
*   **Goal:** Confirm if the port is actively listening and identify any conflicts.

## 3. Log Analysis
*   **Command:** `docker compose -f docker-compose.monitoring.yml logs jaeger`
*   **Goal:** Capture startup errors or crash logs.

## 4. Remediation
*   **Scenario A (Not Started):** Run `docker compose -f docker-compose.monitoring.yml up -d jaeger`.
*   **Scenario B (Port Conflict):** Identify the conflicting process and terminate it, or reconfigure Jaeger's port mapping.
*   **Scenario C (Config Error):** Validate the `docker-compose.monitoring.yml` syntax.

## 5. Verification
*   **Action:** `curl -v http://localhost:16686`
*   **Success Criteria:** HTTP 200 OK response.
