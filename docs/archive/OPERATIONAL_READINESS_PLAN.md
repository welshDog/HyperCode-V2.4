# Operational Readiness Checklist & Execution Plan: HyperCode V2.0

## 1. Executive Summary
This document outlines the validation, execution, and contingency strategies for deploying HyperCode V2.0 to the production environment. It serves as the primary playbook for operations, ensuring system stability, security, and recoverability.

## 2. Pre-Operation Validation Checklist
Before initiating deployment or major operational changes, ensure the following criteria are met:

### 2.1 System Health (Status: 🟢 Ready with Warnings)
- **Configuration**: Docker Compose files (`production`, `agents`) validated. Nginx routing configured for `/api` and `/grafana`.
- **Dependencies**: 🟠 **Warning**: Frontend dependencies have known vulnerabilities (Audit ID: `npm-audit-frontend`). *Mitigation: Monitor for exploit attempts; schedule dependency update sprint post-launch.*
- **Tests**: 🟠 **Warning**: Unit tests (`pytest`) have context configuration issues, but runtime `smoke_test.py` passes with SSL verification bypass.
- **Connectivity**: Service-to-service communication verified via `smoke_test.py`.

### 2.2 Security Confirmation
- [x] **Secrets Management**: All sensitive keys (`API_KEY`, `JWT_SECRET`, `DB_PASSWORD`) are loaded via `.env` and NOT hardcoded.
- [x] **SSL/TLS**: Self-signed certificates in place for Nginx. *Action Required: Plan migration to Let's Encrypt for public release.*
- [x] **Network Isolation**: Backend services (`redis`, `postgres`, `hypercode-core`) are on `platform-net` and not exposed via public ports (only Nginx is exposed).

### 2.3 Resource Allocation
| Service | CPU Limit | Memory Limit | Current Status | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **hypercode-core** | *Undefined* | *Undefined* | Unbounded | **Set Limit**: 2 CPUS, 4GB RAM |
| **broski-terminal** | *Undefined* | *Undefined* | Unbounded | **Set Limit**: 1 CPU, 2GB RAM |
| **crew-orchestrator** | 1.0 | 1GB | Defined | ✅ Optimal |
| **project-strategist** | 0.75 | 768MB | Defined | ✅ Optimal |
| **postgres** | *Undefined* | *Undefined* | Unbounded | **Set Limit**: 2 CPUs, 4GB RAM |

*Risk: Unbounded production services may consume all host resources, impacting the agent swarm.*

## 3. Backup & Rollback Strategy

### 3.1 Database Backup
**Protocol**: Automated daily backups + Pre-deployment manual backup.
**Tool**: `scripts/backup_postgres.ps1`
**Location**: `.\backups\postgres\`

### 3.2 Rollback Procedure (Database)
In case of data corruption or failed migration:
1.  **Stop Services**: `docker compose -f docker-compose.production.yml stop hypercode-core celery-worker`
2.  **Execute Restore**:
    ```powershell
    ./scripts/restore_postgres.ps1
    # Or specify a file:
    # ./scripts/restore_postgres.ps1 -BackupFile ".\backups\postgres\backup_YYYYMMDD_HHMMSS.sql"
    ```
3.  **Verify**: Check logs for successful restoration.
4.  **Restart**: Services will auto-restart via script.

### 3.3 Application Rollback
**Protocol**: Revert to previous Docker image tags or git commit.
1.  `git checkout <previous-stable-commit>`
2.  `docker compose -f docker-compose.production.yml up -d --build`

## 4. Monitoring & Alerting
- **Dashboards**: Grafana available at `https://localhost/grafana/` (Credentials: `admin`/`admin` default).
- **Metrics**: Prometheus scraping `hypercode-core`, `postgres` (via exporter), and `cadvisor` (if enabled).
- **Alerts**: Configured in `alert.rules.yml`.
    - *High CPU/Memory Usage*
    - *Service Down (Up == 0)*
    - *High Error Rate*

## 5. Execution Plan (Step-by-Step)

### Phase 1: Preparation
1.  **Pull Latest Code**: `git pull origin main`
2.  **Verify .env**: Ensure production secrets are populated.
3.  **Backup Data**:
    ```powershell
    ./scripts/backup_postgres.ps1
    ```

### Phase 2: Deployment
4.  **Launch Platform Stack**:
    ```powershell
    docker compose -f docker-compose.production.yml up -d --build
    ```
5.  **Launch Agent Swarm**:
    ```powershell
    docker compose -f docker-compose.agents.yml up -d --build
    ```
6.  **Wait for Healthchecks**: Monitor `docker ps` until all statuses are `(healthy)`.

### Phase 3: Validation
7.  **Run Verification Script**:
    ```powershell
    ./scripts/verify_launch.ps1
    ```
8.  **Manual Verification**:
    - Access Terminal: `https://localhost/` (Accept self-signed cert)
    - Access Grafana: `https://localhost/grafana/`
    - Check Agent Status: Verify `crew-orchestrator` is reachable.

## 6. Contingency & Communication
- **Incident Commander**: [Assign Name]
- **Communication Channel**: #devops-alerts
- **Critical Failure Criteria**:
    - Database data loss (Trigger Rollback 3.2)
    - > 1% API Error Rate (Trigger Hotfix or Rollback 3.3)
    - Security Breach (Trigger Emergency Shutdown)

## 7. Post-Operation Tasks
- [ ] Monitor resource usage for 24h to refine limits.
- [ ] Rotate temporary production keys if exposed.
- [ ] Schedule dependency patching.
