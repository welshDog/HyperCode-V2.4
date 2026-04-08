# HyperCode V2.4 — Testing & Scanning Matrix

> Last updated: 2026-04-07
> Thresholds: `quality-gate-thresholds.yml`
> CI workflows: `.github/workflows/`
> Orchestration: `quality-gate.yml` calls reusable workflows via `workflow_call` (ci-python.yml, ci-js.yml, ci-security.yml, plus scheduled-only pipelines).

---

## Overview

| Category | Tools | Frequency | Blocks CI | Report Location |
|---|---|---|---|---|
| Unit Tests | pytest | Every commit | Yes | `reports/coverage/` |
| Integration Tests | pytest | Every commit | Yes | `reports/coverage/` |
| E2E Tests | Playwright | PR + main push | No (advisory) | CI artifact |
| Load / Performance | Locust, k6 | main push + manual | Yes (regression) | CI artifact |
| Static Code Analysis | Ruff, ESLint, mypy | Every commit | Yes (lint) | CI logs + artifacts |
| SAST | CodeQL, Semgrep, Bandit | PR + main push + weekly | Yes (High/Critical) | GitHub Security tab + `reports/security/` |
| Secret Detection | detect-secrets, Gitleaks | Every commit + pre-commit | Yes | `reports/secrets/` |
| Dependency Vulnerabilities | Trivy FS, pip-audit, npm audit, Dependency Review | Every commit/PR | Yes (policy) | GitHub Security tab + `reports/security/` |
| Container Scan | Trivy | PR + main push | Yes (CRITICAL/HIGH) | GitHub Security tab |
| IaC Scan | Trivy config | IaC file changes | Yes (CRITICAL/HIGH) | GitHub Security tab |
| IaC Validation | docker compose config, kubeconform, Helm lint/template | IaC file changes | Yes | CI artifacts |
| Container Hardening | Hadolint, Dockle | PR + main push | Advisory (configurable) | CI artifacts |
| License Compliance | pip-licenses, license-checker | Every commit | Yes (blocked SPDX) | `reports/licenses/` |
| SBOM Generation | Trivy CycloneDX | main push | No (informational) | CI artifact (90d) |
| Dynamic Security Scan (DAST) | OWASP ZAP Baseline | Nightly + manual | Advisory (pre-release gate) | CI artifacts |
| License/Policy Audit | pip-licenses, license-checker | Every commit | Yes | `reports/security/` |
| Executive Health Summary | CI summarizer | PR + main push | No (informational) | CI job summary + artifact |

---

## 1. Unit & Integration Tests

| Attribute | Value |
|---|---|
| **Tool** | pytest + pytest-asyncio |
| **Scope** | `tests/unit/`, `tests/integration/` |
| **Frequency** | Every commit/PR |
| **Coverage threshold** | ≥70% line, ≥60% branch |
| **Gate behaviour** | Fails CI if below threshold |
| **Markers** | `unit`, `integration`, `asyncio`, `slow`, `e2e` |
| **Config** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Reports** | `reports/coverage/coverage.xml`, `reports/coverage/html/` |
| **Workflow** | `quality-gate.yml` → `coverage` job |

### Success criteria
- All tests pass (exit code 0)
- Line coverage ≥ 70%
- No new `FAIL` markers introduced

---

## 2. End-to-End Tests

| Attribute | Value |
|---|---|
| **Tool** | Playwright (TypeScript) |
| **Scope** | `tests/e2e/`, browser-level UI flows |
| **Frequency** | PR + push to main |
| **Gate behaviour** | Advisory (does not block merge) |
| **Config** | `tests/e2e/playwright.config.ts` |
| **Workflow** | `ci-js.yml` / `ci.yml` (E2E job) |

---

## 3. Load & Performance Tests

| Attribute | Value |
|---|---|
| **Tool** | Locust (`tests/load/locustfile.py`), k6 (`tests/performance/k6-api-load.js`) |
| **Scope** | Core API endpoints — 50 users, 5/s spawn, 1 minute |
| **Frequency** | Push to `main`/`production` + `workflow_dispatch` |
| **Thresholds** | avg response ≤200ms, failure rate ≤1%, p95 ≤500ms |
| **Regression gate** | Prometheus baseline in `.github/prom-baseline.json`; >15% regression fails |
| **Config** | `performance.yml`, `.github/scripts/prom-regression.py` |
| **Workflow** | `performance.yml`, `swarm-pipeline.yml` |

