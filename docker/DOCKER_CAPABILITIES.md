# Docker Capabilities for HyperCode Project

This document outlines all Docker capabilities and tooling available for the HyperCode project.

## 🐳 Docker Compose Configurations

### 1. **docker-compose.yml** - Main Production Stack
- Full HyperCode platform with all services
- Redis, PostgreSQL, Ollama
- All 8 specialist agents
- Monitoring with Prometheus, Grafana, Jaeger
- Dashboard UI

**Usage:**
```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

### 2. **docker-compose.dev.yml** - Development Environment
- Hot-reload enabled for all services
- Source code mounted as volumes
- Debug ports exposed (Python debugger)
- Development tools (Redis Commander, pgAdmin, Mailhog)
- Local reverse proxy
- Live documentation server
- No persistence (faster iteration)

**Usage:**
```bash
docker-compose -f docker-compose.dev.yml up
```

**Included Dev Tools:**
- **Redis Commander** (port 8081) - Redis GUI
- **pgAdmin** (port 5050) - PostgreSQL GUI
- **Mailhog** (port 8025) - Email testing
- **Docs Server** (port 8888) - Live documentation

### 3. **docker-compose.agents.yml** - Agent-Only Stack
- Lightweight agent crew setup
- Orchestrator + 8 specialist agents
- Redis and PostgreSQL
- Agent dashboard
- Resource-constrained for development

**Usage:**
```bash
docker-compose -f docker-compose.agents.yml up -d
```

### 4. **docker-compose.monitoring.yml** - Monitoring Stack
- Prometheus + Grafana
- Alertmanager
- Node Exporter
- cAdvisor
- Redis Exporter
- Blackbox Exporter
- Jaeger tracing

**Usage:**
```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

### 5. Other Compose Variants (current)
This repo includes additional compose variants for specific environments and partial stacks:
- `docker-compose.agents-lite.yml`
- `docker-compose.hyper-agents.yml`
- `docker-compose.mcp-gateway.yml`
- `docker-compose.hyperhealth.yml`
- `docker-compose.external-net.yml`
- `docker-compose.secrets.yml`
- `docker-compose.windows.yml`
- `docker-compose.grafana-cloud.yml`
- `docker-compose.demo.yml`
- `docker-compose.nano.yml` / `docker-compose.nim.yml`

CI/CD runs via GitHub Actions workflows in `.github/workflows/` (not via a dedicated `docker-compose.ci.yml` in this repo).

## 🏗️ Specialized Dockerfiles

### 1. **Dockerfile.builder** - Multi-Purpose Builder
Multi-stage builder for various purposes:
- **base**: Common dependencies
- **development**: Dev tools (pytest, black, ruff, mypy)
- **testing**: Test frameworks and tools
- **ci**: CI/CD specific tools
- **docs**: Documentation builder (mkdocs)
- **migration**: Database migration tools

**Usage:**
```bash
# Build dev environment
docker build --target development -t hypercode-dev -f Dockerfile.builder .

# Build test runner
docker build --target testing -t hypercode-test -f Dockerfile.builder .

# Build docs
docker build --target docs -t hypercode-docs -f Dockerfile.builder .
```

### 2. **docker-bake.hcl** - BuildKit Bake
Efficient multi-platform builds for all services:
- Build all images in parallel
- Multi-architecture (amd64, arm64)
- Consistent labeling and tagging
- Version management

**Usage:**
```bash
# Build everything
docker buildx bake

# Build specific group
docker buildx bake agents
docker buildx bake infrastructure
docker buildx bake monitoring

# Build for production with version
REGISTRY=myregistry.com VERSION=v2.0.0 docker buildx bake --push

# Multi-platform build
docker buildx bake --platform linux/amd64,linux/arm64
```

## 🛠️ Management Scripts

### 1. **docker-health-monitor.sh** - Health Monitoring
Comprehensive health monitoring:
- Container status checks
- Health check verification
- Restart count monitoring
- Resource usage tracking
- Alert webhook integration
- Watch mode for continuous monitoring

**Usage:**
```bash
# Single check
./scripts/docker-health-monitor.sh

# Watch mode
./scripts/docker-health-monitor.sh docker-compose.yml hypercode --watch

# With alerts
ALERT_WEBHOOK=https://hooks.slack.com/xxx ./scripts/docker-health-monitor.sh
```

### 2. **docker-cleanup.sh** - Resource Cleanup
Safe cleanup of Docker resources:
- Remove stopped containers
- Remove dangling images
- Remove unused volumes
- Clean build cache
- Remove unused networks
- Remove old image versions
- Deep clean option
- HyperCode-specific cleanup

**Usage:**
```bash
# Standard cleanup
./scripts/docker-cleanup.sh

# Clean specific resources
./scripts/docker-cleanup.sh --containers
./scripts/docker-cleanup.sh --images
./scripts/docker-cleanup.sh --volumes

# Deep clean
./scripts/docker-cleanup.sh --deep

# Remove all HyperCode resources
./scripts/docker-cleanup.sh --hypercode
```

### 3. **docker-backup.sh** - Backup Utility
Complete backup solution:
- PostgreSQL database backup
- Redis dump backup
- Docker volume backup
- Configuration backup
- Backup manifest creation
- Automatic compression
- Old backup cleanup (7 day retention)

