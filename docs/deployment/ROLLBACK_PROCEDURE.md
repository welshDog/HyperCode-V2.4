# 🔄 Rollback Procedure for HyperCode V2.0

**Last Updated:** 2026-02-06
**Scope:** Production Environment

This document outlines the standard operating procedure (SOP) for reverting a failed deployment of HyperCode V2.0.

## 1. Triggers for Rollback
Initiate a rollback immediately if any of the following occur within 1 hour of deployment:
*   **Error Rate Spike:** HTTP 5xx errors exceed 1% of total traffic.
*   **Latency Spike:** p95 latency exceeds 500ms (baseline is ~100ms).
*   **Critical Feature Failure:** "Coder Agent" or "Orchestrator" becomes unresponsive.
*   **Data Corruption:** Evidence of invalid database writes.

## 2. Infrastructure Rollback (Docker)

### Step 2.1: Revert Container Images
If using `docker-compose`, revert to the previous stable tag.

```bash
# 1. Identify the previous stable commit hash (e.g., abc1234)
git checkout abc1234

# 2. Pull the old images
docker-compose pull

# 3. Restart services (Zero-Downtime if possible, otherwise hard restart)
docker-compose up -d --force-recreate
```

### Step 2.2: Verify Service Health
Check that the old containers are running and healthy.

```bash
docker ps -a | grep "hypercode"
curl http://localhost:8000/health
```

## 3. Database Rollback (Postgres)

**⚠️ WARNING:** Database rollbacks can cause data loss for transactions that occurred *after* the deployment. Only perform this if the schema migration itself caused the failure.

### Step 3.1: Revert Migration
If using Prisma:

```bash
# 1. Resolve the migration down (requires manual SQL usually, or restoring backup)
# For HyperCode, we rely on Point-In-Time Recovery (PITR) for catastrophic schema failures.
```

### Step 3.2: Restore from Backup (Catastrophic)
If the database is corrupted:

1.  Stop the application: `docker-compose stop hypercode-core`
2.  Restore the pre-deploy backup:
    ```bash
    cat backup_pre_deploy.sql | docker exec -i hyper-postgres psql -U hyper -d hypercode
    ```
3.  Restart application.

## 4. Frontend Rollback (Vercel)
1.  Go to the Vercel Dashboard.
2.  Navigate to **Deployments**.
3.  Find the previous "Ready" deployment.
4.  Click **...** -> **Promote to Production** (Instant Rollback).

## 5. Post-Rollback Verification
1.  Run the **Smoke Test Suite**:
    *   Login
    *   Create Mission
    *   Chat with Agent
2.  Notify stakeholders via `#dev-ops` channel:
    > "🚨 Deployment failed. Rollback to v2.0.x completed. System operating normally. Investigation started."
