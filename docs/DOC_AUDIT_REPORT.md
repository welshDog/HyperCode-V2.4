# Documentation Audit Report

**Doc Tag:** v2.0.0 | **Last Updated:** 2026-03-10

This report summarizes documentation drift detected versus the current codebase and configuration, and lists prioritized updates to bring docs back into sync.

## Executive Summary

### Key drift themes found

- **LLM service rename drift**: multiple docs reference `hypercode-llama` (legacy) while the current service is `hypercode-ollama` in [docker-compose.yml](../docker-compose.yml).
- **Compose syntax drift**: docs inconsistently use `docker-compose` vs `docker compose`, and some health-check advice is no longer accurate.
- **Linking drift**: several docs used local `file:///` links (not GitHub-friendly); canonical docs now use repo-relative links.
- **Historical reports treated as current guidance**: dated health reports contain recommendations that conflict with the current stack; these should be explicitly marked as snapshots.
- **Changelog drift**: `CHANGELOG.md` includes items not present in the current repo (needs cleanup to be trustworthy).

## Prioritized Update List

### P0 — Must fix (user-facing confusion / incorrect instructions)

- [docs/index.md](index.md)
  - Fix: remove links to missing pages; point to current canonical docs.
- [docs/ai/brain-architecture.md](ai/brain-architecture.md)
  - Fix: update AI provider description (Ollama-first, cloud optional).
- [docs/observability/monitoring-guide.md](observability/monitoring-guide.md)
  - Fix: remove Jaeger references (current stack uses Tempo + Grafana Explore).
- [REPOSITORY_REPORT.md](../REPOSITORY_REPORT.md)
  - Fix: replace local `file:///` links with repo-relative links (GitHub-compatible).
  - Fix: add doc tag + last updated metadata.
- [CONTRIBUTING.md](../CONTRIBUTING.md)
  - Fix: replace placeholder clone URL with actual repo URL.
  - Fix: standardize on `docker compose` examples.
- [TINYLLAMA_CONFIGURATION.md](configuration/TINYLLAMA_CONFIGURATION.md)
  - Fix: replace `hypercode-llama` references with `hypercode-ollama`.
  - Fix: align storage details with `ollama-data` named volume.
- [ai-integration-notes.md](notes/ai-integration-notes.md)
  - Fix: remove stale paths and legacy implementation notes referencing non-existent directories.
  - Fix: link to current backend integration points.

### P1 — Should fix (keeps “current docs” aligned with released code)

- [CHANGELOG.md](../CHANGELOG.md)
  - Fix: remove unverified/unshipped entries; add recent verified changes.
- Dated health reports that reference `hypercode-llama` should be marked as snapshots and point to canonical current docs:
  - [docs/health-reports](health-reports/)
  - [docs/reports](reports/)
  - [docs/archive](archive/)

### P2 — Nice-to-have (improves maintainability)

- Add a docs synchronization checklist and a lightweight “docs version header” convention.
- Add a “source of truth” section to canonical docs to reduce drift.

## Documents Flagged for Snapshot Banner (Historical)

The following docs reference legacy service names and/or “point-in-time” infrastructure assumptions and should be explicitly labeled as historical reports (not live guidance):

- [deployment/DEPLOYMENT_READINESS.md](deployment/DEPLOYMENT_READINESS.md)
- [health-reports/DOCKER_HEALTH_ASSESSMENT_2026-02-06.md](health-reports/DOCKER_HEALTH_ASSESSMENT_2026-02-06.md)
- [health-reports/DOCKER_HEALTH_REVIEW_2026-02-06.md](health-reports/DOCKER_HEALTH_REVIEW_2026-02-06.md)
- [health-reports/DOCKER_OPTIMIZATION_ANALYSIS_2026-02-06.md](health-reports/DOCKER_OPTIMIZATION_ANALYSIS_2026-02-06.md)
- [health-reports/PROJECT_HEALTH_CHECK_2026-02-06.md](health-reports/PROJECT_HEALTH_CHECK_2026-02-06.md)
- [health-reports/SYSTEM_STATUS_REPORT_2026-02-06.md](health-reports/SYSTEM_STATUS_REPORT_2026-02-06.md)
- [health-reports/TECHNICAL_EVALUATION_2026-02-06.md](health-reports/TECHNICAL_EVALUATION_2026-02-06.md)
- [health-reports/TECHNICAL_EVALUATION_REVIEW_2026-02-06.md](health-reports/TECHNICAL_EVALUATION_REVIEW_2026-02-06.md)
- [reports/analysis/COMPREHENSIVE_PROJECT_ANALYSIS_2026.md](reports/analysis/COMPREHENSIVE_PROJECT_ANALYSIS_2026.md)
- [reports/health/POST_UPGRADE_HEALTH_REPORT.md](reports/health/POST_UPGRADE_HEALTH_REPORT.md)
- [reports/health/POST_UPDATE_HEALTH_CHECK_COMPLETE.md](reports/health/POST_UPDATE_HEALTH_CHECK_COMPLETE.md)
- [reports/verification/FIX_VERIFICATION_COMPLETE.md](reports/verification/FIX_VERIFICATION_COMPLETE.md)
- [archive/DOCKER_HEALTH_CHECK_REPORT.md](archive/DOCKER_HEALTH_CHECK_REPORT.md)
- [archive/FINAL_HEALTH_REPORT.md](archive/FINAL_HEALTH_REPORT.md)
- [archive/HEALTH_CHECK_REPORT.md](archive/HEALTH_CHECK_REPORT.md)
- [archive/HEALTH_CHECK_UPDATE.md](archive/HEALTH_CHECK_UPDATE.md)

## Canonical Docs (Recommended Sources of Truth)

- Platform overview: [ARCHITECTURE.md](../ARCHITECTURE.md)
- Deployment overview: [DEPLOYMENT.md](../DEPLOYMENT.md) and [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md)
- Environment and configuration: [.env.example](../.env.example)
- LLM configuration: [TINYLLAMA_CONFIGURATION.md](configuration/TINYLLAMA_CONFIGURATION.md)
