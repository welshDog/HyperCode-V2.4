#!/usr/bin/env bash
# ================================================
# HyperCode Security Test Runner
# Outputs: reports/bandit-report.json
#          reports/npm-audit.json
# ================================================
set -euo pipefail

mkdir -p reports

echo "\n\uD83D\uDD12 Running Bandit (Python static security scan)..."
pip install bandit -q
bandit -r backend/ agents/ \
  --format json \
  --output reports/bandit-report.json \
  --confidence-level medium \
  --severity-level medium \
  || echo "Bandit found issues — check reports/bandit-report.json"

echo "\n\uD83D\uDCE6 Running npm audit (frontend dependencies)..."
cd agents/dashboard
npm audit --json > ../../reports/npm-audit.json \
  || echo "npm audit found issues — check reports/npm-audit.json"
cd ../..

echo "\n\uD83D\uDD0D Running detect-secrets scan..."
pip install detect-secrets -q
detect-secrets scan --all-files \
  --exclude-files 'package-lock\.json' \
  --exclude-files '\.secrets\.baseline' \
  > reports/secrets-scan.json \
  || true

echo "\n✅ Security scan complete — check reports/ directory"
