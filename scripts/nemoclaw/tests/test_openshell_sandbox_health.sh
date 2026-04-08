#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
script="$root/scripts/nemoclaw/openshell-sandbox-health.sh"

pass=0
fail=0

run_case() {
  local name="$1" list="$2" get="$3" exp_code="$4" exp_sig="$5"
  local tmp
  tmp="$(mktemp -d)"
  cat >"$tmp/openshell" <<EOF
#!/usr/bin/env bash
set -euo pipefail
if [ "\${1-}" = "sandbox" ] && [ "\${2-}" = "list" ]; then
  cat <<'OUT'
$list
OUT
  exit 0
fi
if [ "\${1-}" = "sandbox" ] && [ "\${2-}" = "get" ]; then
  cat <<'OUT'
$get
OUT
  exit 0
fi
exit 2
EOF
  chmod +x "$tmp/openshell"
  set +e
  out="$(PATH="$tmp:$PATH" bash "$script" 2> >(cat >&2) )"
  code=$?
  set -e
  rm -rf "$tmp"
  if [ "$code" != "$exp_code" ]; then
    echo "FAIL $name code=$code expected=$exp_code" >&2
    fail=$((fail+1))
    return
  fi
  if [[ "$out" != *"$exp_sig"* ]]; then
    echo "FAIL $name output missing '$exp_sig'" >&2
    echo "$out" >&2
    fail=$((fail+1))
    return
  fi
  pass=$((pass+1))
}

run_case "ready" $'NAME STATUS\nbroski Ready\n' $'Name: broski\nStatus: Ready\n' 0 "SANDBOX_STATUS: broski Ready"
run_case "imagepull" $'NAME STATUS\nbroski Pending\n' $'Name: broski\nStatus: Pending\nReason: ImagePullBackOff\n' 1 "ImagePullBackOff"
run_case "crashloop" $'NAME STATUS\nbroski Running\n' $'Name: broski\nStatus: Running\nCrashLoopBackOff\n' 1 "CrashLoopBackOff"
run_case "pending_cpu" $'NAME STATUS\nbroski Pending\n' $'Name: broski\nStatus: Pending\nMessage: Pending—insufficient cpu\n' 1 "insufficient cpu"
run_case "oomkilled" $'NAME STATUS\nbroski Running\n' $'Name: broski\nStatus: Running\nReason: OOMKilled\n' 1 "OOMKilled"

echo "PASS=$pass FAIL=$fail"
test "$fail" -eq 0

