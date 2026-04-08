#!/usr/bin/env bash
set -euo pipefail

name="openshell-cluster-nemoclaw"

if ! docker ps -a --format '{{.Names}}' | grep -qx "$name"; then
  echo "Container not found: $name" >&2
  exit 1
fi

docker update \
  --health-interval 30s \
  --health-timeout 30s \
  --health-start-period 90s \
  --health-retries 3 \
  "$name" >/dev/null

docker ps -a --filter "name=$name" --format 'table {{.Names}}\t{{.Status}}'

