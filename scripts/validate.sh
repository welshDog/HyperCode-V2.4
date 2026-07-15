#!/usr/bin/env bash
# Validate dashboard JSON files before promotion
# Checks: valid JSON, uid present, no duplicate UIDs across all dashboards

set -euo pipefail

DASHBOARD_DIR="${1:-dashboards}"
ERRORS=0

echo "🔍 Validating dashboards in $DASHBOARD_DIR/"

# Check each file is valid JSON and has a uid
while IFS= read -r -d '' file; do
  if ! jq empty "$file" 2>/dev/null; then
    echo "❌ Invalid JSON: $file"
    ((ERRORS++))
    continue
  fi

  UID=$(jq -r '.uid // empty' "$file")
  if [[ -z "$UID" ]]; then
    echo "❌ Missing uid: $file"
    ((ERRORS++))
  else
    echo "✅ $file (uid: $UID)"
  fi
done < <(find "$DASHBOARD_DIR" -name '*.json' -print0 2>/dev/null)

# Check for duplicate UIDs
echo ""
echo "🔍 Checking for duplicate UIDs..."
DUPS=$(find "${DASHBOARD_DIR}" -name '*.json' -exec jq -r '.uid // empty' {} \; 2>/dev/null | sort | uniq -d)
if [[ -n "$DUPS" ]]; then
  echo "❌ Duplicate UIDs found: $DUPS"
  ((ERRORS++))
else
  echo "✅ All UIDs are unique"
fi

if [[ $ERRORS -gt 0 ]]; then
  echo ""
  echo "❌ Validation failed with $ERRORS error(s)"
  exit 1
fi

echo ""
echo "✅ All dashboards valid — ready to promote"
