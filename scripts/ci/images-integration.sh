#!/usr/bin/env bash
# Runtime integration test for the images docker-push.yml publishes.
# Starts each published :latest image on a throwaway network (with Redis where it needs it)
# and makes real requests, instead of only building/importing them. Every check is reported;
# the script exits non-zero if any failed. Used by .github/workflows/images-integration.yml.
set -u

REG="${REGISTRY_PREFIX:?set REGISTRY_PREFIX, e.g. ghcr.io/welshdog/hypercode-v2.4}"
NET=itest
PASS=0
FAIL=0
RESULTS=()
CONTAINERS=()

ok()  { PASS=$((PASS+1)); RESULTS+=("PASS  $1"); echo "PASS  $1"; }
bad() { FAIL=$((FAIL+1)); RESULTS+=("FAIL  $1  ($2)"); echo "FAIL  $1  ($2)"; }

cleanup() {
  for c in "${CONTAINERS[@]:-}"; do [ -n "$c" ] && docker rm -f "$c" >/dev/null 2>&1; done
  docker compose -f /tmp/itest-compose.yml -p itest down -v >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT

start() { # name image hostport containerport [docker run args...]
  local name=$1 image=$2 hp=$3 cp=$4; shift 4
  CONTAINERS+=("$name")
  docker run -d --name "$name" --network "$NET" -p "127.0.0.1:${hp}:${cp}" "$@" "$REG/$image:latest" >/dev/null
}

wait_http() { # url [tries] [curl args...]
  local url=$1 tries=${2:-40}; shift 2 2>/dev/null || shift 1
  for _ in $(seq 1 "$tries"); do
    if curl -fsS -m 3 "$@" "$url" >/dev/null 2>&1; then return 0; fi
    sleep 2
  done
  return 1
}

logs_of() { echo "----- logs: $1 -----"; docker logs --tail 25 "$1" 2>&1 | sed 's/^/    /'; }

running_nonroot() { # container
  local uid; uid=$(docker exec "$1" id -u 2>/dev/null)
  [ -n "$uid" ] && [ "$uid" != "0" ]
}

docker network create "$NET" >/dev/null
CONTAINERS+=(itest-redis)
docker run -d --name itest-redis --network "$NET" redis:7-alpine >/dev/null

echo "== pulling images"
for img in hypercode-dashboard hypercode-hyper-architect hypercode-devops-engineer hypercode-coder hypercode-test-agent \
           hypercode-goal-keeper hypercode-session-snapshot hypercode-hypercode-mcp-server agent-spawner; do
  docker pull -q "$REG/$img:latest" >/dev/null 2>&1 || echo "pull failed: $img"
done

# ---- dashboard (Next.js, built in CI instead of locally) -------------------------------------------
n=dashboard
start itest-dashboard hypercode-dashboard 18088 3000
if wait_http http://127.0.0.1:18088/health 45; then
  ok "$n /health"
  curl -fsS -o /dev/null -m 10 http://127.0.0.1:18088/ && ok "$n /" || bad "$n /" "non-200"
  curl -fsS -m 10 http://127.0.0.1:18088/ide | grep -qi "HyperCode" && ok "$n /ide renders" || bad "$n /ide renders" "no HyperCode in page"
  running_nonroot itest-dashboard && ok "$n runs non-root" || bad "$n runs non-root" "uid 0"
  # its own health probe is a docker exec of node: a container whose rootfs mount is broken fails exactly here
  docker exec itest-dashboard node -e "process.exit(0)" >/dev/null 2>&1 && ok "$n docker exec works" || bad "$n docker exec works" "exec failed"
else bad "$n starts" "no /health in 90s"; logs_of itest-dashboard; fi

# ---- hyper-architect (NestJS, npm removed from runtime) ------------------------------------------
n=hyper-architect
start itest-architect hypercode-hyper-architect 18080 8080
if wait_http http://127.0.0.1:18080/health 30; then
  body=$(curl -fsS http://127.0.0.1:18080/health)
  echo "$body" | grep -q '"status":"ok"' && ok "$n /health" || bad "$n /health" "$body"
  curl -fsS http://127.0.0.1:18080/info | grep -q architect && ok "$n /info" || bad "$n /info" "no 'architect'"
  running_nonroot itest-architect && ok "$n runs non-root" || bad "$n runs non-root" "uid 0"
  docker exec itest-architect sh -c 'command -v npm' >/dev/null 2>&1 && bad "$n npm removed" "npm present" || ok "$n npm removed"
else bad "$n starts" "no /health in 60s"; logs_of itest-architect; fi

# ---- devops-engineer (compose + kubectl removed) --------------------------------------------------
n=devops-engineer
start itest-devops hypercode-devops-engineer 18081 8080 -e AGENT_PORT=8080 -e REDIS_URL=redis://itest-redis:6379
if wait_http http://127.0.0.1:18081/health 40; then
  ok "$n /health"
  running_nonroot itest-devops && ok "$n runs non-root" || bad "$n runs non-root" "uid 0"
  docker exec itest-devops docker --version >/dev/null 2>&1 && ok "$n docker CLI present" || bad "$n docker CLI present" "missing"
  docker exec itest-devops sh -c 'command -v kubectl || test -e /usr/libexec/docker/cli-plugins/docker-compose' >/dev/null 2>&1 \
    && bad "$n kubectl/compose removed" "still present" || ok "$n kubectl/compose removed"
else bad "$n starts" "no /health in 80s"; logs_of itest-devops; fi

# ---- coder (pipx shared pip removed, docker-mcp venv) ---------------------------------------------
n=coder
start itest-coder hypercode-coder 18082 8080 -e AGENT_PORT=8080 -e AGENT_NAME=coder-agent -e REDIS_URL=redis://itest-redis:6379
if wait_http http://127.0.0.1:18082/health 45; then
  ok "$n /health"
  running_nonroot itest-coder && ok "$n runs non-root" || bad "$n runs non-root" "uid 0"
else bad "$n starts" "no /health in 90s"; logs_of itest-coder; fi
out=$(docker exec itest-coder sh -c 'timeout 15 docker-mcp </dev/null 2>&1; echo "rc=$?"' 2>&1 | tail -15)
if echo "$out" | grep -qE "Traceback|ModuleNotFoundError|ImportError|No module named|not found"; then
  bad "$n docker-mcp launches" "$(echo "$out" | tr '\n' ' ' | cut -c1-200)"
else ok "$n docker-mcp launches (no import errors)"; fi
docker exec itest-coder sh -c 'test ! -d /opt/pipx/shared/lib/python3.12/site-packages/pip' && ok "$n shared pip removed" || bad "$n shared pip removed" "present"

# ---- generic python agents ------------------------------------------------------------------------
gen() { # label image hostport envs...
  local label=$1 image=$2 hp=$3; shift 3
  start "itest-$label" "$image" "$hp" 8080 "$@"
  if wait_http "http://127.0.0.1:${hp}/health" 40; then
    ok "$label /health"
    running_nonroot "itest-$label" && ok "$label runs non-root" || bad "$label runs non-root" "uid 0"
  else bad "$label starts" "no /health in 80s"; logs_of "itest-$label"; fi
}
gen test-agent hypercode-test-agent 18083 -e REDIS_URL=redis://itest-redis:6379
gen goal-keeper hypercode-goal-keeper 18084 -e AGENT_PORT=8080 -e REDIS_URL=redis://itest-redis:6379
gen session-snapshot hypercode-session-snapshot 18085 -e PORT=8080 -e REDIS_URL=redis://itest-redis:6379

# ---- hypercode-mcp-server (mcp 1.28.1): real MCP session over SSE ---------------------------------
n=mcp-server
start itest-mcp hypercode-hypercode-mcp-server 18823 8823 -e HYPERCODE_CORE_URL=http://127.0.0.1:1 -e HYPERCODE_ORCH_URL=http://127.0.0.1:1
if wait_http http://127.0.0.1:18823/health 30; then
  ok "$n /health (host-allowlist ok)"
  running_nonroot itest-mcp && ok "$n runs non-root" || bad "$n runs non-root" "uid 0"
  res=$(docker exec -i itest-mcp python - <<'PY' 2>&1
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    async with sse_client("http://localhost:8823/sse") as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = [t.name for t in (await s.list_tools()).tools]
            assert "hypercode_system_health" in tools, tools
            print("TOOLS", len(tools))
            res = await asyncio.wait_for(s.call_tool("hypercode_system_health", {}), 30)
            print("CALL_OK", res.isError, str(res.content)[:120].replace("\n", " "))

asyncio.run(asyncio.wait_for(main(), 90))
PY
)
  echo "$res" | tail -4 | sed 's/^/    /'
  echo "$res" | grep -q "^TOOLS" && echo "$res" | grep -q "^CALL_OK" \
    && ok "$n MCP session: initialize + list_tools + call_tool" || bad "$n MCP session" "$(echo "$res" | tail -2 | tr '\n' ' ' | cut -c1-200)"
else bad "$n starts" "no /health in 60s"; logs_of itest-mcp; fi

# ---- skillweaver (+redis) and memstream -----------------------------------------------------------
n=skillweaver
# skillweaver/memstream are not pushed by docker-push.yml: build them from this checkout instead.
docker build -q -t itest-skillweaver -f services/skillweaver/Dockerfile . >/dev/null 2>&1 || bad "$n build" "docker build failed"
CONTAINERS+=(itest-skillweaver)
docker run -d --name itest-skillweaver --network "$NET" -p 127.0.0.1:18051:8051 -e REDIS_URL=redis://itest-redis:6379 itest-skillweaver >/dev/null
if wait_http http://127.0.0.1:18051/health 40; then
  h=$(curl -fsS http://127.0.0.1:18051/health)
  echo "$h" | grep -q '"redis_connected":true' && ok "$n /health with redis_connected=true" || bad "$n redis_connected" "$h"
  running_nonroot itest-skillweaver && ok "$n runs non-root" || bad "$n runs non-root" "uid 0"
  reg=$(curl -sS -m 10 -X POST http://127.0.0.1:18051/api/v1/skills/register -H 'content-type: application/json' \
    -d '{"skill_id":"itest.echo","agent_id":"itest-agent","name":"Echo","description":"Echo text back to the caller","category":"io","inputs":{"text":"string"},"outputs":{"text":"string"}}')
  echo "$reg" | grep -q '"status":"registered"' && ok "$n register skill" || bad "$n register skill" "$reg"
  disc=$(curl -sS -m 10 -X POST http://127.0.0.1:18051/api/v1/skills/discover -H 'content-type: application/json' -d '{"query":"echo text back","top_k":3}')
  echo "$disc" | grep -q 'itest.echo' && ok "$n discover finds the registered skill" || bad "$n discover" "$(echo "$disc" | cut -c1-200)"
  curl -fsS -m 10 http://127.0.0.1:18051/api/v1/skills/itest.echo | grep -q 'itest.echo' && ok "$n get skill" || bad "$n get skill" "not found"
else bad "$n starts" "no /health in 80s"; logs_of itest-skillweaver; fi

n=memstream
docker build -q -t itest-memstream memstream >/dev/null 2>&1 || bad "$n build" "docker build failed"
CONTAINERS+=(itest-memstream)
docker run -d --name itest-memstream --network "$NET" -p 127.0.0.1:18009:8009 itest-memstream >/dev/null
if wait_http http://127.0.0.1:18009/health 30; then
  ok "$n /health"
  running_nonroot itest-memstream && ok "$n runs non-root" || bad "$n runs non-root" "uid 0"
  curl -fsS http://127.0.0.1:18009/health/memstream | grep -q timestamp && ok "$n /health/memstream" || bad "$n /health/memstream" "no timestamp"
  curl -fsS -X POST http://127.0.0.1:18009/throttle -H 'content-type: application/json' -d '{"delay_ms":50}' | grep -q '"ok":true' \
    && ok "$n POST /throttle" || bad "$n POST /throttle" "no ok:true"
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:18009/throttle -H 'content-type: application/json' -d '{}')
  [ "$code" = "400" ] && ok "$n /throttle rejects bad body (400)" || bad "$n /throttle bad body" "got $code"
else bad "$n starts" "no /health in 60s"; logs_of itest-memstream; fi

# ---- agent-spawner: source-built Compose really spawns a container --------------------------------
n=agent-spawner
cat > /tmp/itest-compose.yml <<'YML'
services:
  probe:
    image: alpine:3.20
    command: ["sleep", "120"]
YML
cv=$(docker run --rm --entrypoint docker "$REG/agent-spawner:latest" compose version 2>&1)
echo "$cv" | grep -q "v5.6.0" && ok "$n compose version v5.6.0 ($cv)" || bad "$n compose version" "$cv"
up=$(docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v /tmp/itest-compose.yml:/work/compose.yml:ro \
      -w /work --entrypoint docker "$REG/agent-spawner:latest" compose -f compose.yml -p itest up -d 2>&1)
if docker ps --filter label=com.docker.compose.project=itest --format '{{.Names}}' | grep -q probe; then
  ok "$n docker compose up -d spawned a container through the socket"
else bad "$n compose up -d" "$(echo "$up" | tail -3 | tr '\n' ' ' | cut -c1-200)"; fi
down=$(docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v /tmp/itest-compose.yml:/work/compose.yml:ro \
      -w /work --entrypoint docker "$REG/agent-spawner:latest" compose -f compose.yml -p itest down 2>&1)
docker ps -a --filter label=com.docker.compose.project=itest --format '{{.Names}}' | grep -q probe \
  && bad "$n compose down" "$(echo "$down" | tail -2 | tr '\n' ' ')" || ok "$n docker compose down cleaned up"
CONTAINERS+=(itest-spawner)
docker run -d --name itest-spawner --network "$NET" -v /var/run/docker.sock:/var/run/docker.sock \
  -e REDIS_URL=redis://itest-redis:6379/0 "$REG/agent-spawner:latest" >/dev/null
sleep 8
[ "$(docker inspect -f '{{.State.Running}}' itest-spawner)" = "true" ] && ok "$n service stays up with redis" || { bad "$n service stays up" "exited"; logs_of itest-spawner; }

echo
echo "================ SUMMARY ================"
printf '%s\n' "${RESULTS[@]}"
echo "passed=$PASS failed=$FAIL"
[ "$FAIL" -eq 0 ]