---

## 4. Python SAST

### Bandit

| Attribute | Value |
|---|---|
| **Tool** | Bandit 1.8.x |
| **Scope** | `backend/`, `agents/`, `tools/` (excludes `tests/`) |
| **Severity gate** | HIGH → blocks; MEDIUM → reported |
| **Skipped rules** | B101 (assert), B601 (paramiko — no SSH in prod) |
| **Config** | CLI flags in `quality-gate.yml` |
| **Reports** | `reports/sast/bandit.json` |

### Semgrep

| Attribute | Value |
|---|---|
| **Tool** | Semgrep OSS |
| **Rulesets** | `p/python`, `p/flask`, `p/secrets`, `p/jwt`, `p/docker`, `p/owasp-top-ten` |
| **Severity gate** | ERROR → blocks; WARNING → advisory |
| **Config** | `semgrep.yaml` (project overrides + path exclusions) |
| **Reports** | `reports/sast/semgrep.json`, SARIF → GitHub Security tab |
| **Workflow** | `security-comprehensive.yml` → `semgrep` job |

---

## 4.1 CodeQL (SAST)

| Attribute | Value |
|---|---|
| **Tool** | GitHub CodeQL |
| **Scope** | Python + JavaScript/TypeScript code paths |
| **Frequency** | PR + push to main + weekly scheduled |
| **Gate** | High/Critical issues block merge (via required checks) |
| **Reports** | SARIF → GitHub Security tab |
| **Workflow** | `codeql.yml` |

---

## 5. Secret Detection

| Tool | Scope | Pre-commit | CI | Blocks |
|---|---|---|---|---|
| detect-secrets | Full repo scan + baseline diff | Yes | `ci-security.yml` | Yes |
| Gitleaks | Full git history | Yes (`.pre-commit-config.yaml`) | `security-comprehensive.yml` | Yes |

**Baseline file:** `.secrets.baseline`
**False positive suppression:** add `# pragma: allowlist secret` inline

---

## 6. Dependency Vulnerability Scanning

### Python — pip-audit

| Attribute | Value |
|---|---|
| **Tool** | pip-audit |
| **Scope** | `requirements.txt`, `backend/requirements.txt`, all `agents/*/requirements.txt` |
| **Gate** | Any CVE in root/backend requirements blocks CI |
| **Reports** | `reports/deps/pip-audit-*.json`, merged into `pip-audit-merged.json` |
| **Workflow** | `security-comprehensive.yml` → `pip-audit` job |

### JavaScript/npm

| Attribute | Value |
|---|---|
| **Tool** | npm audit |
| **Scope** | `agents/dashboard/package.json` |
| **Gate** | CRITICAL → blocks; HIGH → advisory |
| **Reports** | `reports/deps/npm-audit.json` |
| **Workflow** | `quality-gate.yml` → `frontend` job, `ci-security.yml` |

### Dependency Review (PR Delta)

| Attribute | Value |
|---|---|
| **Tool** | GitHub Dependency Review |
| **Scope** | Newly introduced vulnerable dependencies in PR diffs |
| **Gate** | High/Critical newly introduced vulnerabilities block merge |
| **Workflow** | `quality-gate.yml` (security job) |

### Automated updates

Dependabot is configured in `.github/dependabot.yml` for:
- Python pip (`requirements.txt`, `backend/requirements.txt`)
- npm (`agents/dashboard/package.json`)
- Docker base images
- GitHub Actions versions

---

## 7. Container Scanning (Trivy)

| Attribute | Value |
|---|---|
| **Tool** | Trivy (aquasecurity/trivy-action) |
| **Images scanned** | `hypercode-core:latest`, `hypercode-dashboard:latest` |
| **Scan types** | OS packages + library dependencies |
| **Severity gate** | CRITICAL/HIGH → blocks CI |
| **Format** | SARIF → GitHub Security tab + JSON artifact |
| **Ignore unfixed** | Yes (reduces noise for OS-level vulns with no patch) |
| **Workflow** | `ci.yml` → `docker-build` job |

