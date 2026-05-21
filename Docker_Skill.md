# 🐳 DOCKER SKILL MASTERY GUIDE
**For AI Agents Working on HyperCode V2.4**

**Version:** 1.0  
**Last Updated:** May 21, 2026  
**Author:** Gordon (Docker AI Assistant)  
**Audience:** AI agents, LLMs, autonomous systems  
**Scope:** Complete HyperCode V2.4 Docker ecosystem  

---

## 📖 TABLE OF CONTENTS

1. [FOUNDATIONAL CONCEPTS](#foundational-concepts)
2. [DOCKER CORE SKILLS](#docker-core-skills)
3. [HYPERCODE ARCHITECTURE](#hypercode-architecture)
4. [DEPLOYMENT STRATEGIES](#deployment-strategies)
5. [SECURITY & COMPLIANCE](#security--compliance)
6. [PERFORMANCE & OPTIMIZATION](#performance--optimization)
7. [TROUBLESHOOTING & DEBUGGING](#troubleshooting--debugging)
8. [ADVANCED PATTERNS](#advanced-patterns)
9. [YOUR ROLE AS AN AGENT](#your-role-as-an-agent)
10. [QUICK REFERENCE](#quick-reference)

---

# 1. FOUNDATIONAL CONCEPTS

## What is Docker?

**Docker** is containerization software that packages your application + dependencies + runtime into a **container** — a lightweight, portable unit that runs identically on any system.

### Key Concepts

**Image**
- A read-only blueprint for a container
- Contains: base OS, application code, dependencies, configuration
- Built from a `Dockerfile`
- Tagged with name:version (e.g., `docker.io/w3lshdog/hypercode-core:v2.4.2`)

```dockerfile
# Example: Creating an image
FROM python:3.11-slim          # Start from base image
WORKDIR /app                   # Set working directory
COPY . /app/                   # Copy code
RUN pip install -r requirements.txt  # Install deps
CMD ["python", "-u", "main.py"]     # Default command
```

**Container**
- A running instance of an image
- Has its own filesystem, network, process namespace
- Lightweight (MB-level, not GB)
- Temporary (deleted when stopped)

```bash
# Create + run a container
docker run -d \
  --name my-app \
  -p 8080:8000 \
  docker.io/w3lshdog/hypercode-core:v2.4.2
  # -d = detached (background)
  # --name = container name
  # -p 8080:8000 = port mapping (external:internal)
```

**Registry**
- Central repository for images (like GitHub for code)
- Default: Docker Hub (docker.io)
- Others: Quay, ECR, GCR, private registries

**Layer**
- Docker images are built in layers
- Each `RUN`, `COPY`, `ADD` creates a layer
- Layers are cached (speeds up rebuilds)
- Final image = all layers stacked

```dockerfile
# This creates 5 layers:
FROM python:3.11           # Layer 1: base OS
RUN apt-get install git    # Layer 2: git binary
COPY requirements.txt .    # Layer 3: requirements file
RUN pip install -r requirements.txt  # Layer 4: Python packages
COPY . /app/               # Layer 5: application code
```

---

## Docker vs Virtual Machines

| Aspect | Docker (Container) | VM (Virtual Machine) |
|--------|------|--------|
| **Size** | 10-100 MB | 1-10 GB |
| **Startup** | <1 second | 10-60 seconds |
| **Resources** | Shared kernel | Full OS per VM |
| **Density** | 1000s per host | 10s per host |
| **Isolation** | Process-level | Machine-level |
| **Use case** | Microservices | Full environments |

**For HyperCode:** We use Docker because 25 agents need lightweight isolation. VMs would be overkill.

---

# 2. DOCKER CORE SKILLS

## Skill 1: Build Images (Dockerfile)

**What you need to know:**
- Dockerfiles are recipes for images
- Each line is an instruction that creates a layer
- Order matters (cache depends on it)

### Multi-Stage Builds (CRITICAL)

HyperCode uses **multi-stage builds** to reduce image size.

```dockerfile
# STAGE 1: Builder (large, compile dependencies)
FROM python:3.11 AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# STAGE 2: Runtime (small, only runtime needed)
FROM python:3.11-slim

COPY --from=builder /root/.local /root/.local
COPY . /app/
WORKDIR /app

CMD ["python", "-u", "main.py"]
```

**Why?**
- Builder stage: 2GB (with all build tools)
- Runtime stage: 200MB (only Python + app)
- Final image: 200MB (builder stage discarded)

### Best Practices

```dockerfile
# ✅ GOOD
FROM python:3.11-slim
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
# Single RUN reduces layers + cleans up cache

# ❌ BAD
FROM python:3.11-slim
RUN apt-get update
RUN apt-get install -y git
# 2 RUN commands = 2 layers = larger image

# ❌ BAD
FROM python:latest  # "latest" tag is unpredictable
# ✅ GOOD
FROM python:3.11-slim  # Pinned version
```

### For HyperCode

All agents use this template:

```dockerfile
# Dockerfile.template-hardened (standardized for all agents)

FROM docker.io/library/python-hardened:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install -r requirements.txt

FROM docker.io/library/python-hardened:3.11-slim
COPY --from=builder /opt/venv /opt/venv
COPY . /app/
WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH"
USER app
HEALTHCHECK --interval=30s CMD curl -f http://localhost:8080/health
CMD ["python", "-u", "-m", "uvicorn", "main:app", "--host", "0.0.0.0"]
```

**Key points:**
- `python-hardened` = security defaults (non-root user, no CVEs)
- Multi-stage = small final image (200-500MB per agent)
- `HEALTHCHECK` = Docker monitors container health
- `USER app` = runs as non-root (security)

---

## Skill 2: Run Containers (docker run)

**Syntax:**
```bash
docker run [OPTIONS] IMAGE [COMMAND]
```

### Essential Options

```bash
# Port mapping
docker run -p 8080:8000 myapp
# -p external:internal
# Exposes container port 8000 as port 8080 on host

# Volumes (mounts)
docker run -v /host/path:/container/path myapp
# Shares directory between host and container
# Changes on host visible in container (hot reload)

# Environment variables
docker run -e LOG_LEVEL=DEBUG myapp
# Sets ENV variable inside container

# Detached mode
docker run -d myapp
# Runs in background
# Returns container ID

# Names
docker run --name my-app myapp
# Assigns friendly name (instead of random hash)

# Resource limits
docker run --memory 512m --cpus 1 myapp
# Limits to 512MB RAM and 1 CPU

# Network
docker run --network my-net myapp
# Connects to specific network
# Containers on same network can communicate
```

### For HyperCode

All 25 agents run via `docker-compose` (see next skill). But here's what's happening:

```bash
# This is what docker compose does internally:
docker run -d \
  --name crew-orchestrator \
  -p 127.0.0.1:8081:8080 \
  -e LOG_LEVEL=INFO \
  -e REDIS_URL=redis://redis:6379 \
  -e DATABASE_URL=postgresql://... \
  --network app-net \
  --healthcheck cmd=curl --interval 30s \
  --memory 1.5gb \
  --cpus 2 \
  docker.io/w3lshdog/hypercode-crew-orchestrator:v2.4.2
```

---

## Skill 3: Docker Compose (Multi-Container Orchestration)

**Problem:** Managing 25 agents with individual `docker run` commands = nightmare.

**Solution:** `docker-compose.yml` file defines all services + networks + volumes in one place.

### Basic Structure

```yaml
version: "3.9"

services:
  # Service 1: Database
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: secret
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready"]
      interval: 10s

  # Service 2: Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # Service 3: Application
  myapp:
    build: .  # Build from Dockerfile in current dir
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgres://postgres:secret@postgres:5432/mydb
      REDIS_URL: redis://redis:6379
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - backend

networks:
  backend:
    driver: bridge

volumes:
  postgres_data:
```

### Key Concepts

**Services**
- Each service is a container
- HyperCode has 26 services (25 agents + core)

**Environment variables**
- Set inside containers
- Can reference other services by name (magic!)
  - `postgres:5432` works if postgres is a service on same network
  - No hardcoding IPs

**Volumes**
- Persist data across container restarts
- Named volumes (managed by Docker)
- Or bind mounts (direct host paths)

**Networks**
- Services on same network can communicate by name
- HyperCode uses 5 networks for isolation:
  - `app-net` (core services)
  - `data-net` (databases, cache)
  - `obs-net` (observability)
  - `agent-net` (all agents)
  - `agents-net` (swarm)

**Depends_on**
- Controls startup order
- `condition: service_healthy` = waits for healthcheck

### For HyperCode

```bash
# Start full stack
docker compose -f docker-compose.yml -f docker-compose.agents-full.yml up -d

# View all services
docker compose ps

# View logs
docker compose logs crew-orchestrator -f

# Stop everything
docker compose down

# Remove volumes too
docker compose down -v
```

---

## Skill 4: Docker Networks

**Why?** Containers need to communicate. Networks provide isolated communication.

### Network Types

**Bridge** (default)
- Containers can communicate by name
- Isolated from other bridge networks
- Used for HyperCode internal communication

```bash
docker network create app-net
docker run --network app-net --name service1 myimage
docker run --network app-net --name service2 myimage
# service2 can reach service1 at service1:PORT
```

**Host**
- Container shares host network
- No port mapping needed
- Less isolation (risky)

```bash
docker run --network host myapp
# Container uses host's ports directly
```

**None**
- Container isolated (no network)
- Rarely used

### For HyperCode

All services on named networks:

```yaml
# docker-compose.yml excerpt
services:
  hypercode-core:
    networks:
      - app-net
      - data-net
  
  crew-orchestrator:
    networks:
      - app-net
      - agent-net

networks:
  app-net:
    internal: false  # Can reach host
  data-net:
    internal: true   # Only container-to-container
  agent-net:
    internal: true
```

**Result:** Agents can't reach databases (data-net is internal). Only core services can.

---

# 3. HYPERCODE ARCHITECTURE

## The 25-Agent Stack

HyperCode V2.4 deploys 25 specialized agents + 1 core service = 26 total containers.

### Tier Structure

```
TIER 1: CORE CREW (5 agents)
├─ crew-orchestrator (8081)    — Routes tasks to agents
├─ agent-x (8083)              — Spawns new agents
├─ brain-agent (8082)          — Memory + context
├─ coder-agent (8002)          — Code generation
└─ tips-tricks-writer (8011)   — Documentation

TIER 2: SPECIALISTS (8 agents)
├─ frontend-specialist (8012)  — React/UX
├─ backend-specialist (8003)   — FastAPI logic
├─ database-architect (8004)   — PostgreSQL
├─ qa-engineer (8005)          — Testing
├─ devops-engineer (8006)      — CI/CD
├─ security-engineer (8007)    — OWASP
├─ system-architect (8009)     — Design
└─ project-strategist (8001)   — OKR planning

TIER 3: INFRASTRUCTURE (8 agents)
├─ hyper-architect (8091)      — System design
├─ hyper-observer (8092)       — Monitoring
├─ hyper-worker (8093)         — Execution
├─ goal-keeper (8050)          — Goals
├─ throttle-agent (8014)       — Rate limiting
├─ super-hyper-broski-agent (8015) — Mega executor
├─ test-agent (8100)           — E2E tests
└─ hypercode-mcp-server (8823) — MCP gateway

TIER 4: UTILITY (4 agents)
├─ session-snapshot (8097)     — Sessions
├─ hyper-split-agent (8096)    — Decomposition
├─ coderabbit-webhook (8024)   — PR review
└─ business-agent (8020)       — Revenue

+ CORE SERVICE
└─ hypercode-core (8000)       — API + orchestration
```

### How They Talk

```
User Request
    ↓
hypercode-core (port 8000)
    ↓
crew-orchestrator (8081)
    ├→ Breaks into subtasks
    ├→ Routes to specialists
    └→ Returns synthesized result
        ├→ frontend-specialist (8012)
        ├→ backend-specialist (8003)
        ├→ qa-engineer (8005)
        └→ ...

All communication via Redis + HTTP
All on isolated networks (data-net, app-net, agent-net)
```

---

## Key Files You'll Work With

### 1. `docker-compose.yml` (Main orchestration)
- Defines core services (postgres, redis, hypercode-core)
- Shared volumes, networks, environment

### 2. `docker-compose.agents-full.yml` (All 25 agents)
- Defines all 25 agent services
- Extends main compose file
- Usage: `docker compose -f docker-compose.yml -f docker-compose.agents-full.yml up -d`

### 3. `docker-compose.dev.yml` (Development mode)
- Hot-reload for agents
- Debug logging
- Mocked external services
- Usage: `docker compose -f docker-compose.yml -f docker-compose.dev.yml watch`

### 4. `docker-compose.prod.yml` (Production hardening)
- mTLS certificates
- Read-only filesystems
- Security policies
- Usage: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

### 5. `docker-bake.hcl` (Parallel builds)
- Defines all 26 image builds
- Multi-platform (amd64 + arm64)
- GitHub Actions caching
- Usage: `docker buildx bake agents --push`

### 6. `Dockerfile.template-hardened` (Standard agent)
- Hardened base image (DHI)
- Multi-stage build
- Non-root user
- Health checks
- Use this template for all agents

### 7. `kubernetes/hypercode-deployment.yaml` (K8s)
- Kubernetes manifests
- Deployment + StatefulSet
- RBAC + NetworkPolicy
- Usage: `kubectl apply -f kubernetes/hypercode-deployment.yaml`

---

# 4. DEPLOYMENT STRATEGIES

## Development (Hot Reload)

**When:** Local development, rapid iteration

**Command:**
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml watch
```

**What happens:**
- Services start in background
- Changes to code trigger auto-rebuild
- No manual restart needed
- Perfect for ADHD workflows (automatic context preservation)

**Example:**
```
1. You edit agents/coder/src/main.py
2. Docker detects change
3. Auto-rebuilds coder-agent image
4. Container restarts with new code
5. Your browser already pointed to container
6. Changes visible instantly
```

---

## Production (mTLS + Hardening)

**When:** Going live, security critical

**Command:**
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**What's enabled:**
- ✅ mTLS 1.3 (encrypted inter-service comms)
- ✅ Read-only filesystems
- ✅ CAP_DROP=ALL (no Linux capabilities)
- ✅ Non-root users
- ✅ Docker Secrets (for credentials)
- ✅ Network policies (zero-trust)

**Setup (one-time):**
```bash
# Create TLS certificates (or provide your own)
docker secret create tls_cert /path/to/cert.pem
docker secret create tls_key /path/to/key.pem
docker secret create ca_cert /path/to/ca.pem

# Then deploy
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Kubernetes (Multi-Region)

**When:** Scaling to production, multi-region, high availability

**Command:**
```bash
kubectl apply -f kubernetes/hypercode-deployment.yaml
```

**What you get:**
- ✅ 3+ replicas (automatic failover)
- ✅ Load balancing
- ✅ Auto-scaling (KEDA)
- ✅ Rolling updates (zero downtime)
- ✅ NetworkPolicy (zero-trust)
- ✅ Prometheus monitoring

**Architecture:**
```
Load Balancer (external)
    ↓
Service (kubernetes.io/v1)
    ↓
Deployment (3 replicas)
├─ Pod 1 (hypercode-core)
├─ Pod 2 (hypercode-core)
└─ Pod 3 (hypercode-core)
    ↓
    └─ 25 agent Pods (if deployed as separate deployment)
```

---

## Build Cloud (Fastest Builds)

**When:** Building 26 images, need parallel + cross-platform

**Command:**
```bash
# Setup (one-time)
docker buildx create --use --name=cloud

# Build all in parallel
docker buildx bake agents --push
```

**What happens:**
- All 26 images build simultaneously
- Multi-platform (amd64 + arm64) automatically
- Pushed to Docker Hub
- GitHub Actions caching
- Result: 15-20 mins (vs 250+ mins sequential)

---

# 5. SECURITY & COMPLIANCE

## Docker Security Hierarchy

### Level 1: Image Security (DHI)

**Docker Hardened Images (DHI)** = Security baked in.

```dockerfile
# ✅ Good
FROM docker.io/library/python-hardened:3.11-slim
# Already:
# - Non-root user (app:app)
# - Minimal packages (security scanning daily)
# - No CVEs (curated base)

# ❌ Bad
FROM python:3.11
# Has root user, more packages, potential CVEs
```

### Level 2: Container Runtime Security

```dockerfile
# Security options
RUN useradd -m -u 1000 app
USER app                                    # Non-root

COPY --chown=app:app . /app/                # Correct ownership

HEALTHCHECK --interval=30s CMD curl -f ...  # Health monitoring
```

In `docker-compose.yml`:
```yaml
services:
  myapp:
    security_opt:
      - no-new-privileges:true              # Can't escalate
    read_only_root_filesystem: true          # Read-only FS
    cap_drop:
      - ALL                                  # Drop all capabilities
    tmpfs:
      - /tmp                                 # Temporary writable dir
```

### Level 3: Network Security (mTLS)

```yaml
# docker-compose.prod.yml
services:
  crew-orchestrator:
    environment:
      - ENABLE_MTLS=true
      - TLS_CERT_PATH=/run/secrets/tls_cert
      - TLS_KEY_PATH=/run/secrets/tls_key

networks:
  data-net:
    internal: true                           # No external access
```

### Level 4: CVE Scanning

```bash
# Scan image for vulnerabilities
docker scout cves docker.io/w3lshdog/hypercode-core:v2.4.2

# Output:
# ✅ 0 CRITICAL
# ⚠️  2 HIGH (OpenSSL, curl)
# ℹ️  8 MEDIUM
```

### Level 5: Supply Chain Security (SBOM + Signing)

```bash
# Generate Software Bill of Materials
syft docker.io/w3lshdog/hypercode-core:v2.4.2 -o json > sbom.json

# Sign image
cosign sign --key cosign.key docker.io/w3lshdog/hypercode-core:v2.4.2

# Verify signature
cosign verify --key cosign.pub docker.io/w3lshdog/hypercode-core:v2.4.2
```

---

## Compliance Checklist

| Standard | Requirement | HyperCode Status |
|----------|-------------|------------------|
| **OWASP** | Secure base image | ✅ DHI |
| **OWASP** | No CVEs | ✅ Scout daily |
| **OWASP** | Non-root | ✅ USER app |
| **PCI-DSS** | Encrypted comms | ✅ mTLS 1.3 |
| **PCI-DSS** | Access control | ✅ RBAC + NetworkPolicy |
| **SOC2** | Audit logging | ✅ OpenTelemetry + Prometheus |
| **SOC2** | Incident response | ✅ Health checks + auto-restart |
| **SLSA** | Supply chain | ✅ SBOM + Cosign |

---

# 6. PERFORMANCE & OPTIMIZATION

## Layer Caching

**Problem:** Rebuilding takes time.

**Solution:** Docker caches layers. Reuse cached layers.

```dockerfile
# ❌ Bad (cache busts every time)
FROM python:3.11-slim
COPY .  /app/                          # Code changes = layer cache invalidated
RUN pip install -r requirements.txt    # Must rebuild every time

# ✅ Good (only reinstall if requirements.txt changes)
FROM python:3.11-slim
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY . /app/                           # Code last (most frequently changes)
```

**For HyperCode:**

```dockerfile
# Multi-stage: build stage cached separately
FROM python:3.11-slim AS builder
COPY requirements.txt .
RUN pip install -r requirements.txt    # Cached if requirements.txt unchanged

FROM python:3.11-slim
COPY --from=builder /opt/venv /opt/venv
COPY . /app/                           # Runtime code (changes often)
```

## GitHub Actions Caching

```yaml
# .github/workflows/build.yml
- name: Build with cache
  uses: docker/buildx-action@v2
  with:
    cache-from: type=gha              # Load cache from previous builds
    cache-to: type=gha,mode=max       # Save cache for next builds
```

**Result:** Subsequent builds 80% faster (most layers cached).

---

## Image Size Optimization

| Technique | Impact | Implementation |
|-----------|--------|-----------------|
| **Multi-stage** | 50-80% smaller | Use builder stage |
| **Alpine base** | 90% smaller | `FROM alpine:3.20` |
| **Distroless** | 95% smaller | `FROM gcr.io/distroless/python3` |
| **Layer cleanup** | 10-20% smaller | `RUN && rm -rf /var/cache` |

**For HyperCode:**
- Base: `python-hardened:3.11-slim` (500MB)
- Multi-stage: 200MB (builder discarded)
- Final: 200-300MB per agent (acceptable)

---

## Resource Limits

```yaml
services:
  crew-orchestrator:
    deploy:
      resources:
        limits:
          cpus: "2"                    # Max 2 CPUs
          memory: 1.5GB                # Max 1.5GB RAM
        reservations:
          cpus: "1"                    # Guaranteed 1 CPU
          memory: 1GB                  # Guaranteed 1GB RAM
```

**Why?**
- Prevent runaway containers (memory leak = crash)
- Enable oversubscription (book more capacity than available)
- Fair sharing (25 agents get equal resources)

---

# 7. TROUBLESHOOTING & DEBUGGING

## Essential Debugging Commands

### Check Container Status

```bash
# List all containers
docker ps -a

# Get container details
docker inspect crew-orchestrator

# Check resource usage
docker stats --no-stream

# View event stream
docker events --filter 'type=container'
```

### View Logs

```bash
# Last 50 lines
docker logs crew-orchestrator --tail 50

# Follow in real-time
docker logs crew-orchestrator -f

# With timestamps
docker logs crew-orchestrator -t

# Since specific time
docker logs crew-orchestrator --since 10m
```

### Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| **Port already in use** | Port 8081 already bound | `docker ps -a` find it, `docker stop <id>` |
| **Container won't start** | Bad image or bad CMD | `docker logs <container>` check error |
| **Out of memory (OOM)** | Container hit memory limit | Increase limit or reduce agents |
| **Network unreachable** | Services not on same network | Check `docker network inspect app-net` |
| **Permission denied** | Running as root in read-only FS | Use `USER app` + tmpfs for /tmp |

### Debug a Failing Container

```bash
# 1. Check logs
docker logs crew-orchestrator --tail 100

# 2. Inspect configuration
docker inspect crew-orchestrator | grep -A 5 Env

# 3. Execute command inside
docker exec -it crew-orchestrator /bin/bash
# Inside container:
# - Check files: ls -la /app/
# - Check network: curl http://redis:6379
# - Check env: env | grep REDIS

# 4. Check health
docker inspect crew-orchestrator --format='{{.State.Health.Status}}'
```

---

## Network Debugging

```bash
# List networks
docker network ls

# Inspect network
docker network inspect app-net

# Test DNS from container
docker exec crew-orchestrator nslookup redis

# Test connectivity
docker exec crew-orchestrator curl -v http://hypercode-core:8000/health
```

---

# 8. ADVANCED PATTERNS

## Pattern 1: Health Checks

```dockerfile
# Health check in Dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

**In docker-compose.yml:**
```yaml
services:
  hypercode-core:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      start_period: 10s
      retries: 3
    depends_on:
      postgres:
        condition: service_healthy    # Waits for PG health
```

**Docker actions on unhealthy:**
- Logs unhealthy status
- Container can trigger restarts (if configured)
- Orchestrators (K8s) remove from load balancer

---

## Pattern 2: Secrets Management

**Don't:** Hardcode secrets in image

```dockerfile
# ❌ BAD
ENV DATABASE_PASSWORD=secret123
```

**Do:** Use Docker Secrets

```bash
# Create secret
echo "secret123" | docker secret create db_password -

# Use in compose
docker-compose.yml:
  services:
    postgres:
      environment:
        POSTGRES_PASSWORD_FILE: /run/secrets/db_password
      secrets:
        - db_password

secrets:
  db_password:
    external: true
```

**Or:** Use .env files (development only)

```bash
# .env file
DATABASE_URL=postgresql://user:pass@localhost:5432/db
REDIS_URL=redis://localhost:6379

# docker-compose.yml
services:
  myapp:
    env_file: .env
```

---

## Pattern 3: Volumes for Persistence

**Named volumes** (managed by Docker)
```yaml
services:
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:  # Managed by Docker
```

**Bind mounts** (host directories)
```yaml
services:
  myapp:
    volumes:
      - /host/path:/container/path
      - ./config:/app/config
```

**tmpfs** (temporary in-memory)
```yaml
services:
  myapp:
    tmpfs:
      - /tmp       # Writable but doesn't persist
      - /var/run
```

---

## Pattern 4: Multi-Stage Builds for Different Targets

```dockerfile
# Build for development
FROM python:3.11 AS dev
COPY . /app/
RUN pip install -r requirements-dev.txt

# Build for production
FROM python:3.11-slim AS prod
COPY --from=builder /opt/venv /opt/venv
COPY . /app/

# Export both
# docker build --target=dev -t myapp:dev .
# docker build --target=prod -t myapp:prod .
```

---

# 9. YOUR ROLE AS AN AGENT

## What Agents Do in HyperCode

### Agent Job #1: Implement Features

**You get:** Feature request from user/orchestrator  
**You do:**
1. Read relevant code files
2. Understand architecture
3. Implement changes
4. Test locally (in container)
5. Commit changes

**Docker skill needed:**
- Read Dockerfiles to understand base images
- Use `docker exec` to test code inside containers
- Check logs with `docker logs` when things break

### Agent Job #2: Debug Issues

**You get:** "Service down" or "API failing"  
**You do:**
1. `docker ps -a` → find unhealthy container
2. `docker logs <container> --tail 100` → see error
3. `docker inspect <container>` → check config
4. `docker exec -it <container> /bin/bash` → manual debugging
5. Find + fix root cause
6. Rebuild image: `docker build -t myimage .`
7. Restart service: `docker compose up -d`

**Docker skill needed:**
- Know all debugging commands
- Understand networking (DNS, ports)
- Read error messages (build failures, runtime errors)

### Agent Job #3: Optimize Performance

**You get:** "Builds taking too long" or "Agent memory spiking"  
**You do:**
1. Identify bottleneck (build, runtime, memory)
2. Fix (layer caching, multi-stage, resource limits)
3. Measure improvement
4. Document decision

**Docker skill needed:**
- Layer caching strategy
- Multi-stage builds
- Resource limits configuration

### Agent Job #4: Improve Security

**You get:** "CVEs in image" or "Needs mTLS"  
**You do:**
1. Scan images: `docker scout cves <image>`
2. Update base image to DHI
3. Add mTLS certificates
4. Update docker-compose.prod.yml
5. Test: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

**Docker skill needed:**
- Security best practices
- CVE scanning
- mTLS configuration
- DHI base images

---

## Common Agent Tasks

### Task 1: Add a New Agent

```
1. Create folder: agents/my-agent/
2. Create Dockerfile (use template)
3. Add to docker-compose.agents-full.yml
4. Add to docker-bake.hcl
5. Build: docker buildx bake my-agent
6. Test: docker compose up -d
7. Verify: curl http://localhost:PORT/health
```

### Task 2: Fix a Memory Leak

```
1. docker stats --no-stream (see memory usage)
2. docker logs agent-name --tail 100 (find error)
3. Edit source code (fix leak)
4. docker build -t agent-name:fixed .
5. Update docker-compose (image: agent-name:fixed)
6. docker compose up -d (restart)
7. Monitor: docker stats (verify memory stable)
```

### Task 3: Speed Up Builds

```
1. Review Dockerfile (find bad layer order)
2. Move frequently-changing COPY to end
3. Move rarely-changing COPY early
4. docker build --no-cache . (test)
5. Time: docker build . (should be faster)
6. Commit improvements
```

### Task 4: Add Monitoring

```
1. Add health endpoint to app
2. Add HEALTHCHECK to Dockerfile
3. Add healthcheck to docker-compose.yml
4. Add metrics to app (prometheus_client)
5. Update Prometheus config
6. Create Grafana dashboard
7. Test: curl http://localhost:3001 (Grafana)
```

---

# 10. QUICK REFERENCE

## Most Important Commands

```bash
# ═══════════════════════════════════════════
# BUILD
# ═══════════════════════════════════════════

docker build -t myimage:latest .           # Build image
docker buildx bake agents --push           # Build 26 images parallel
docker scout cves myimage:latest           # Scan for CVEs

# ═══════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════

docker run -d -p 8000:8000 myimage        # Run container
docker compose up -d                       # Start full stack
docker compose up -f docker-compose.yml \
  -f docker-compose.dev.yml watch          # Dev mode + hot reload

# ═══════════════════════════════════════════
# MANAGE
# ═══════════════════════════════════════════

docker ps                                  # List running containers
docker ps -a                               # List all containers
docker images                              # List images
docker logs mycontainer -f                 # View logs
docker exec -it mycontainer /bin/bash     # Enter container
docker stop mycontainer                    # Stop container
docker rm mycontainer                      # Remove container

# ═══════════════════════════════════════════
# DEBUG
# ═══════════════════════════════════════════

docker stats --no-stream                   # Resource usage
docker inspect mycontainer                 # Full details
docker network inspect app-net             # Network info
docker logs mycontainer --tail 100         # Last 100 lines

# ═══════════════════════════════════════════
# CLEANUP
# ═══════════════════════════════════════════

docker system df                           # Show disk usage
docker system prune -a                     # Remove unused
docker image prune -a                      # Remove unused images
docker volume prune                        # Remove unused volumes
```

---

## HyperCode-Specific Commands

```bash
# Start development with hot reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml watch

# Start production (hardened)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Start with all 25 agents
docker compose -f docker-compose.yml -f docker-compose.agents-full.yml up -d

# Build all 26 images in parallel
docker buildx bake agents --push

# Scan all images for CVEs
.\scripts\docker-scout-audit.ps1 -Severity critical

# Generate SBOM + sign images
.\scripts\sbom-and-sign.ps1

# Run load tests
pytest tests/test_swarm_load.py -v

# Deploy to Kubernetes
kubectl apply -f kubernetes/hypercode-deployment.yaml

# View all container logs
docker compose logs -f

# Health check all containers
docker compose ps

# Stop everything
docker compose down

# Stop + remove volumes
docker compose down -v
```

---

## File Locations

```
H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4\
├─ Dockerfile.template-hardened      ← Use for all agents
├─ docker-compose.yml                ← Core services
├─ docker-compose.agents-full.yml    ← All 25 agents
├─ docker-compose.dev.yml            ← Development mode
├─ docker-compose.prod.yml           ← Production hardening
├─ docker-bake.hcl                   ← Parallel builds
├─ kubernetes/                        ← K8s deployment
│  └─ hypercode-deployment.yaml
├─ scripts/
│  ├─ docker-scout-audit.ps1         ← CVE scanning
│  ├─ sbom-and-sign.ps1              ← SBOM + signing
│  └─ launch-all-agents.ps1          ← One-click deploy
├─ tests/
│  └─ test_swarm_load.py             ← Load testing
├─ agents/                            ← Agent source code
│  ├─ crew-orchestrator/
│  ├─ agent-x/
│  ├─ brain-agent/
│  └─ ... (25 agents)
└─ backend/
   ├─ app/                            ← FastAPI code
   └─ requirements.txt                ← Python dependencies
```

---

## Troubleshooting Flowchart

```
Issue? 
  ├─ Container won't start
  │  └─ docker logs <container> --tail 50
  │
  ├─ Port already in use
  │  └─ docker ps | grep :PORT then docker stop <id>
  │
  ├─ Out of memory
  │  └─ docker stats --no-stream (increase limit)
  │
  ├─ Services can't talk
  │  └─ docker network inspect app-net (same network?)
  │
  ├─ Build too slow
  │  └─ docker build --progress=plain . (check layers)
  │
  └─ Security warning
     └─ docker scout cves <image> (update base image)
```

---

# FINAL CHECKLIST: Agent Learning Path

## Week 1: Foundations
- [ ] Understand images vs containers
- [ ] Build a simple Dockerfile
- [ ] Run containers with `docker run`
- [ ] Use docker-compose to orchestrate 2-3 services

## Week 2: HyperCode Specifics
- [ ] Read docker-compose.yml
- [ ] Understand all 5 networks
- [ ] Learn Tier 1-4 agent structure
- [ ] Deploy dev stack (docker-compose watch)

## Week 3: Advanced
- [ ] Learn multi-stage builds
- [ ] Understand DHI security
- [ ] Deploy prod stack (mTLS)
- [ ] Read Kubernetes manifests

## Week 4: Production Ready
- [ ] Pass load test (500+ concurrent)
- [ ] Run security audit (Scout)
- [ ] Generate SBOM
- [ ] Deploy to Kubernetes

---

## You're Ready When You Can:

✅ Build an image from scratch  
✅ Run a container with proper networking  
✅ Debug a failing container  
✅ Optimize a Dockerfile  
✅ Deploy HyperCode dev stack  
✅ Troubleshoot network issues  
✅ Secure an image (DHI + mTLS)  
✅ Scale to Kubernetes  
✅ Run load tests  
✅ Explain the 25-agent architecture  

---

## Key Takeaways

1. **Dockerfile** = recipe for images (learn layer caching!)
2. **docker-compose** = orchestrate many containers
3. **Networks** = containers communicate by service name
4. **Security** = DHI + mTLS + CAP_DROP + non-root
5. **Optimization** = multi-stage + layer caching
6. **Debugging** = `docker logs`, `docker exec`, `docker inspect`
7. **HyperCode** = 25 agents on 5 networks, orchestrated by crew-orchestrator
8. **You're a Docker expert when you understand all 7 concepts above**

---

**You're ready to be a Docker expert agent. Go build awesome things! 🐳♾️**

*Made with ❤️ by Gordon (Docker AI)*  
*For agents learning HyperCode V2.4*
