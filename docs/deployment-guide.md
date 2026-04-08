# HyperCode V2.0 - Deployment Guide

**Version:** 2.0.0
**Target Environments:** Development (Docker Compose), Staging/Production (Kubernetes)

---

## 1. Prerequisites & Infrastructure

*   **Runtime:** Docker Engine 24+ / Kubernetes 1.25+
*   **Database:** PostgreSQL 15+ (Managed RDS recommended for Prod)
*   **Message Broker:** Redis 7+ (ElastiCache recommended for Prod)
*   **Reverse Proxy:** Nginx / Traefik (Ingress Controller)
*   **Monitoring:** Prometheus + Grafana Stack

### Environment Variables (.env)
Required secrets for all environments:
```bash
ENVIRONMENT=production
HYPERCODE_DB_URL=postgresql://user:pass@host:5432/hypercode
HYPERCODE_REDIS_URL=redis://host:6379/0
JWT_SECRET=super_secure_random_string_min_32_chars
OPENAI_API_KEY=sk-... (or Azure Endpoint)
```

## 2. Deployment Procedures

### Development (Local)
1.  **Clone Repository:** `git clone ...`
2.  **Configure:** Copy `.env.example` to `.env`.
3.  **Build & Launch:**
    ```bash
    docker-compose --profile agents up -d --build
    ```
4.  **Verify:** Visit `http://localhost:8000/health` -> `{"status": "healthy"}`.

### Staging / Production (Kubernetes)
1.  **Secrets Management:**
    *   Create K8s Secrets for `HYPERCODE_DB_URL`, `JWT_SECRET`, etc.
    *   Do NOT commit `.env` files.
2.  **Apply Manifests:**
    ```bash
    kubectl apply -f k8s/policies/ # Network Policies first
    kubectl apply -f k8s/deployments/
    kubectl apply -f k8s/services/
    ```
3.  **Database Migration:**
    *   Run as a Job or InitContainer:
    ```bash
    python -m prisma migrate deploy
    ```
    *(Note: Do not run `prisma db push` in production; use migrations).*

## 3. Post-Deployment Verification

### Smoke Tests
*   [ ] **Core API:** `curl https://api.hypercode.ai/health` (Expect 200 OK)
*   [ ] **Agent Registry:** `curl https://api.hypercode.ai/agents` (Expect JSON list)
*   [ ] **Crew Assembly:** POST to `/crews/assemble` with a test manifest.
*   [ ] **Turing Gym:** Run a manual trigger of the "Hello World" test suite.

### Monitoring Checklist
*   [ ] **Grafana Dashboards:** Verify "Agent Health" and "Pool Status" panels are populating.
*   [ ] **AlertManager:** Trigger a test alert (e.g., high CPU) to verify notification routing (Slack/PagerDuty).

## 4. Disaster Recovery (DR)

### Backup & Restore
*   **Database:** Enable automated daily snapshots (RDS) + WAL archiving (PITR).
    *   *Restore:* Launch new RDS instance from snapshot -> Update K8s Secret -> Restart Pods.
*   **Redis:** Enable AOF persistence for durability (if using Redis for critical queues).

### Rollback Procedure
If a deployment fails:
1.  **Identify Issue:** Check logs (`kubectl logs -l app=hypercode-core`).
2.  **Revert Image:** Update Deployment to previous tag.
    ```bash
    kubectl set image deployment/hypercode-core hypercode-core=hypercode/core:v1.9.0
    ```
3.  **Database Rollback:** If schema changed, run the down-migration script (manually prepared).

## 5. Troubleshooting Common Issues

### Issue: "Agent Not Connected" (500 Error)
*   **Cause:** Redis connectivity issue or Agent container crashed.
*   **Fix:** Check Redis logs. Verify Agent container status (`kubectl get pods`).

### Issue: "Crew Assembly Timeout"
*   **Cause:** Warm Pool exhausted or Docker limit reached.
*   **Fix:** Check Pool Manager logs (`WarmPoolManager`). Scale up worker nodes.

### Issue: "Database Connection Failed" (Startup)
*   **Cause:** DB migration hasn't run or credentials invalid.
*   **Fix:** Run `prisma migrate deploy` manually. Verify `HYPERCODE_DB_URL`.

---
*For support, contact DevOps Team or Agent X.*
