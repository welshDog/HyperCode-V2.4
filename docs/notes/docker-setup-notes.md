Excellent! Now I'm ready to create the comprehensive report. Let me generate it:

***

# 🚀 Docker Mastery for HyperCode: Complete Developer's Guide
## Executive Summary
Mastering Docker for HyperCode isn't about memorizing commands—it's about **understanding system design principles** that map to your neurodivergent-first approach to code. Docker containerization solves the fundamental "it works on my machine" problem by creating **reproducible, isolated environments** where your code behaves identically whether you're developing locally in Windsurf, running CI/CD tests, or deploying to production.

This guide transforms you from Docker user to Docker architect. You'll learn why Docker decisions matter, how containers actually work under the hood, and how to build a professional DevOps workflow that scales with HyperCode from prototype to production. The focus is on **clarity through structure**—Docker's strength for ADHD-friendly development.

***

## Part 1: Foundation — Understanding Docker's Mental Model
### Why Docker Matters for HyperCode
Docker solves three critical problems for language and IDE projects:

**Problem 1: Environment Consistency.** Your development machine has Python 3.11, Node.js 20, Supabase CLI, and build tools installed. A contributor's machine might have Python 3.10 or Node 18. Docker **freezes the entire environment** into a single image, eliminating the "works for me" excuse. For neurodivergent development workflows where context-switching is taxing, this means **one setup, infinite reliability**. [talent500](https://talent500.com/blog/modern-docker-best-practices-2025/)

