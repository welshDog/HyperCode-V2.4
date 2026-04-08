System Health Check Report (HyperCode V2.0)
 BROski > Overall Status: AMBER (core is up; several supporting subsystems are degraded)

- Spec note: this for Agent first.md is currently empty (0 lines). Health-check behavior was derived from QUICK_REFERENCE.md , docker-compose.yml , docker-compose.mcp-gateway.yml , and comprehensive_health_check.py .
What’s Locked In

- hypercode-core: healthy; GET http://localhost:8000/health -> 200 (body: {"status":"ok","service":"hypercode-core","version":"2.0.0","environment":"production"} ).
- crew-orchestrator: healthy; GET http://localhost:8081/health -> 200 (body: {"status":"ok","service":"crew-orchestrator"} ).
- dashboard: healthy; GET http://localhost:8088/ -> 200.
- postgres + redis: healthy; redis-cli ping -> PONG, pg_isready -> accepting connections.
- prometheus/grafana/tempo/minio: responding and healthy on their exposed endpoints.
What’s Not Locked In (Degraded / Down)

- celery-worker: exited (255) and not auto-restarting (no restart: configured in docker-compose.yml ); celery-exporter is stuck in Created because it depends on celery-worker health.
- broski-bot: crash-looping (restarting) due to invalid Discord token (401 Unauthorized / “Improper token has been passed.”).
- MCP gateway/tooling stack (from docker-compose.mcp-gateway.yml ):
  - mcp-gateway: restarting and not serving http://localhost:8820/health (connection fails); container “health” is failing because the image lacks curl .
  - mcp-postgres: appears “Up” with port mapping, but does not accept connections on localhost:3002 (connection fails).
  - mcp-filesystem: repeatedly restarting; logs repeatedly print “running on stdio”.
  - mcp-github: exited (EOF / “client is closing: EOF”).
  - chroma (MCP profile): running but marked unhealthy (healthcheck failing due to missing curl inside container), and no host port is published (so host-side checks fail).
  - ollama (MCP profile): serving http://localhost:11434/api/tags but marked unhealthy (healthcheck uses curl which is not in the image).
- Potential service collision risk: both stacks declare container_name: chroma ; the MCP profile’s chroma container name conflicts with the main stack’s chroma service name in docker-compose.yml , which can block the intended “core” ChromaDB from coming up.
Performance Snapshot (docker stats, current)

- Highest CPU: cadvisor ~47% CPU, ~802 MiB memory (watch this; it can starve smaller services on constrained machines).
- Prometheus: ~484 MiB memory, ~6–7% CPU.
- hypercode-core: ~161 MiB / 1 GiB limit (~16%), low CPU.
- dashboard: ~55 MiB / 512 MiB limit (~11%), moderate CPU spikes observed (~12% at sample time).
Endpoint Latency Snapshot (host-side curl)

- hypercode-core /health : 200, ~228 ms
- crew-orchestrator /health : 200, ~78 ms
- dashboard / : 200, ~248 ms
- grafana /api/health : 200, ~11 ms
- prometheus /-/healthy : 200, ~24 ms
- minio /minio/health/live : 200, ~207 ms
- mcp-gateway /health : connection failed (000)
- chroma (expected on host): connection failed (000) to localhost:8009 (no published port on the running chroma container)
Error Log Highlights

- broski-bot: Discord auth failure loop: 401 Unauthorized -> discord.errors.LoginFailure: Improper token has been passed.
- mcp-gateway / chroma / ollama healthchecks: failing because curl binary is missing in those images (healthcheck “OCI runtime exec failed: exec: curl: not found”).
- mcp-github: server sessions immediately disconnect (EOF), then exits.
Dependency Health

- Redis: OK (PONG)
- PostgreSQL: OK (accepting connections)
- Core API: OK
- Orchestrator API: OK
- Grafana internal DB: OK (per /api/health )
- Celery pipeline: NOT OK (worker down; exporter blocked)
Top 3 Critical Issues (Immediate Attention)

- P0 — Celery worker is down (job processing halted)
  
  - Evidence: celery-worker is Exited (255) ; not OOMKilled; no restart policy; celery-exporter remains Created .
  - Impact: background jobs/queues won’t run; anything async (agent jobs, scheduled tasks) will silently stall.
  - Fix:
    - Add restart: unless-stopped to celery-worker in docker-compose.yml .
    - Restart worker and confirm healthcheck passes ( celery inspect ping inside container healthcheck).
    - After worker is healthy, confirm celery-exporter transitions to running.
- P0 — MCP Gateway profile is miswired (gateway not reachable; tool services unstable; “healthy” signals are misleading)
  
  - Evidence:
    - http://localhost:8820/health fails; container healthchecks fail because curl is missing.
    - mcp-github exits with EOF; mcp-postgres publishes a port but doesn’t accept HTTP connections; mcp-filesystem loops printing “stdio”.
    - mcp-gateway logs show it’s running in “stdio server” mode and reporting “No server is enabled” / “0 tools listed”.
  - Impact: agents relying on MCP gateway/toolchain won’t get governed tool access; the whole “central tool access control” layer is effectively down.
  - Fix:
    - Update docker-compose.mcp-gateway.yml to align transport expectations:
      - Either run MCP components in a mode that actually serves HTTP on the exposed ports, or remove exposed ports and treat them as stdio-attached processes (invoked by a parent MCP host).
      - Replace healthchecks that require curl with a tool that exists in-image (or install curl in a derived image).
      - Ensure tools are actually enabled/discovered (right now “No server is enabled / 0 tools listed”).
    - Re-verify: curl.exe http://localhost:8820/health returns 200 and tools list is non-empty.
- P1 — broski-bot crash-looping (invalid DISCORD_TOKEN)
  
  - Evidence: repeated 401 Unauthorized; “Improper token has been passed.”
  - Impact: Discord automation/alerts/moderation features are down; log noise; wasted restarts.
  - Fix:
    - Set a valid DISCORD_TOKEN (and any required guild variables) in your environment/.env used by Compose, then restart only broski-bot .
    - If Discord integration is optional in this environment, gate it behind a Compose profile so it doesn’t run (and fail) by default.
Supporting Notes

- Disk pressure risk: docker system df shows ~57.4 GB images with ~45.7 GB reclaimable. If the host disk is tight, this becomes a cascading failure vector (builds fail, volumes can’t grow, DBs corrupt).
- Service naming collisions: avoid duplicate container_name values across compose files (notably chroma , and potential ollama ) to prevent “wrong service is running” scenarios when stacking compose overlays.