**Usage:**
```bash
# Create backup
./scripts/docker-backup.sh

# Backup specific compose file
./scripts/docker-backup.sh docker-compose.prod.yml

# Custom backup location
BACKUP_DIR=/mnt/backups ./scripts/docker-backup.sh
```

## 📋 Makefile Commands

Enhanced Makefile with comprehensive commands:

```bash
# Development
make setup          # Initialize environment
make dev            # Start in dev mode
make build          # Build all containers
make up             # Start all services
make down           # Stop all services
make restart        # Restart services

# Monitoring
make logs           # View all logs
make logs-core      # View specific service logs
make status         # Check service status
make test           # Run tests

# Individual Services
make logs-frontend
make logs-backend
make restart-frontend

# Maintenance
make clean          # Remove all resources
make backup         # Create backup

# Production
make prod           # Start in production mode
```

## 🎯 Use Cases

### Local Development
```bash
# Start dev environment with hot reload
docker-compose -f docker-compose.dev.yml up

# Access dev tools
open http://localhost:8081  # Redis Commander
open http://localhost:5050  # pgAdmin
open http://localhost:8888  # Docs
```

### Testing
```bash
# Run all tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Run specific test suite
docker-compose -f docker-compose.test.yml run unit-tests
docker-compose -f docker-compose.test.yml run integration-tests
```

### CI/CD Pipeline
```bash
# Run CI pipeline
docker-compose -f docker-compose.ci.yml up --abort-on-container-exit

# Build and scan
docker buildx bake
docker-compose -f docker-compose.ci.yml run security-scan
```

### Production Deployment
```bash
# Build for production
REGISTRY=myregistry.com VERSION=v2.0.0 docker buildx bake --push

# Deploy
docker-compose -f docker-compose.prod.yml up -d

# Monitor health
./scripts/docker-health-monitor.sh docker-compose.prod.yml hypercode --watch
```

### Backup & Restore
```bash
# Create backup
./scripts/docker-backup.sh docker-compose.prod.yml

# Restore backup
tar xzf backups/hypercode-backup-20240209-120000.tar.gz
./scripts/docker-restore.sh 20240209-120000
```

### Resource Management
```bash
# Check disk usage
docker system df

# Cleanup unused resources
./scripts/docker-cleanup.sh

# Deep clean (careful!)
./scripts/docker-cleanup.sh --deep
```

## 🚀 Advanced Features

### Multi-Platform Builds
```bash
# Setup buildx
docker buildx create --name hypercode-builder --use

# Build for multiple platforms
docker buildx bake --platform linux/amd64,linux/arm64 --push
```

### Remote Development
```bash
# Use .devcontainer for VS Code
# Already configured in .devcontainer/devcontainer.json
code .  # Opens in dev container
```

### Docker Secrets (Production)
```bash
# Create secrets
echo "secret_value" | docker secret create api_key -

# Use in compose
docker stack deploy -c docker-compose.prod.yml hypercode
```

### Docker Context (Multi-Host)
```bash
# Add remote context
docker context create remote --docker "host=ssh://user@remote.host"

# Use remote context
docker context use remote
docker-compose up -d
```

## 📊 Monitoring & Observability

All configurations include:
- **Prometheus** - Metrics collection (port 9090)
- **Grafana** - Metrics visualization (port 3001)
- **Jaeger** - Distributed tracing (port 16686)
- **Health checks** - All services
- **Resource metrics** - CPU, memory, network
- **Custom metrics** - Application-specific

## 🔒 Security Features

- Non-root users in all containers
- Read-only filesystems where possible
- Network isolation
- Secret management
- Security scanning in CI
- Minimal base images
- Capability dropping
- No privileged containers (except DevOps agent when needed)

## 📦 Complete Docker Workflow

```bash
# 1. Development
docker-compose -f docker-compose.dev.yml up

# 2. Testing
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# 3. CI/CD
docker-compose -f docker-compose.ci.yml up --abort-on-container-exit

# 4. Build for production
REGISTRY=myregistry VERSION=v2.0 docker buildx bake --push

# 5. Deploy to production
docker-compose -f docker-compose.prod.yml up -d

# 6. Monitor
./scripts/docker-health-monitor.sh --watch

# 7. Backup
./scripts/docker-backup.sh

# 8. Scale
docker-compose -f docker-compose.prod.yml up -d --scale hypercode-core=3

# 9. Update
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# 10. Cleanup
./scripts/docker-cleanup.sh
```

## 🎓 Best Practices

1. **Always use specific versions** - Don't use `latest` in production
2. **Use multi-stage builds** - Keep images small
3. **Implement health checks** - For all services
4. **Set resource limits** - Prevent resource exhaustion
5. **Use secrets properly** - Never commit secrets
6. **Regular backups** - Automated and tested
7. **Monitor everything** - Logs, metrics, traces
8. **Clean up regularly** - Disk space management
9. **Security scanning** - Part of CI/CD
10. **Document everything** - This file!

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [BuildKit Bake Reference](https://docs.docker.com/build/bake/)
- [Kubernetes Manifests](../k8s/DEPLOYMENT.md)