**Problem 2: Isolation Without Fragility.** Unlike virtual machines, containers share the host kernel—lightweight, fast, ephemeral. You can spin up 10 HyperCode build environments, run tests in parallel, tear them down instantly. For rapid iteration and hyperfocus sessions, this speed is critical. [docs.docker](https://docs.docker.com/build/building/best-practices/)

**Problem 3: Production Parity.** The Dockerfile you write for local development runs identically in CI/CD and production. Zero surprises. This **deterministic execution** aligns perfectly with ADHD brains that thrive on predictable, structured systems. [techstackdigital](https://techstackdigital.com/blog/top-docker-use-cases-every-software-developer-should-know-in-2025/)

### Docker Architecture: The Three Layers
Think of Docker as three layers:

1. **Image Layer** — The blueprint (like a class definition). Contains OS, dependencies, code. Immutable. Shared across containers.
2. **Container Layer** — Running instance (like an object instantiation). Has writable filesystem, process, network. Ephemeral.
3. **Network/Storage Layer** — How containers talk to each other and persist data. Volumes = managed storage outside container lifecycle.

For HyperCode: Your Dockerfile = Image Layer (build once, run anywhere). `docker-compose.yml` = orchestrating the Container Layer + networks/volumes. This separation of concerns—blueprint vs. runtime—is clean, explicit architecture.

***

## Part 2: Building Production-Grade Images
### The Multi-Stage Build Pattern (Your Secret Weapon)
Multi-stage builds solve image bloat. Most Docker beginners create **fat images** (500MB+) because they bundle build tools (compilers, dev dependencies) into the final image. These tools are only needed during build, not at runtime.

**Pattern: Build → Test → Runtime**
For HyperCode, which likely includes both Python (for language runtime/compiler) and JavaScript/React (for IDE web interface), multi-stage builds are **essential**:

**Example: HyperCode Python + React Multi-Stage Dockerfile**

```dockerfile
# ========================================
# Stage 1: Python Dependencies Builder
# ========================================
FROM python:3.11-slim AS py-builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ========================================
# Stage 2: Node Dependencies Builder  
# ========================================
FROM node:20-alpine AS js-builder

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --only=production

# ========================================
# Stage 3: Production Runtime
# ========================================
FROM python:3.11-slim

WORKDIR /app

# Copy only production Python packages from builder
COPY --from=py-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy only production Node modules from builder
COPY --from=js-builder /build/node_modules ./node_modules

# Copy application code
COPY . .

# Non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

EXPOSE 3000 5000
CMD ["python", "main.py"]
```

**Why this works:**

- **Py-builder stage**: Installs C-heavy packages (like numpy) with build tools, keeps only `.local` wheel files.
- **Js-builder stage**: Node dependencies installed separately, clean npm cache.
- **Final runtime**: Only 2 small layers (Python slim base + production deps). **70% smaller** than if you bundled build tools. [collabnix](https://collabnix.com/docker-multi-stage-builds-for-python-developers-a-complete-guide/)
- **Health check**: Docker automatically restarts unhealthy containers. Catch crashes before users report them. [lumigo](https://lumigo.io/container-monitoring/docker-health-check-a-practical-guide/)

**Layer Caching Strategy** — Docker caches each `RUN` instruction as a layer. Order matters:

```dockerfile
# ❌ WRONG: Code changes invalidate pip cache
COPY . .
RUN pip install -r requirements.txt

# ✅ RIGHT: Pip cache stays valid until requirements.txt changes
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

This alone cuts rebuild time from **5 minutes → 10 seconds** during active development. [docs.benchhub](https://docs.benchhub.co/docs/tutorials/docker/docker-best-practices-2025)

### Base Image Selection: The Foundation
```dockerfile
# ❌ Avoid bloated base images
FROM ubuntu:latest          # 77MB, includes build tools

# ✅ Production
FROM python:3.11-slim       # 125MB, minimal but includes pip
FROM python:3.11-alpine     # 50MB, tiny, uses musl libc (sometimes incompatible)

# ✅ Development
FROM python:3.11            # 900MB, includes build-essentials (OK for dev)
```

**For HyperCode:**
- **Development Dockerfile** (used locally + CI tests): Use `-slim` or full base (speed vs. size tradeoff isn't critical).
- **Production Dockerfile** (deployed image): Use `-alpine` for smallest footprint, or `-slim` if Alpine's libc causes compatibility issues.

Always use **specific version tags**, never `latest`. `latest` breaks reproducibility. [docs.docker](https://docs.docker.com/build/building/best-practices/)

***

## Part 3: Local Development with Windsurf & Dev Containers
### Dev Containers: Your Local Environment Superpower
Windsurf supports **Dev Containers** (OCI container spec). Instead of installing tools locally, Windsurf runs inside a container. Benefits:

- **Clean host**: No Python 3.11 + Node 20 + Supabase CLI cluttering your system.
- **Team consistency**: Every developer runs identical environment.
- **Project isolation**: HyperCode dependencies don't conflict with other projects.
- **One-click onboarding**: New contributor runs `git clone` + opens in Windsurf → Dev Container spins up automatically.

**Setting up Dev Containers for HyperCode**

Create `.devcontainer/devcontainer.json`:

```json
{
  "name": "HyperCode Dev",
  "image": "mcr.microsoft.com/devcontainers/python:3.11-node-20",
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/github-cli:1": {}
  },
  "postCreateCommand": "npm install && pip install -r requirements.txt",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "esbenp.prettier-vscode",
        "GitHub.copilot"
      ]
    }
  },
  "forwardPorts": [3000, 5000],
  "portsAttributes": {
    "3000": {"label": "React IDE", "onAutoForward": "notify"},
    "5000": {"label": "Python API", "onAutoForward": "notify"}
  }
}
```

**How Windsurf uses it:**
1. User opens HyperCode folder in Windsurf.
2. Windsurf detects `.devcontainer/devcontainer.json`.
3. Windsurf asks: "Reopen in Dev Container?" → Click yes.
4. Windsurf connects to container's VS Code Server (running inside container).
5. Terminal commands run in container. Port 3000 auto-forwards to host.

Result: **You edit code locally in Windsurf, but all tooling runs containerized**. [docs.windsurf](https://docs.windsurf.com/windsurf/advanced)

### Local Development Workflow: docker-compose
For active development, use `docker-compose.yml` to orchestrate multiple services:

```yaml
version: "3.9"

services:
  hypercode-api:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    volumes:
      - ./backend:/app       # Mount source for live edits
      - /app/node_modules    # Prevent host node_modules overwriting
    ports:
      - "5000:5000"
    environment:
      - DEBUG=1
      - DATABASE_URL=postgresql://user:pass@postgres:5432/hypercode
    depends_on:
      postgres:
        condition: service_healthy
    command: npm run dev    # Live reload with nodemon/uvicorn

  hypercode-ide:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:5000
    command: npm start

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=hypercode
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres-data:
```

**Key patterns:**

- **Bind mounts** (`./backend:/app`): Code changes on host sync instantly into container. Perfect for rapid iteration.
- **Named volumes** (`postgres-data`): Database persists across container restarts. Dev data doesn't evaporate.
- **Health checks**: `depends_on: service_healthy` ensures API doesn't start until database is ready.
- **docker compose watch** (2025 feature): Auto-rebuilds and restarts services when files change—hands-free development. [talent500](https://talent500.com/blog/modern-docker-best-practices-2025/)

**Running it:**

```bash
# First time: build images, start services
docker compose up

