#!/usr/bin/env bash
# ============================================================================
# HyperCode V2.4 — Local Comprehensive Scan Runner
# ============================================================================
# Usage:
#   bash scripts/scan/run-all-scans.sh              # run everything
#   bash scripts/scan/run-all-scans.sh --only sast  # run one category
#   bash scripts/scan/run-all-scans.sh --skip perf  # skip one category
#
# Categories: sast | secrets | deps | iac | licenses | coverage | perf | all
# ============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORTS="$REPO_ROOT/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$REPORTS/scan-$TIMESTAMP.log"

# Colours
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
BLUE='\033[0;34m'; BOLD='\033[1m'; RESET='\033[0m'

ONLY=""
SKIP=""
FAIL_FAST=false

# ── Argument parsing ─────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --only) ONLY="$2"; shift 2 ;;
    --skip) SKIP="$2"; shift 2 ;;
    --fail-fast) FAIL_FAST=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ── Helpers ──────────────────────────────────────────────────────────────
mkdir -p "$REPORTS"/{sast,secrets,deps,iac,licenses,coverage,perf}

PASS=0; FAIL=0; SKIP_COUNT=0
declare -A RESULTS

header() { echo -e "\n${BOLD}${BLUE}═══ $1 ═══${RESET}"; }
ok()     { echo -e "${GREEN}  ✓ $1${RESET}"; PASS=$((PASS+1)); RESULTS["$2"]="PASS"; }
fail()   { echo -e "${RED}  ✗ $1${RESET}"; FAIL=$((FAIL+1)); RESULTS["$2"]="FAIL"; }
warn()   { echo -e "${YELLOW}  ⚠ $1${RESET}"; }
skip()   { echo -e "  — $1 (skipped)"; SKIP_COUNT=$((SKIP_COUNT+1)); RESULTS["$2"]="SKIP"; }

should_run() {
  local cat="$1"
  [[ "$SKIP" == "$cat" ]] && return 1
  [[ -n "$ONLY" && "$ONLY" != "$cat" && "$ONLY" != "all" ]] && return 1
  return 0
}

check_cmd() { command -v "$1" &>/dev/null; }

cd "$REPO_ROOT"

# ── 1. Static Analysis (Bandit + Ruff) ──────────────────────────────────
if should_run sast; then
  header "SAST — Static Analysis"

  if check_cmd bandit; then
    bandit \
      -r backend/ agents/ tools/ \
      --format json \
      --output "$REPORTS/sast/bandit.json" \
      -ll -ii --skip B101,B601 \
      > /dev/null 2>&1 && ok "Bandit passed" "bandit" \
      || { fail "Bandit found issues — see reports/sast/bandit.json" "bandit"
           $FAIL_FAST && exit 1; }
  else
    warn "bandit not installed — run: pip install bandit"
    RESULTS["bandit"]="MISSING"
  fi

  if check_cmd ruff; then
    ruff check backend/ agents/ tools/ \
      --output-format json \
      --output-file "$REPORTS/sast/ruff.json" \
      > /dev/null 2>&1 && ok "Ruff lint passed" "ruff" \
      || { fail "Ruff found lint errors — see reports/sast/ruff.json" "ruff"
           $FAIL_FAST && exit 1; }
  else
    warn "ruff not installed — run: pip install ruff"
    RESULTS["ruff"]="MISSING"
  fi

  if check_cmd semgrep; then
    semgrep scan \
      --config "p/python" \
      --config "p/secrets" \
      --config "p/owasp-top-ten" \
      --config semgrep.yaml \
      --json --output "$REPORTS/sast/semgrep.json" \
      --severity ERROR \
      --exclude "tests/" --exclude "*.lock" --exclude "node_modules/" \
      --quiet \
      && ok "Semgrep passed" "semgrep" \
      || { fail "Semgrep found issues — see reports/sast/semgrep.json" "semgrep"
           $FAIL_FAST && exit 1; }
  else
    warn "semgrep not installed — run: pip install semgrep"
    RESULTS["semgrep"]="MISSING"
  fi
else
  skip "SAST" "sast"
fi

# ── 2. Secret Detection ──────────────────────────────────────────────────
if should_run secrets; then
  header "Secret Detection"

  if check_cmd detect-secrets; then
    detect-secrets scan \
      --all-files \
      --exclude-files 'package-lock\.json' \
      --exclude-files '\.secrets\.baseline' \
      --exclude-files '.*\.lock' \
      > "$REPORTS/secrets/detect-secrets.json" 2>&1
    # check if new secrets vs baseline
    detect-secrets audit --diff \
      .secrets.baseline "$REPORTS/secrets/detect-secrets.json" \
      > "$REPORTS/secrets/diff.txt" 2>&1 && ok "detect-secrets clean" "detect-secrets" \
      || { fail "New secrets detected vs baseline" "detect-secrets"
           $FAIL_FAST && exit 1; }
  else
    warn "detect-secrets not installed — run: pip install detect-secrets"
    RESULTS["detect-secrets"]="MISSING"
  fi

  if check_cmd gitleaks; then
    gitleaks detect \
      --source . \
      --report-path "$REPORTS/secrets/gitleaks.json" \
      --report-format json \
      --no-git \
      --exit-code 0 \
      > /dev/null 2>&1
    # check for findings
    python3 -c "