---

## 8. IaC Scanning

### Trivy Config

| Attribute | Value |
|---|---|
| **Tool** | Trivy config scan |
| **Scope** | All `docker-compose*.yml`, `Dockerfile*`, `k8s/`, `helm/` |
| **Trigger** | Changes to IaC files + every PR |
| **Gate** | CRITICAL/HIGH → blocks |
| **Config** | `trivy.yaml` |
| **Workflow** | `iac-scan.yml` → `trivy-iac` job |

### Hadolint

| Attribute | Value |
|---|---|
| **Tool** | Hadolint 2.12.x |
| **Scope** | All `Dockerfile*` recursively |
| **Gate** | ERROR level → blocks; WARNING → advisory |
| **Ignored rules** | DL3008, DL3009, DL3018 (apt/apk pin advisory) |
| **Pre-commit** | Yes (`.pre-commit-config.yaml`) |
| **Workflow** | `iac-scan.yml` → `hadolint` job |

### Docker Compose Validation

| Attribute | Value |
|---|---|
| **Tool** | `docker compose config --quiet` |
| **Scope** | All `docker-compose*.yml` files |
| **Gate** | Invalid config → blocks |
| **Workflow** | `iac-scan.yml` → `compose-validate` job |

---

## 9. Ownership & Accountability

| Area | Primary Owner | Backup Owner |
|---|---|---|
| Backend tests + coverage | Backend Lead | QA |
| Dashboard tests + coverage | Frontend Lead | QA |
| SAST/SCA/secrets | AppSec | DevOps |
| Containers + IaC | DevOps | AppSec |
| Performance | SRE | QA |
| Compliance (licenses) | Compliance | AppSec |
| CI reliability + dashboards | DevOps | Tech Lead |

---

## 10. Evidence Model (100% Validation)

Validation evidence is produced per CI run as:
- SARIF uploads for SAST/IaC/container scans (traceable to file + line where supported)
- Artifacts under `reports/` (coverage, JSON scan outputs, and summaries)
- CI job summary with the executed scan set, pass/fail outcomes, and remediation pointers

## 9. License Compliance

| Attribute | Value |
|---|---|
| **Python tool** | pip-licenses |
| **npm tool** | license-checker |
| **Blocked licenses** | GPL-2.0, GPL-3.0, AGPL-3.0, SSPL-1.0 (and `-only`/`-or-later` variants) |
| **Review required** | LGPL-2.x, MPL-2.0, EUPL-1.x |
| **Gate** | Blocked license → fails CI |
| **Reports** | `reports/licenses/python.json`, `reports/licenses/npm.json` |
| **Workflow** | `security-comprehensive.yml` → `license-check` job |
| **Config** | `quality-gate-thresholds.yml` → `licenses` section |

---

## 10. SBOM Generation

| Attribute | Value |
|---|---|
| **Tool** | Trivy (CycloneDX format) |
| **Scope** | Full repository filesystem |
| **Frequency** | Push to main |
| **Format** | CycloneDX JSON (`sbom.cdx.json`) |
| **Retention** | 90 days as CI artifact |
| **Workflow** | `security-comprehensive.yml` → `sbom` job |

---

## 11. Pre-commit Hooks

Configured in `.pre-commit-config.yaml`. Install once per developer machine:
```bash
pip install pre-commit
pre-commit install        # hooks on git commit
pre-commit install --hook-type commit-msg   # commit message lint
```

| Hook | Purpose | Blocks commit |
|---|---|---|
| trailing-whitespace | File hygiene | Yes |
| end-of-file-fixer | File hygiene | Yes |
| check-yaml | YAML syntax | Yes |
| check-json | JSON syntax | Yes |
| check-merge-conflict | Stale conflict markers | Yes |
| detect-private-key | Accidental key leaks | Yes |
| ruff | Python lint + format | Yes |
| ruff-format | Python formatting | Yes |
| bandit | Python SAST | Yes (HIGH) |
| detect-secrets | Secret detection | Yes |
| gitleaks | Secret detection (git history) | Yes |
| hadolint-docker | Dockerfile lint | Yes (ERROR) |
| yamllint | YAML style | No (advisory) |
| commitizen | Conventional commit format | Yes (commit-msg stage) |