# Subsequent runs: reuse cached images, faster startup
docker compose up

# View logs in real-time
docker compose logs -f hypercode-api

# Execute command in running container
docker exec hypercode-api npm test

# Stop without deleting volumes (data persists)
docker compose stop

# Clean everything (use carefully!)
docker compose down -v
```

***

## Part 4: Networking, Volumes & Data Management
### Docker Networking: Container Communication
By default, containers on the same `docker-compose` network can communicate by **service name** as hostname:

```python
# Inside hypercode-api container
import psycopg2

# Use service name "postgres" instead of localhost
conn = psycopg2.connect("dbname=hypercode user=user password=pass host=postgres")
```

Docker's embedded DNS server resolves `postgres` → container's internal IP (e.g., `172.18.0.2`).

**Network debugging checklist:** [linkedin](https://www.linkedin.com/pulse/debugging-docker-network-issues-practical-checklist-md-yusuf-hasan-ohe6c)

```bash
# 1. Check if containers are on same network
docker network ls
docker network inspect hypercode_default

# 2. Test connectivity
docker exec hypercode-api ping postgres

# 3. Check DNS resolution
docker exec hypercode-api nslookup postgres

# 4. Test specific port
docker exec hypercode-api nc -zv postgres 5432

# 5. Inspect container's network settings
docker inspect hypercode-api | grep -A 20 NetworkSettings

# 6. Use nicolaka/netshoot for advanced debugging
docker run --rm -it --network hypercode_default nicolaka/netshoot
  # Now inside netshoot container, run:
  curl -v http://hypercode-api:5000/health
  tcpdump -i eth0    # Capture network packets
```

**Common issues & fixes:** [codesolutionshub](https://codesolutionshub.com/2025/03/18/how-to-debug-and-fix-docker-container-communication-problems/)

| Problem | Cause | Solution |
|---------|-------|----------|
| "Cannot reach postgres" | Containers on different networks | Add service to same docker-compose file |
| DNS fails for service name | Using default bridge network | Use custom network (docker-compose creates automatically) |
| Port mapping not working | Wrong syntax or internal port mismatch | `ports: ["HOST:CONTAINER"]` not `["CONTAINER:HOST"]` |
| "Address already in use" | Port 5000 already bound on host | `docker ps` to find conflicting container, stop it, or use `ports: ["5001:5000"]` |

### Volumes: Persistent Data & Development Flow
**Three storage mechanisms:**

1. **Named Volumes** — Docker-managed storage (recommended for production).

```bash
docker volume create my-data
docker run -v my-data:/app/data nginx
# Data at /app/data persists even after container deletion
```

2. **Bind Mounts** — Host directory mounted into container (recommended for development).

```bash
docker run -v /home/user/project:/app -w /app node npm install
# Host /home/user/project ↔ Container /app
# Perfect for live code edits
```

3. **Tmpfs** — In-memory filesystem (use for secrets, temporary files).

```bash
docker run --tmpfs /app/secrets:noexec,nosuid,size=100m nginx
# /app/secrets exists only in RAM, wiped on restart
```

**For HyperCode development:**

```yaml
# docker-compose.yml
services:
  hypercode-api:
    volumes:
      # Live code edits
      - ./backend/src:/app/src
      
      # Exclude node_modules to avoid sync slowdown
      - /app/node_modules
      
      # Database for development (persistent)
      - hypercode-dev-db:/app/data
      
      # Secrets from .env (secure, not in git)
      - ./.env:/app/.env:ro

volumes:
  hypercode-dev-db:
