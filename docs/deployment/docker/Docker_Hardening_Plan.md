# Docker Hardening Implementation Plan

## 1. Executive Summary
This plan outlines the hardening measures to be applied to the HyperCode V2.0 Docker infrastructure. The goal is to enhance security, stability, and resource management without compromising existing functionality. We will integrate production-grade configurations into the existing `docker-compose.yml`, preserving the current network segmentation and service architecture while applying the security controls recommended in `next2.md`.

## 2. Hardening Measures

### 2.1 Security Context & Capabilities
*   **Measure**: Apply `security_opt: ["no-new-privileges:true"]` to all containers.
    *   **Justification**: Prevents processes inside the container from gaining additional privileges via `setuid` or `setgid` binaries.
*   **Measure**: Apply `cap_drop: ["ALL"]` to Agent containers.
    *   **Justification**: Adheres to the principle of least privilege by removing all Linux capabilities. Specific capabilities (like `NET_BIND_SERVICE`) will be added back only if strictly necessary.
    *   **Exceptions**: `devops-engineer` previously mounted the Docker socket. This mount will be removed to eliminate the risk of host privilege escalation, as per the hardening guide.

### 2.2 Resource Management
*   **Measure**: Define `deploy.resources.limits` and `reservations` for all services.
    *   **Configuration**:
        *   **Agents**: Limit 0.5 CPUs, 512MB RAM. Reserve 0.25 CPUs, 256MB RAM.
        *   **Core**: Limit 1.0 CPUs, 1GB RAM. Reserve 0.5 CPUs, 512MB RAM.
        *   **Databases**: Limit 1.0 CPUs, 1GB RAM.
    *   **Justification**: Prevents "noisy neighbor" scenarios where one runaway agent consumes all host resources, ensuring system stability.

### 2.3 Network Security
*   **Measure**: Bind internal service ports to localhost (`127.0.0.1`) only.
    *   **Services**: Postgres (5432), Redis (6379), Prometheus (9090), Grafana (3000), Ollama (11434).
    *   **Justification**: Prevents accidental exposure of administrative and data services to the external network. Access remains available via the internal Docker networks (`backend-net`, `data-net`).
*   **Measure**: Preserve Network Segmentation.
    *   **Strategy**: Maintain `frontend-net`, `backend-net`, and `data-net` isolation. Agents remain on `backend-net` and `data-net` but are isolated from `frontend-net` (direct user access).

### 2.4 Observability & Reliability
*   **Measure**: Implement `healthcheck` blocks for all services.
    *   **Strategy**: Use service-specific checks (e.g., `redis-cli ping`, `pg_isready`, `curl localhost/health`).
    *   **Justification**: Enables Docker to automatically restart unhealthy containers and ensures dependent services wait for readiness (via `depends_on: condition: service_healthy`).
*   **Measure**: Configure Log Rotation.
    *   **Configuration**: `driver: "json-file"`, `options: { max-size: "10m", max-file: "3" }`.
    *   **Justification**: Prevents container logs from consuming all available disk space on the host.

### 2.5 Data Protection
*   **Measure**: Automated Backup Script (`backup_hypercode.sh`).
    *   **Function**: Daily dumps of PostgreSQL (schema + data) and Redis (RDB snapshots).
    *   **Retention**: 7-day rolling retention policy.

## 3. Implementation Steps

1.  **Backup**: Archive current `docker-compose.yml`.
2.  **Refactor**: Modify `docker-compose.yml` to inject hardening configurations into existing services.
3.  **Scripting**: Generate `backup_hypercode.sh` with execution permissions.
4.  **Verification**:
    *   Validate syntax: `docker compose config`
    *   Verify capabilities: `docker inspect [container] --format '{{.HostConfig.CapDrop}}'`
    *   Verify logging: `docker inspect [container] --format '{{.HostConfig.LogConfig}}'`

## 4. Verification Test Cases

| Test Case | Command | Expected Result |
|-----------|---------|-----------------|
| **Privilege Escalation** | `docker exec [agent] whoami` | Should run as configured user (usually root inside, but restricted privileges) |
| **Capability Drop** | `docker inspect [agent] | grep CapDrop` | Should show `["ALL"]` |
| **Port Binding** | `netstat -ano | findstr 6379` | Should listen on `127.0.0.1` only |
| **Resource Limits** | `docker stats --no-stream` | Should show configured Limits |
| **Log Rotation** | Inspect `docker-compose config` | Should show `max-size: 10m` |