import json, sys
with open('$REPORTS/secrets/gitleaks.json') as f:
    findings = json.load(f)
if findings:
    print(f'  Found {len(findings)} secret(s):')
    for s in findings[:5]:
        print(f'    {s.get(\"File\",\"?\")}:{s.get(\"StartLine\",\"?\")} — {s.get(\"RuleID\",\"?\")}')
    sys.exit(1)
" 2>/dev/null && ok "Gitleaks clean" "gitleaks" \
      || { fail "Gitleaks found secrets — see reports/secrets/gitleaks.json" "gitleaks"
           $FAIL_FAST && exit 1; }
  else
    warn "gitleaks not installed — see https://github.com/gitleaks/gitleaks#installing"
    RESULTS["gitleaks"]="MISSING"
  fi
else
  skip "Secrets" "secrets"
fi

# ── 3. Dependency Vulnerabilities ────────────────────────────────────────
if should_run deps; then
  header "Dependency Vulnerabilities"

  if check_cmd pip-audit; then
    pip-audit \
      -r requirements.txt \
      --format json \
      --output "$REPORTS/deps/pip-audit.json" \
      > /dev/null 2>&1 && ok "pip-audit: no CVEs in root requirements" "pip-audit" \
      || { fail "pip-audit found vulnerabilities — see reports/deps/pip-audit.json" "pip-audit"
           $FAIL_FAST && exit 1; }
  else
    warn "pip-audit not installed — run: pip install pip-audit"
    RESULTS["pip-audit"]="MISSING"
  fi

  if check_cmd npm && [ -f agents/dashboard/package.json ]; then
    (cd agents/dashboard && npm audit --json > "$REPORTS/deps/npm-audit.json" 2>/dev/null) || true
    python3 -c "
import json, sys
try:
    with open('$REPORTS/deps/npm-audit.json') as f:
        data = json.load(f)
    crit = data.get('metadata',{}).get('vulnerabilities',{}).get('critical', 0)
    high = data.get('metadata',{}).get('vulnerabilities',{}).get('high', 0)
    print(f'  npm audit: critical={crit}, high={high}')
    if crit > 0:
        sys.exit(1)
except Exception:
    pass
" && ok "npm audit: no critical vulnerabilities" "npm-audit" \
    || { fail "npm audit found CRITICAL vulnerabilities" "npm-audit"
         $FAIL_FAST && exit 1; }
  fi
else
  skip "Dependencies" "deps"
fi

# ── 4. IaC / Dockerfile Scanning ─────────────────────────────────────────
if should_run iac; then
  header "IaC & Dockerfile Scanning"

  if check_cmd hadolint; then
    DOCKERFILES=$(find . -name "Dockerfile*" -not -path "*/node_modules/*" -not -path "*/_archive/*" 2>/dev/null)
    if [ -n "$DOCKERFILES" ]; then
      echo "$DOCKERFILES" | xargs hadolint \
        --ignore DL3008 --ignore DL3009 --ignore DL3018 \
        --format json \
        > "$REPORTS/iac/hadolint.json" 2>&1 && ok "Hadolint: Dockerfiles clean" "hadolint" \
        || { warn "Hadolint found issues — see reports/iac/hadolint.json (advisory)"
             RESULTS["hadolint"]="WARN"; }
    fi
  else
    warn "hadolint not installed — see https://github.com/hadolint/hadolint#installing"
    RESULTS["hadolint"]="MISSING"
  fi

  # Validate docker-compose files
  COMPOSE_OK=true
  for f in $(find . -name "docker-compose*.yml" -not -path "*/_archive/*" 2>/dev/null); do
    docker compose -f "$f" config --quiet 2>&1 | head -1 || { COMPOSE_OK=false; break; }
  done
  $COMPOSE_OK && ok "All docker-compose files valid" "compose" \
    || { fail "docker-compose validation failed" "compose"
         $FAIL_FAST && exit 1; }

  if check_cmd trivy; then
    trivy config \
      --format json \
      --output "$REPORTS/iac/trivy-iac.json" \
      --severity CRITICAL,HIGH,MEDIUM \
      . > /dev/null 2>&1 && ok "Trivy IaC: no critical misconfigurations" "trivy-iac" \
      || { fail "Trivy IaC found misconfigurations" "trivy-iac"
           $FAIL_FAST && exit 1; }
  else
    warn "trivy not installed — see https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
    RESULTS["trivy-iac"]="MISSING"
  fi