```

**Volume best practices:** [dev](https://dev.to/mayankcse/managing-data-in-docker-understanding-volumes-for-persistence-49i6)

- Use named volumes for stateful data (databases, caches).
- Use bind mounts for development code (enables live edit).
- Use tmpfs for secrets and sensitive files (RAM-only, never hits disk).
- Always backup named volumes: `docker run -v my-data:/data alpine tar czf - /data > backup.tar.gz`.
- Clean up unused volumes: `docker volume prune`.

***

## Part 5: Secrets & Environment Variables (Security Foundation)
### The Secret Handling Hierarchy
**❌ Never do this:**

```dockerfile
# DANGER: Secret hardcoded in image layer, forever in registry
FROM ubuntu
RUN curl -H "Authorization: Bearer sk_live_abc123xyz" https://api.example.com
```

Attackers can extract this from image layers. Once pushed, it's **impossible to remove**—the hash is permanent.

**❌ Avoid this:**

```yaml
# Plain environment variables visible to anyone with docker inspect
environment:
  - DATABASE_PASSWORD=supersecret
  - API_KEY=sk_live_abc123xyz
```

**Password visible:** `docker inspect my-container | grep -i password`

**✅ Correct approaches:** [blog.gitguardian](https://blog.gitguardian.com/how-to-handle-secrets-in-docker/)

**1. BuildKit Secrets** — For build-time secrets (package authentication):

```dockerfile
# Dockerfile
FROM node:20
RUN --mount=type=secret,id=npm_token \
    echo "//npm.pkg.github.com/:_authToken=$(cat /run/secrets/npm_token)" > .npmrc && \
    npm ci && \
    rm .npmrc

# Build command
docker build --secret npm_token=/home/user/.npm_token .
# Secret not baked into image layer!
```

**2. File-Based Secret Mounts** — For runtime secrets (production):

```yaml
# docker-compose.yml
services:
  hypercode-api:
    image: hypercode:prod
    secrets:
      - db_password
      - api_key
    environment:
      # App reads from /run/secrets/ (RAM-backed tmpfs)
      - DB_PASSWORD_FILE=/run/secrets/db_password

secrets:
  db_password:
    file: /secure/db_password.txt  # Permissions: 600
  api_key:
    file: /secure/api_key.txt
```

**App code reads securely:**

```python
# app.py
with open("/run/secrets/db_password", "r") as f:
    db_password = f.read().strip()
# File never loaded into environment, safe from process inspection
```

**3. Docker Secrets** — For Swarm deployments:

```bash
# Create secret from file
docker secret create db_password /secure/db_password.txt

# Use in service
docker service create \
  --secret db_password \
  --env DB_PASSWORD_FILE=/run/secrets/db_password \
  hypercode:prod
```

Secrets encrypted in transit and at rest in Swarm manager. [docs.docker](https://docs.docker.com/engine/swarm/secrets/)

**4. External Secret Managers** — For enterprise:

- **HashiCorp Vault**, **AWS Secrets Manager**, **Azure Key Vault**: Applications fetch secrets at runtime.
- Not covered here, but understand this is the gold standard for multi-environment deployments.

**For HyperCode development/staging:**

```bash
# Create .env file (NOT in git)
cat > .env.local << EOF
DATABASE_URL=postgresql://user:pass@postgres:5432/hypercode
API_KEY=sk_test_123456
DEBUG=1
EOF

# Load via .env file (docker-compose native support)
docker compose --env-file .env.local up
```

***

## Part 6: Resource Management & Performance
### CPU & Memory Limits
Running containers without limits is dangerous. A single memory leak or runaway loop crashes your entire host. [oneuptime](https://oneuptime.com/blog/post/2026-01-16-docker-limit-cpu-memory/view)

**Memory limits:**

```bash
# Hard limit: container killed if exceeds 1GB
docker run -m 1g my-app

# Soft limit + hard limit: try 512MB, allow up to 1GB under pressure
docker run -m 1g --memory-reservation 512m my-app

# docker-compose
services:
  hypercode-api:
    image: hypercode:prod
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

**CPU limits:**

```bash
# Limit to 1.5 CPUs (can use 150% of one core or 75% of two cores)
docker run --cpus 1.5 my-app

# Relative weight (default 1024)
docker run --cpu-shares 512 background-task    # Gets half CPU vs default
docker run --cpu-shares 2048 high-priority-app # Gets double CPU vs default

# Pin to specific cores (for NUMA systems or isolation)
docker run --cpuset-cpus "0,1" my-app   # Use cores 0 and 1 only

# docker-compose
services:
  hypercode-api:
    deploy:
      resources:
        limits:
          cpus: "1.5"
          memory: 2G
        reservations:
          cpus: "1"
          memory: 1G
```

**For HyperCode development stack:**

