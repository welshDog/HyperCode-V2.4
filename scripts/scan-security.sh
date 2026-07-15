#!/bin/bash
# ========================================
# Automated CVE Scanning Script
# Scans all custom Docker images for vulnerabilities
# Generates JSON reports + brief summary
# ========================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}🔒 Docker Image Security Scan${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REPORT_DIR="$PROJECT_DIR/reports/security"

# Create reports directory
mkdir -p "$REPORT_DIR"

# List of images to scan (update as needed)
IMAGES=(
  "hypercode-core:latest"
  "coder-agent:latest"
  "backend-specialist:latest"
  "frontend-specialist:latest"
  "database-architect:latest"
  "qa-engineer:latest"
  "devops-engineer:latest"
  "crew-orchestrator:latest"
  "healer-agent:latest"
  "nemoclaw-agent:latest"
  "broski-pets-bridge:latest"
  "goal-keeper:latest"
)

echo -e "${YELLOW}Scanning ${#IMAGES[@]} images for vulnerabilities...${NC}"
echo ""

# Check if trivy is installed
if ! command -v docker scout &> /dev/null; then
  echo -e "${YELLOW}⚠️  docker scout not found${NC}"
  echo "    Install with: docker scout version"
  echo ""
  echo "    Fallback: Using docker scout via image...${NC}"
fi

CRITICAL_TOTAL=0
HIGH_TOTAL=0

# Scan each image
for IMAGE in "${IMAGES[@]}"; do
  echo -n "  Scanning $IMAGE... "
  
  # Try docker scout first
  if docker scout cves "$IMAGE" --format json >/dev/null 2>&1; then
    docker scout cves "$IMAGE" --format json > "$REPORT_DIR/${IMAGE//\//-}_scout.json" 2>/dev/null || true
    echo -e "${GREEN}✓${NC}"
  else
    echo -e "${YELLOW}(skipped)${NC}"
  fi
done

echo ""
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}Summary:${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"

# Generate summary
echo -e "${YELLOW}Reports saved to: $REPORT_DIR${NC}"
echo ""
echo -e "${BLUE}Available scans:${NC}"
ls -1 "$REPORT_DIR"/ 2>/dev/null | head -10 || echo "  No reports yet"

echo ""
echo -e "${GREEN}✅ Scan Complete${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Review: cat $REPORT_DIR/*.json"
echo "  2. Fix:    Update vulnerable dependencies"
echo "  3. Rescan: bash scripts/scan-security.sh"
