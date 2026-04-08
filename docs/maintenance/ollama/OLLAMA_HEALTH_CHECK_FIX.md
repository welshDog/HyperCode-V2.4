# 🛠️ Ollama Health Check Fix Guide

## Problem
The `ollama/ollama:latest` Docker image is a minimal image that does **not** contain standard HTTP clients like `curl` or `wget`.
The original health check failed because it tried to execute `wget`, resulting in an `unhealthy` status even though the service was running perfectly.

## The Solution: TCP Handshake
We replaced the HTTP-based check with a native Bash TCP connection test. This verifies that the service is listening on port `11434` without requiring external tools.

### Code Change in `docker-compose.yml`

**Old (Failing):**
```yaml
healthcheck:
  test: ["CMD-SHELL", "wget -qO- http://localhost:11434/api/tags || exit 1"]
```

**New (Working):**
```yaml
healthcheck:
  test: ["CMD-SHELL", "bash -c 'cat < /dev/null > /dev/tcp/localhost/11434'"]
```

## How It Works
1. `bash -c`: Runs a bash command.
2. `/dev/tcp/localhost/11434`: Bash's special built-in file for TCP connections.
3. `cat < /dev/null > ...`: Attempts to open a connection to the host and port.
   - If successful (port open), it returns exit code 0 (Healthy).
   - If failed (port closed), it returns a non-zero exit code (Unhealthy).

## Verification
Run the following command to verify status:
```bash
docker compose ps ollama
```
**Expected Output:** `Up ... (healthy)`