```yaml
services:
  hypercode-api:
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G
        reservations:
          cpus: "1"
          memory: 1G

  hypercode-ide:
    deploy:
      resources:
        limits:
          cpus: "1"
          memory: 1G

  postgres:
    deploy:
      resources:
        limits:
          cpus: "1"
          memory: 1G
        reservations:
          cpus: "0.5"
          memory: 512M
```

**Monitoring resource usage:**

```bash
# Real-time container stats
docker stats

# Specific container
docker stats hypercode-api --no-stream

# Output: CPU%, MEM usage/limit, network I/O, block I/O
```

***

## Part 7: Health Checks & Observability
### Health Checks: Let Docker Heal Itself
Health checks tell Docker: "Is this container actually working?"

```dockerfile
# Dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

# Explanation:
# --interval=30s: Run check every 30 seconds
# --timeout=5s: Allow 5 seconds for check to complete
# --retries=3: Mark unhealthy after 3 consecutive failures
# CMD: Execute command in running container
```

**Health check states:** [lumigo](https://lumigo.io/container-monitoring/docker-health-check-a-practical-guide/)

- `starting` — Container initialized, health checks not started yet.
- `healthy` — Health check passed.
- `unhealthy` — Health check failed. Docker can auto-restart.

**Health check endpoints for HyperCode:**

```python
# Flask/FastAPI
@app.get("/health")
def health():
    """Readiness check: Can you handle requests?"""
    try:
        # Check database
        db.execute("SELECT 1")
        # Check critical dependencies
        return {"status": "healthy", "db": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503

@app.get("/live")
def liveness():
    """Liveness check: Are you alive?"""
    return {"status": "alive"}
```

**Dockerfile:**

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1
```

**docker-compose:**

```yaml
services:
  hypercode-api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 40s  # Wait 40s before first check (startup time)

  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5
```

**Automatic restart on unhealthy:**

```yaml
services:
  hypercode-api:
    restart: on-failure:5  # Restart max 5 times if health check fails
```

**Monitoring health:**

```bash
# Check current health status
docker inspect --format='{{json .State.Health}}' hypercode-api | jq

# Output: {"Status":"healthy","FailingStreak":0,"Recurrences":10}

# View health check events
docker events --filter 'type=container' --filter 'action=health_status'
```

***

## Part 8: CI/CD Pipeline with GitHub Actions & Docker Buildx
### GitHub Actions: Automate Building & Testing
Multi-platform builds (x86_64, ARM64 for Apple Silicon) require **Docker Buildx**. GitHub Actions automates this:

```yaml
# .github/workflows/build.yml
name: Docker Build & Push

on:
  push:
    branches: [main]
    tags: ["v*"]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Extract Metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: |
            ${{ secrets.DOCKERHUB_USERNAME }}/hypercode
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build & Push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          platforms: linux/amd64,linux/arm64
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**What this does:** [github](https://github.com/docker/build-push-action)

1. On push to `main` → Build images for x86_64 + ARM64.
2. On PR → Build images (don't push).
3. On tag `v1.0.0` → Tag as `hypercode:v1.0.0` + `hypercode:1.0` + `hypercode:latest`.
4. Cache layers in GitHub Actions cache → subsequent builds **80% faster**. [github](https://github.com/docker/build-push-action)

***

## Part 9: Production Deployment Checklist
Before pushing HyperCode to production, verify:

**Image & Security:**

- [ ] Non-root user in Dockerfile: `USER appuser`
- [ ] Health checks defined and tested
- [ ] Secrets injected via files, not environment variables
- [ ] `.dockerignore` excludes `.git`, `node_modules`, `.env`, etc.
- [ ] Base images from official registries, pinned to specific versions
- [ ] Image scanned for vulnerabilities: `docker scout cves hypercode:latest`

**Networking & Data:**

- [ ] All services use named networks (not default bridge)
- [ ] Volumes for stateful data (databases, caches)
- [ ] Health checks for all services
- [ ] Resource limits and reservations set

**Observability:**

- [ ] Structured logging (JSON format for parsing)
- [ ] Health check endpoints tested manually
- [ ] Resource monitoring in place (CPU, memory, disk, network)

**Deployment:**

- [ ] docker-compose.yml or Kubernetes manifests versioned
- [ ] Environment-specific configs (.env.prod, .env.staging)
- [ ] Rollback strategy tested (can you revert to previous version?)
- [ ] Zero-downtime deployment possible (load balancer + rolling updates)

***

## Part 10: Advanced Patterns for HyperCode Scale
### Multi-Repo Orchestration (As HyperCode Grows)
As HyperCode separates into `hypercode-language` (compiler), `hypercode-ide` (web interface), `hypercode-runtime` (executor), consider:

```yaml
# docker-compose.prod.yml
version: "3.9"

services:
  # Frontend IDE
  ide:
    image: hypercode-ide:${VERSION}
    deploy:
      resources:
        limits: {cpus: "1", memory: "1G"}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]

  # Compiler API
  compiler:
    image: hypercode-language:${VERSION}
    deploy:
      replicas: 3  # Scale compiler across 3 instances
      resources:
        limits: {cpus: "2", memory: "2G"}

  # Code execution engine
  executor:
    image: hypercode-runtime:${VERSION}
    privileged: true  # Required for sandboxing user code
    deploy:
      replicas: 5

  # Message queue for async jobs
  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

  # Database
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password
    volumes:
      - pg-data:/var/lib/postgresql/data

volumes:
  redis-data:
  pg-data:

secrets:
  db_password:
    file: /secure/db_password.txt
```

### Observability Stack (As Maturity Increases)
```yaml
# Add monitoring as HyperCode matures
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"  # Avoid conflict with IDE on 3000
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}

  loki:
    image: grafana/loki:latest
    volumes:
      - ./loki-config.yml:/etc/loki/local-config.yml

  # Wire up HyperCode services to export metrics
  compiler:
    image: hypercode-language:${VERSION}
    environment:
      - PROMETHEUS_PORT=9090
      - LOG_FORMAT=json  # For Loki parsing
```

***

## Your Next Steps: From Theory to Practice
**Week 1: Foundation**
- Set up `.devcontainer/devcontainer.json` for HyperCode repo.
- Create `docker-compose.yml` with local dev setup (IDE + API + database).
- Run `docker compose up` and verify Windsurf Dev Container workflow.

**Week 2: Production Image**
- Build multi-stage Dockerfile for both frontend and backend.
- Test image locally: `docker build -t hypercode:test . && docker run -it hypercode:test`.
- Verify image runs identical to `docker compose up`.

**Week 3: CI/CD**
- Set up GitHub Actions workflow (build on push, push to registry on tag).
- Validate images build in parallel for multi-platform (x86_64 + ARM64).

**Week 4: Production Hardening**
- Add health checks, resource limits, secrets management.
- Test Docker image security scan.
- Document deployment procedure.

***

## Key Takeaways (Your Brain's Cliff Notes)
| Concept | Why It Matters | For HyperCode |
|---------|---|---|
| **Multi-stage builds** | 70% smaller images, faster deploys | Separate Python + Node compilation from runtime |
| **Dev Containers** | Consistent environment, no "works on my machine" | Windsurf + HyperCode dev = identical for all contributors |
| **Volumes** | Persistent data survives container restarts | Database development data doesn't evaporate |
| **Secrets** | Credentials never leak in image layers | API keys, database passwords secure and injectable |
| **Health checks** | Docker auto-restarts broken containers | Catch crashes before users notice |
| **Resource limits** | Prevent runaway processes crashing host | Fair CPU/memory allocation in multi-service setup |
| **docker-compose watch** | Live reload without manual restarts | Hyperfocus-friendly: edit code, browser auto-refreshes |

***

## Resources & Documentation
- **Official Docker Docs**: https://docs.docker.com (authoritative, bookmark it) [docs.docker](https://docs.docker.com/build/building/best-practices/)
- **Multi-Stage Builds Guide**: https://docs.docker.com/build/building/multi-stage/ [docs.docker](https://docs.docker.com/get-started/docker-concepts/building-images/multi-stage-builds/)
- **Windsurf Dev Containers**: https://docs.windsurf.com/windsurf/advanced [docs.windsurf](https://docs.windsurf.com/windsurf/advanced)
- **Docker Best Practices 2025**: Modern production patterns, security hardening [talent500](https://talent500.com/blog/modern-docker-best-practices-2025/)
- **Debugging Commands Cheat Sheet**: nicolaka/netshoot for network troubleshooting [codesolutionshub](https://codesolutionshub.com/2025/03/18/how-to-debug-and-fix-docker-container-communication-problems/)

***

**You're now equipped to build, deploy, and scale HyperCode with Docker confidence.** The system is yours to master. 🚀
