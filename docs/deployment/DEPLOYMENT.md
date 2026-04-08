# 🚀 Production Deployment Guide

## Prerequisites

- **Docker & Docker Compose** (or Kubernetes)
- **4GB+ RAM** available
- **PERPLEXITY/OpenAI API key**
- **Domain name** (optional, for HTTPS)

## Deployment Options

### Option 1: Docker Compose (Standard Deployment)

This is the recommended method for most users and small teams. It launches the entire ecosystem on a single host.

#### 1. Prepare Environment
```bash
# Clone repository
git clone https://github.com/welshDog/HyperCode-V2.0.git
cd HyperCode-V2.0

# Configure Environment
cp .env.example .env
nano .env
```

#### 2. Configure Settings
Ensure your `.env` file has:
- `PERPLEXITY_API_KEY` / `OPENAI_API_KEY`
- Secure passwords for Database (`POSTGRES_PASSWORD`) if exposing to public.
- `HYPERCODE_JWT_SECRET` (generate a random string).

#### 3. Deploy
```bash
# Start all services
docker compose up -d

# Verify Deployment
docker compose ps
```

#### 4. Access
- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`

---

### Option 2: Kubernetes (Enterprise Scale)

For high-availability production environments.

#### 1. Create Namespace
```bash
kubectl create namespace hypercode-agents
```

#### 2. Create Secrets
```bash
kubectl create secret generic PERPLEXITY-key \
  --from-literal=api-key=sk-ant-xxxxx \
  -n hypercode-agents

kubectl create secret generic db-credentials \
  --from-literal=password=<strong-password> \
  -n hypercode-agents
```

#### 3. Deploy Infrastructure
```bash
# Apply base infrastructure
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/postgres.yaml
```

#### 4. Deploy Agents
```bash
# Apply agent deployments
kubectl apply -f k8s/orchestrator.yaml
kubectl apply -f k8s/agents/
```

#### 5. Setup Ingress
```bash
kubectl apply -f k8s/ingress.yaml
```

---

## Security Hardening

### 1. API Key Rotation
Regularly rotate keys in your `.env` or K8s secrets.

### 2. Network Isolation
HyperCode uses internal Docker networks (`backend-net`, `data-net`) to isolate services. Ensure you do not expose ports 5432 (Postgres) or 6379 (Redis) to the public internet in production.

### 3. Resource Limits
Default `docker-compose.yml` includes resource limits. Adjust `deploy.resources.limits` based on your server capacity.

## Monitoring Setup

### Prometheus + Grafana
HyperCode comes with a pre-configured observability stack.
- **Grafana**: `http://localhost:3001`
- **Prometheus**: `http://localhost:9090`

### Logging
Logs are driver-configured to `json-file` with rotation.
```bash
docker compose logs -f hypercode-core
```

## Maintenance

### Updates
```bash
git pull origin main
docker compose pull
docker compose up -d
```

### Backup
See `runbook.md` for detailed backup procedures.

---

**Support**: For issues, create a GitHub issue or contact the team.
**Documentation**: See `docs/` for detailed guides.