Run against all files manually:
```bash
pre-commit run --all-files
```

---

## 12. Automated Pipeline Map

```
Every commit / PR
│
├── quality-gate.yml         ← Master gate (MUST pass to merge)
│   ├── coverage             pytest + pytest-cov, ≥70% threshold
│   ├── bandit               Python SAST, HIGH → blocks
│   ├── frontend             ESLint + Vitest + npm audit
│   ├── deps-check           Dependency freshness (advisory)
│   └── dashboard            Generates HTML health report
│
├── security-comprehensive.yml
│   ├── semgrep              SAST — p/python, p/owasp-top-ten, etc.
│   ├── gitleaks             Secret scan (full git history)
│   ├── pip-audit            Python CVE scan
│   ├── trivy-full           Filesystem + IaC Trivy scan
│   ├── sbom                 CycloneDX SBOM generation
│   ├── license-check        pip-licenses + license-checker
│   └── security-gate        Aggregated pass/fail
│
├── ci.yml                   Existing: Black, Flake8, pytest, Trivy containers
│
└── iac-scan.yml             Triggered on IaC file changes only
    ├── hadolint             Dockerfile lint
    ├── trivy-iac            docker-compose/k8s misconfig scan
    ├── yamllint             YAML style (advisory)
    └── compose-validate     docker compose config validation

Push to main/production only:
└── performance.yml          Locust load test + regression gate
```

---

## 13. Quality Gate Thresholds (quick reference)

All thresholds are defined in `quality-gate-thresholds.yml` and can be adjusted without changing workflow code.

| Metric | Threshold | Action |
|---|---|---|
| Test coverage | ≥70% | Fail CI |
| Branch coverage | ≥60% | Fail CI |
| Bandit HIGH issues | 0 | Fail CI |
| Semgrep ERROR findings | 0 | Fail CI |
| CRITICAL CVEs (Python/npm/container) | 0 | Fail CI |
| HIGH CVEs (Python) | >10 | Fail CI |
| Secrets detected | 0 | Fail CI |
| Blocked licenses | 0 | Fail CI |
| npm CRITICAL vulns | 0 | Fail CI |
| IaC CRITICAL/HIGH misconfigs | 0 | Fail CI |
| Avg API response time | ≤200ms | Fail CI (perf) |
| API failure rate | ≤1% | Fail CI (perf) |
| Prometheus regression | ≤15% | Fail CI (perf) |

---

## 14. Local Scan Runner

Run all scans locally (requires tools installed):
```bash
# Full scan
bash scripts/scan/run-all-scans.sh

# Specific category
bash scripts/scan/run-all-scans.sh --only sast
bash scripts/scan/run-all-scans.sh --only secrets
bash scripts/scan/run-all-scans.sh --only deps

# Skip slow scans
bash scripts/scan/run-all-scans.sh --skip perf

# Stop immediately on first failure
bash scripts/scan/run-all-scans.sh --fail-fast
```

Generate the HTML dashboard from existing reports:
```bash
python3 scripts/scan/generate-dashboard.py \
    --reports-dir reports \
    --output reports/dashboard.html
```

Via Make (after Makefile targets added):
```bash
make scan         # full scan suite
make scan-quick   # sast + secrets only
make scan-report  # generate dashboard from existing reports
```

---

## 15. Tool Installation (Developer Setup)

```bash
# Python scanning tools
pip install bandit semgrep pip-audit pip-licenses detect-secrets

# Pre-commit framework
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg

# Gitleaks (binary)
# Windows: winget install gitleaks
# macOS:   brew install gitleaks
# Linux:   https://github.com/gitleaks/gitleaks/releases

# Hadolint (binary)
# Windows: winget install hadolint
# macOS:   brew install hadolint
# Linux:   https://github.com/hadolint/hadolint/releases

# Trivy (binary)
# Windows: winget install aquasecurity.trivy
# macOS:   brew install trivy
# Linux:   https://aquasecurity.github.io/trivy/latest/getting-started/installation/

# Node tools (from dashboard)
cd agents/dashboard && npm install
```