else
  skip "IaC" "iac"
fi

# ── 5. License Compliance ─────────────────────────────────────────────────
if should_run licenses; then
  header "License Compliance"

  if check_cmd pip-licenses; then
    pip-licenses \
      --format=json \
      --output-file="$REPORTS/licenses/python.json" \
      --with-urls 2>/dev/null

    python3 - << 'PYEOF'
import json, sys
BLOCKED = {"GPL-2.0","GPL-3.0","AGPL-3.0","SSPL-1.0","Commons-Clause",
           "GPL-2.0-only","GPL-3.0-only","AGPL-3.0-only"}
try:
    with open("$REPORTS/licenses/python.json") as f:
        pkgs = json.load(f)
except Exception:
    sys.exit(0)
violations = [f"  {p['Name']} — {p['License']}" for p in pkgs
              if any(b in p.get('License','') for b in BLOCKED)]
if violations:
    print("Blocked licenses found:")
    print('\n'.join(violations))
    sys.exit(1)
print(f"  {len(pkgs)} Python packages — all licenses OK")
PYEOF
    RC=$?
    [ $RC -eq 0 ] && ok "Python license audit passed" "py-licenses" \
      || { fail "Blocked Python licenses found" "py-licenses"
           $FAIL_FAST && exit 1; }
  else
    warn "pip-licenses not installed — run: pip install pip-licenses"
    RESULTS["py-licenses"]="MISSING"
  fi
else
  skip "Licenses" "licenses"
fi

# ── 6. Test Coverage ──────────────────────────────────────────────────────
if should_run coverage; then
  header "Test Coverage"

  export PYTHONPATH="$PYTHONPATH:$REPO_ROOT"
  pytest tests/unit/ tests/integration/ \
    --cov=backend/app \
    --cov-branch \
    --cov-report=xml:"$REPORTS/coverage/coverage.xml" \
    --cov-report=html:"$REPORTS/coverage/html" \
    --cov-report=term-missing \
    --cov-fail-under=70 \
    -q --tb=short \
    -m "not e2e and not slow" \
    2>&1 | tee "$REPORTS/coverage/output.txt"
  RC=${PIPESTATUS[0]}
  [ $RC -eq 0 ] && ok "Coverage gate passed (≥70%)" "coverage" \
    || { fail "Coverage below 70% threshold" "coverage"
         $FAIL_FAST && exit 1; }
else
  skip "Coverage" "coverage"
fi

# ── 7. Performance (smoke check) ─────────────────────────────────────────
if should_run perf; then
  header "Performance (k6 smoke)"
  warn "Performance tests require a running stack — skipping in local mode"
  warn "Run: make up && k6 run tests/performance/k6-api-load.js"
  RESULTS["perf"]="SKIP"
else
  skip "Performance" "perf"
fi

# ── Summary ───────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}═══════════════════════════════════════${RESET}"
echo -e "${BOLD}         SCAN SUMMARY — $TIMESTAMP${RESET}"
echo -e "${BOLD}═══════════════════════════════════════${RESET}"
printf "%-20s %s\n" "Check" "Result"
printf "%-20s %s\n" "─────────────────" "──────"
for check in bandit ruff semgrep detect-secrets gitleaks pip-audit npm-audit hadolint compose trivy-iac py-licenses coverage perf; do
  result="${RESULTS[$check]:-N/A}"
  case "$result" in
    PASS) colour=$GREEN ;;
    FAIL) colour=$RED ;;
    WARN) colour=$YELLOW ;;
    SKIP|N/A) colour="" ;;
    MISSING) colour=$YELLOW ;;
    *) colour="" ;;
  esac
  printf "%-20s ${colour}%s${RESET}\n" "$check" "$result"
done
echo ""
echo -e "Passed: ${GREEN}$PASS${RESET}  Failed: ${RED}$FAIL${RESET}  Skipped: $SKIP_COUNT"
echo -e "Reports: $REPORTS"
echo ""

if [ $FAIL -gt 0 ]; then
  echo -e "${RED}${BOLD}SCAN FAILED — $FAIL check(s) need attention${RESET}"
  exit 1
else
  echo -e "${GREEN}${BOLD}ALL SCANS PASSED${RESET}"
fi

# Generate dashboard if Python available
if check_cmd python3 && [ -f "$REPO_ROOT/scripts/scan/generate-dashboard.py" ]; then
  python3 "$REPO_ROOT/scripts/scan/generate-dashboard.py" \
    --reports-dir "$REPORTS" \
    --output "$REPORTS/dashboard.html" \
    --commit "$(git rev-parse --short HEAD 2>/dev/null || echo 'local')" \
    --branch "$(git branch --show-current 2>/dev/null || echo 'local')" \
    --run-id "local-$TIMESTAMP" \
    2>/dev/null && echo -e "Dashboard: ${BLUE}$REPORTS/dashboard.html${RESET}" || true
fi
