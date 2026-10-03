#!/bin/bash
# Measure the HyperCrew success RATE: N live crew runs, one at a time, RAM-guard + core-health check before each.
# Prints one RESULT line per run (outcome ALLOW | BLOCK + failed checks + the verifier's detail | FAILED | STUCK) and a summary.
# ALWAYS rejects the handover gate (no draft PR can open). Each ALLOW run settles XP/coins to the owner account, as any run does.
#
#   MSYS_NO_PATHCONV=1 bash scripts/measure-crew-rate.sh                  # the 5 default goals
#   MSYS_NO_PATHCONV=1 bash scripts/measure-crew-rate.sh "goal one" "goal two"
#
# Needs: core + crew-orchestrator + coder-agent + qa-engineer + safety-shepherd + fcc-proxy healthy. Uses the real model
# (fcc-proxy -> NVIDIA NIM): crew text is sent to NVIDIA. Goals must avoid the words health/metrics/deploy/docker/"todo list".
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.." || exit 1
if [ $# -gt 0 ]; then GOALS=("$@"); else GOALS=(
  "add a version endpoint to the API"
  "add a /ping endpoint that returns pong"
  "add a function that converts celsius to fahrenheit"
  "add a helper that turns a string into a url slug"
  "add a README section explaining how to run the tests"
); fi
results=()
for goal in "${GOALS[@]}"; do
  python scripts/ram_guard.py --for check >/dev/null 2>&1; rc=$?
  if [ $rc -ge 2 ]; then echo "ABORT: RAM guard RED (exit $rc) before: $goal"; break; fi
  st=$(docker inspect -f '{{.State.Health.Status}}' hypercode-core 2>/dev/null)
  if [ "$st" != "healthy" ]; then echo "ABORT: core is '$st' before: $goal"; break; fi
  echo "START $(date -u +%H:%M:%SZ) guard_exit=$rc :: $goal"
  line=$(timeout 560 docker exec -e MEASURE_GOAL="$goal" -i hypercode-core python - < scripts/measure-crew-run.py 2>&1 | grep -E "^RESULT" | tail -1)
  echo "${line:-RESULT {\"goal\": \"$goal\", \"outcome\": \"FAILED\", \"error\": \"no result line\"}}"
  results+=("${line:-FAILED}")
done
python - "${results[@]}" <<'PY'
import json, sys, collections
rows = [json.loads(a[7:]) for a in sys.argv[1:] if a.startswith("RESULT ")]
c = collections.Counter(r.get("outcome") for r in rows)
n = len(sys.argv) - 1
print(f"SUMMARY: {n} runs -> " + ", ".join(f"{k} {v}" for k, v in sorted(c.items())))
secs = [r["seconds"] for r in rows if r.get("seconds")]
if secs:
    print(f"seconds per run: min {min(secs)} max {max(secs)} mean {sum(secs)/len(secs):.0f}")
for r in rows:
    if r.get("outcome") != "ALLOW":
        print(f"  not ALLOW: {r.get('goal')!r} -> {r.get('outcome')} {r.get('failed_checks') or ''} {r.get('verifier_detail') or r.get('error') or ''}")
PY
