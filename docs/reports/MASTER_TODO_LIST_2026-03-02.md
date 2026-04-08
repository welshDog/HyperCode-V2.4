# ✅ HyperCode V2.0 - Master To-Do List
**Date:** 2026-03-02
**Status:** This document supersedes all previous checklists and reports. It is our single source of truth for the next steps.

---

## 🎯 Mission Objective
To move from "Functionally Complete" to "Truly Production-Ready" by systematically addressing all identified gaps, starting with the most critical security vulnerabilities.

---

## Phase 1: Critical Security Hardening (Immediate Priority)
**Goal:** Eliminate all known high-risk security flaws. The system is not safe for production until these are complete.

- [ ] **SEC-01: Rotate Default Credentials**
  - [ ] Change PostgreSQL password from `changeme`.
  - [ ] Change MinIO password from `minioadmin`.
  - [ ] Change Grafana password from `admin`.

- [ ] **SEC-02: Generate Production Secrets**
  - [ ] Generate a strong, random `API_KEY`.
  - [ ] Generate a strong, random `HYPERCODE_JWT_SECRET`.
  - [ ] Generate a strong, random `HYPERCODE_MEMORY_KEY`.

- [ ] **SEC-03: Secure Environment File**
  - [ ] Create a new `.env` file with the new secrets.
  - [ ] **Crucially:** Ensure `.env` is listed in `.gitignore` and is NOT committed to the repository.

---

## Phase 2: Operational Stability (This Week)
**Goal:** Ensure the system is resilient and recoverable.

- [ ] **OPS-01: Automate Backups**
  - [ ] Create a cron job or scheduled task to run `scripts/backup_hypercode.sh` daily.
  - [ ] Extend the backup script to also cover the `minio_data` volume.

- [ ] **OPS-02: Run Vulnerability Scan**
  - [ ] Run `docker scout scan` on the primary images (`hypercode-core`, `dashboard`).
  - [ ] Document any critical vulnerabilities found for remediation in the next phase.

- [ ] **OPS-03: Verify Observability Health**
  - [ ] The `DOCKER_COMPLETE_INVENTORY_REPORT.md` noted that Loki, Tempo, and Promtail had failing health checks on startup.
  - [ ] Confirm that these services are now healthy after their startup period. If not, investigate their logs.

---

## Phase 3: Engineering Rigor (Next Sprint)
**Goal:** Improve code quality, reduce regression risk, and fulfill CI requirements.

- [ ] **QA-01: Expand Backend Test Coverage**
  - [ ] Add `pytest` tests for the main API endpoints in `hypercode-core` (e.g., user auth, task creation).
  - [ ] Configure `pytest-cov` to generate a coverage report. Aim for >80% coverage.

- [ ] **QA-02: Implement Frontend Tests**
  - [ ] The `Execute Comprehensive Project Health Assessment.md` plan noted zero tests for the frontend.
  - [ ] Create a baseline test suite (e.g., using Jest/React Testing Library) for the `hypercode-dashboard`.

---

## Phase 4: Future Enhancements (Backlog)
**Goal:** Long-term improvements for a mature, enterprise-grade system.

- [ ] **SEC-IMPROVE:** Migrate from `.env` file to a more secure secret management system (e.g., Docker Secrets, HashiCorp Vault).
- [ ] **OPS-IMPROVE:** Define and test a full Disaster Recovery (DR) plan, including RTO/RPO.
- [ ] **INF-IMPROVE:** Pin all Docker image versions in `docker-compose.yml` (e.g., `grafana/grafana:10.4.1` instead of `latest`) to ensure deterministic builds.
- [ ] **DATA-IMPROVE:** Enable TLS for the PostgreSQL connection to encrypt data in transit.
