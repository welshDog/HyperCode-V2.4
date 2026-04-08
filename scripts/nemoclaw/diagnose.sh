#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
logs_dir="$root/logs/nemoclaw"

export PATH="$HOME/.local/bin:$PATH"
if [ -d "$HOME/.nvm/versions/node" ]; then
  latest="$(ls -1 "$HOME/.nvm/versions/node" | sort -V | tail -n 1)"
  if [ -n "$latest" ]; then
    export PATH="$HOME/.nvm/versions/node/$latest/bin:$PATH"
  fi
fi

printf "%s\n" "NemoClaw diagnostics"
printf "%s\n" "repo_root=$root"
printf "%s\n" "logs_dir=$logs_dir"
printf "\n"

shopt -s nullglob
files=("$logs_dir"/*.log)
if [ "${#files[@]}" -eq 0 ]; then
  echo "No log files found under $logs_dir" >&2
  exit 1
fi

printf "%s\n" "Recent logs:"
ls -1t "$logs_dir"/*.log | head -n 15 | sed "s|^| - |"
printf "\n"

count_match() {
  local pat="$1"
  local n=0
  local f
  for f in "${files[@]}"; do
    if grep -qE "$pat" "$f"; then
      n=$((n+1))
    fi
  done
  echo "$n"
}

docker_not_running="$(count_match "Docker is not running")"
docker_build_stream="$(count_match "Docker build stream error")"
docker_body_read="$(count_match "error reading a body from connection")"
containerd_mount_notfound="$(count_match "failed to export layer: CreateDiff: NotFound")"
npm_exit_handler="$(count_match "Exit handler never called")"

printf "%s\n" "Failure pattern counts (number of logs containing the pattern):"
printf "%s\n" " - Docker not running / not reachable: $docker_not_running"
printf "%s\n" " - Docker build stream error:          $docker_build_stream"
printf "%s\n" " - Docker connection read error:       $docker_body_read"
printf "%s\n" " - containerd mount/lease errors:      $containerd_mount_notfound"
printf "%s\n" " - npm exit handler error:             $npm_exit_handler"
printf "\n"

printf "%s\n" "Runtime checks:"
if docker ps >/dev/null 2>&1; then
  printf "%s\n" " - Docker reachable: yes"
else
  printf "%s\n" " - Docker reachable: no"
fi

if command -v nemoclaw >/dev/null 2>&1; then
  printf "%s\n" " - nemoclaw on PATH: yes"
else
  printf "%s\n" " - nemoclaw on PATH: no"
fi

if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx 'openshell-cluster-nemoclaw'; then
  printf "%s\n" " - openshell-cluster-nemoclaw: present"
  docker ps -a --filter name=openshell-cluster-nemoclaw --format '   {{.Names}}  {{.Status}}' || true
else
  printf "%s\n" " - openshell-cluster-nemoclaw: not present"
fi
printf "\n"

printf "%s\n" "Recommended fixes (fastest first):"
if [ "$docker_not_running" -gt 0 ]; then
  printf "%s\n" " - Ensure Docker Desktop is running and WSL integration is enabled for Ubuntu-22.04."
fi
if [ "$docker_build_stream" -gt 0 ] || [ "$containerd_mount_notfound" -gt 0 ] || [ "$docker_body_read" -gt 0 ]; then
  printf "%s\n" " - Restart Docker Desktop to reset containerd/buildkit state."
  printf "%s\n" " - Free disk space and prune builder cache if space is tight."
fi
if [ "$npm_exit_handler" -gt 0 ]; then
  printf "%s\n" " - Re-run onboarding once after Docker restart; npm failures during image build are often transient under Docker Desktop load."
fi
printf "%s\n" " - Avoid repeated onboarding runs; if a sandbox exists, onboarding is not needed."
printf "%s\n" " - If OpenShell cluster stays unhealthy due to healthcheck timeouts, run: scripts/nemoclaw/tune-openshell-health.ps1"
printf "\n"

printf "%s\n" "Done."
