#!/bin/bash
# Docker Cleanup Script — Scheduled maintenance for build cache, images, and containers
# Usage:
#   - Run manually: ./scripts/docker-cleanup.sh [all|build-cache|images|containers|system]
#   - Add to crontab for weekly/monthly automation
#   - Excludes volumes (data preservation)

set -e

# Configuration
LOG_DIR="${LOG_DIR:-.}"
LOGFILE="${LOG_DIR}/docker-cleanup.log"
VERBOSE=${VERBOSE:-false}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
  local level=$1
  shift
  local message="$@"
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  local log_entry="[$timestamp] [$level] $message"
  
  echo "$log_entry" >> "$LOGFILE"
  
  case $level in
    ERROR)
      echo -e "${RED}[ERROR]${NC} $message" >&2
      ;;
    WARN)
      echo -e "${YELLOW}[WARN]${NC} $message" >&2
      ;;
    INFO)
      echo -e "${GREEN}[INFO]${NC} $message"
      ;;
    DEBUG)
      if [ "$VERBOSE" = "true" ]; then
        echo -e "${BLUE}[DEBUG]${NC} $message"
      fi
      ;;
  esac
}

# Check Docker daemon is running
check_docker() {
  if ! docker ps > /dev/null 2>&1; then
    log ERROR "Docker daemon is not running or not accessible"
    exit 1
  fi
  log INFO "Docker daemon is running"
}

# Get disk usage before and after
get_disk_usage() {
  docker system df --format 'table {{.Type}}\t{{.Size}}\t{{.Reclaimable}}'
}

# Build cache prune (monthly)
cleanup_build_cache() {
  log INFO "=========================================="
  log INFO "Step 1: Build Cache Prune (Monthly)"
  log INFO "=========================================="
  
  BEFORE=$(docker system df --format='{{.BuildCache.Size}}' 2>/dev/null || echo "unknown")
  BEFORE_ENTRIES=$(docker builder du --format='{{.Count}}' 2>/dev/null || echo "unknown")
  
  log INFO "Before: $BEFORE (entries: $BEFORE_ENTRIES)"
  
  if docker builder prune -f 2>&1 | tee -a "$LOGFILE"; then
    AFTER=$(docker system df --format='{{.BuildCache.Size}}' 2>/dev/null || echo "unknown")
    log INFO "After: $AFTER"
    log INFO "✓ Build cache prune completed successfully"
  else
    log ERROR "Build cache prune failed"
    return 1
  fi
}

# Image prune (weekly)
cleanup_images() {
  log INFO "=========================================="
  log INFO "Step 2: Image Prune - Unused Images (Weekly)"
  log INFO "=========================================="
  
  BEFORE=$(docker system df --format='{{.Images.Size}}' 2>/dev/null || echo "unknown")
  IMAGE_COUNT=$(docker images -q | wc -l)
  
  log INFO "Before: $BEFORE (total images: $IMAGE_COUNT)"
  log WARN "This will remove images not used by any running or stopped container"
  
  if docker image prune -a -f 2>&1 | tee -a "$LOGFILE"; then
    AFTER=$(docker system df --format='{{.Images.Size}}' 2>/dev/null || echo "unknown")
    IMAGE_COUNT_AFTER=$(docker images -q | wc -l)
    log INFO "After: $AFTER (total images: $IMAGE_COUNT_AFTER)"
    log INFO "✓ Image prune completed successfully"
  else
    log ERROR "Image prune failed"
    return 1
  fi
}

# Container prune (weekly)
cleanup_containers() {
  log INFO "=========================================="
  log INFO "Step 3: Container Prune - Exited Containers (Weekly)"
  log INFO "=========================================="
  
  EXITED=$(docker ps -a -f status=exited -q | wc -l)
  log INFO "Found $EXITED exited containers"
  
  if [ "$EXITED" -gt 0 ]; then
    if docker container prune -f 2>&1 | tee -a "$LOGFILE"; then
      log INFO "✓ Container prune completed successfully"
    else
      log ERROR "Container prune failed"
      return 1
    fi
  else
    log INFO "No exited containers to prune"
  fi
}

# System-wide prune (quarterly, use sparingly)
cleanup_system() {
  log INFO "=========================================="
  log INFO "Step 4: System Prune - Full Cleanup (Quarterly)"
  log INFO "=========================================="
  log WARN "This is a full system prune. Volumes will NOT be touched."
  
  if docker system prune -f 2>&1 | tee -a "$LOGFILE"; then
    log INFO "✓ System prune completed successfully"
  else
    log ERROR "System prune failed"
    return 1
  fi
}

# Report disk usage
report_disk_usage() {
  log INFO "=========================================="
  log INFO "Final Disk Usage Summary"
  log INFO "=========================================="
  echo ""
  docker system df | tee -a "$LOGFILE"
  echo ""
  
  RECLAIMABLE=$(docker system df --format='{{.Reclaimable}}')
  log INFO "Total reclaimable space: $RECLAIMABLE"
  log INFO "Note: Reclaimable excludes volumes (preserved for data safety)"
}

# Main execution
main() {
  local action="${1:-all}"
  
  # Initialize log file
  if [ ! -f "$LOGFILE" ]; then
    touch "$LOGFILE"
  fi
  
  log INFO "========================================"
  log INFO "Docker Cleanup Script Started"
  log INFO "Action: $action"
  log INFO "========================================"
  
  # Check Docker is running
  check_docker
  
  # Execute requested action
  local result=0
  case "$action" in
    build-cache)
      cleanup_build_cache || result=$?
      ;;
    images)
      cleanup_images || result=$?
      ;;
    containers)
      cleanup_containers || result=$?
      ;;
    system)
      cleanup_system || result=$?
      ;;
    all)
      cleanup_build_cache || result=$?
      cleanup_images || result=$?
      cleanup_containers || result=$?
      ;;
    *)
      log ERROR "Invalid action: $action"
      echo "Usage: $0 {build-cache|images|containers|system|all}"
      exit 1
      ;;
  esac
  
  # Final report
  report_disk_usage
  
  if [ $result -eq 0 ]; then
    log INFO "✓ Cleanup completed successfully"
    exit 0
  else
    log ERROR "✗ Cleanup completed with errors"
    exit 1
  fi
}

# Run main function
main "$@"
