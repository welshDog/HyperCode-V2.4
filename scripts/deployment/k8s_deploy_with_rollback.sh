#!/usr/bin/env bash

set -euo pipefail

NAMESPACE="${1:-hypercode}"
MANIFEST_PATH="${2:-k8s/}"
SELECTOR="${3:-}"

kubectl apply -n "$NAMESPACE" -f "$MANIFEST_PATH"

if [[ -n "$SELECTOR" ]]; then
  mapfile -t DEPLOYMENTS < <(kubectl get deploy -n "$NAMESPACE" -l "$SELECTOR" -o name)
  mapfile -t STATEFULSETS < <(kubectl get sts -n "$NAMESPACE" -l "$SELECTOR" -o name)
else
  mapfile -t DEPLOYMENTS < <(kubectl get deploy -n "$NAMESPACE" -o name)
  mapfile -t STATEFULSETS < <(kubectl get sts -n "$NAMESPACE" -o name)
fi

rollback_deploy() {
  local res="$1"
  kubectl rollout undo -n "$NAMESPACE" "$res" || true
  kubectl rollout status -n "$NAMESPACE" "$res" --timeout=5m || true
}

for d in "${DEPLOYMENTS[@]}"; do
  if ! kubectl rollout status -n "$NAMESPACE" "$d" --timeout=5m; then
    rollback_deploy "$d"
    exit 1
  fi
done

for s in "${STATEFULSETS[@]}"; do
  if ! kubectl rollout status -n "$NAMESPACE" "$s" --timeout=10m; then
    rollback_deploy "$s"
    exit 1
  fi
done
