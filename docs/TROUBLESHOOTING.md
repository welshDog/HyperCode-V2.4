# Troubleshooting Guide

## Common Issues

### 1. "Backend offline?" / Connection Error
**Symptom**: The CLI says it can't connect to `localhost:8000`.
**Fix**:
1.  Check if Docker is running: `docker ps`.
2.  If `hypercode-core` is missing or exited, check logs:
    ```bash
    docker logs hypercode-core
    ```
3.  Ensure port 8000 isn't used by another app.

### 2. Task stuck in "Pending"
**Symptom**: CLI says "Task Queued" but no output file appears.
**Fix**:
1.  Check the worker logs:
    ```bash
    docker logs -f celery-worker
    ```
2.  If you see "Connection refused" to Redis, ensure Redis is up.
3.  If you see "No route found", check `backend/app/agents/router.py` to ensure your task type maps to an agent.

### 3. Pulse Agent says "CRITICAL: Cannot reach Prometheus"
**Symptom**: `hypercode pulse` returns a critical error.
**Fix**:
1.  The Pulse Agent runs *inside* Docker. It tries to reach `http://prometheus:9090`.
2.  Ensure the `prometheus` service is running in `docker-compose.yml`.
3.  Check if they are on the same Docker network (`backend-net`).

### 4. Git Merge Conflicts
**Symptom**: `git status` shows "Unmerged paths".
**Fix**:
1.  Open the file in VS Code.
2.  Look for `<<<<<<< HEAD`.
3.  Choose "Accept Incoming Change" (or whichever is correct).
4.  `git add .`
5.  `git commit`.

### 5. CLI "Missing auth token"
**Symptom**: CLI refuses to run.
**Fix**:
1.  Create a file named `token.txt` in the root directory.
2.  Paste a valid JWT access token from the backend login (or ask a senior dev/admin for one).

### 6. MCP Server Crash Loop / "Invalid Args"
**Symptom**: Docker container `mcp-server` keeps restarting with `clojure.lang.ExceptionInfo: invalid args`.
**Fix**:
1.  The `mcp/docker` image is a CLI tool, not a service.
2.  **Solution**: Remove the `mcp-server` service from `docker-compose.yml`. Use the MCP client configuration in `mcp-config.json` instead.

### 7. Docker Container Name Conflict
**Symptom**: `Error response from daemon: Conflict. The container name "/hypercode-ollama" is already in use`.
**Fix**:
1.  Run `docker rm -f hypercode-ollama` to remove the orphaned container.
2.  Restart the stack: `docker-compose up -d`.

### 8. Dashboard "Unhealthy"
**Symptom**: Dashboard container is Up but marked `(unhealthy)`.
**Fix**:
1.  This is usually a strict health check timeout during the initial build/start.
2.  If the UI is accessible at `http://localhost:8088`, you can ignore this or increase the `start_period` in `docker-compose.yml`.

### 9. Tempo crashes immediately on startup ⭐ NEW
**Symptom**: `tempo` container exits right after starting. Logs show errors like:
```
field not found, node: root, field: kafka
```
or:
```
field not found, node: root, field: ingester.lifecycler
```
**Root Cause**: `grafana/tempo:latest` resolves to v2.10.3+ which has breaking config changes.
**Fix**:
1. Pin Tempo image in `docker-compose.yml`:
   ```yaml
   image: grafana/tempo:2.4.2
   ```
2. Strip deprecated fields (`kafka`, `ingester.lifecycler`) from `tempo/tempo.yaml`.
3. Recreate the container:
   ```powershell
   docker compose up -d --force-recreate tempo
   Start-Sleep 20
   curl http://localhost:3200/ready
   ```
4. Expected response: `ready` ✅

> 📖 See full details in [TEMPO_FIX_GUIDE.md](TEMPO_FIX_GUIDE.md)

### 10. Tempo `/ready` returns "waiting for 15s after being ready"
**Symptom**: Tempo is running but `/ready` says it's not ready yet.
**Fix**: This is **normal behaviour** — not an error! The ingester has a built-in 15-second warm-up buffer after boot. Wait 20 seconds and retry:
```powershell
Start-Sleep 20
curl http://localhost:3200/ready
```
Expected: `ready` ✅
