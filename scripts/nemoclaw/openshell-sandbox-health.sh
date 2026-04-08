#!/usr/bin/env bash
set -euo pipefail

sandbox="broski"
list_out="$(openshell sandbox list 2>&1 || true)"
get_out="$(openshell sandbox get "$sandbox" 2>&1 || true)"

status=""
reason=""

if [[ "$get_out" =~ [Ss]tatus:[[:space:]]*([A-Za-z0-9._-]+) ]]; then status="${BASH_REMATCH[1]}"; fi
if [[ -z "$status" && "$get_out" =~ [Pp]hase:[[:space:]]*([A-Za-z0-9._-]+) ]]; then status="${BASH_REMATCH[1]}"; fi
if [[ -z "$status" && "$get_out" =~ [Rr]eady:[[:space:]]*(true|false|True|False|READY|Ready|NotReady|NOTREADY) ]]; then status="${BASH_REMATCH[1]}"; fi

if [[ "$get_out" =~ [Rr]eason:[[:space:]]*([A-Za-z0-9._-]+) ]]; then reason="${BASH_REMATCH[1]}"; fi
if [[ -z "$reason" && "$get_out" =~ (insufficient[^$'\n']*(cpu|memory)|Insufficient[^$'\n']*(cpu|memory)) ]]; then reason="${BASH_REMATCH[1]}"; fi
if [[ -z "$reason" && "$get_out" =~ (ImagePullBackOff|CrashLoopBackOff|ErrImagePull|CreateContainerConfigError|RunContainerError|OOMKilled|ContainerCreating|Terminating|Failed|Error) ]]; then reason="${BASH_REMATCH[1]}"; fi

if [[ -z "$status" && "$list_out" =~ (^|$'\n')${sandbox}[[:space:]]+([^$'\n']+) ]]; then status="${BASH_REMATCH[2]}"; fi

sig="${reason:-${status:-unknown}}"

if [[ "$status" =~ ^(Ready|READY|true|True)$ ]]; then
  printf "SANDBOX_STATUS: %s Ready\n" "$sandbox"
  exit 0
fi

printf "SANDBOX_STATUS: %s NOT_READY (%s)\n" "$sandbox" "$sig"
printf "SANDBOX_NOT_READY: %s\n" "$sig" >&2
exit 1
