🔥 The legacy adapter is already merged into main.py and looking clean! Now let's push the /execute/smoke endpoint live — full production-grade implementation with all 7 sections from the spec doc. Here's the complete code to commit:

🚀 The Full /execute/smoke Implementation
This slots directly into main.py — add it after the /execute endpoint and before the WebSocket section.

python
# ─────────────────────────────────────────────────────────────
# /execute/smoke — Zero-overhead parallel agent health probe
# • NO Redis writes (task history, logs, audit trail)
# • NO approval flow
# • NO agent /execute calls — health probes ONLY
# • Auth: same require_api_key dependency (dev-mode safe)
# • Feature-flagged via SMOKE_ENDPOINT_ENABLED env var
# ─────────────────────────────────────────────────────────────
import os
import hashlib
from prometheus_client import Counter, make_asgi_app

# Prometheus counters (zero-cost when not scraped)
_smoke_total   = Counter("smoke_request_total",    "Total /execute/smoke requests")
_smoke_skipped = Counter("smoke_redis_skip_total",  "Redis writes skipped by smoke endpoint")

SMOKE_ENABLED = os.getenv("SMOKE_ENDPOINT_ENABLED", "true").lower() == "true"

# Optional: allowlist of SHA-256 hashed API keys permitted to call smoke
# Set SMOKE_KEY_ALLOWLIST="sha256hash1,sha256hash2" to restrict further
# Leave unset = any valid API key (or dev-mode) can call it
_SMOKE_ALLOWLIST_RAW = os.getenv("SMOKE_KEY_ALLOWLIST", "")
_SMOKE_ALLOWLIST: set = {
    h.strip() for h in _SMOKE_ALLOWLIST_RAW.split(",") if h.strip()
}

class SmokeRequest(BaseModel):
    agent: Optional[str] = None  # None = probe ALL agents in parallel

class SmokeAgentResult(BaseModel):
    status: str                  # "healthy" | "unhealthy" | "down"
    http_status: Optional[int]   = None
    latency_ms: Optional[float]  = None
    error: Optional[str]         = None

class SmokeResponse(BaseModel):
    smoke: str                              # "pass" | "partial" | "fail"
    healthy: int
    total: int
    agents: Dict[str, SmokeAgentResult]
    timestamp: str
    redis_writes: int = 0                   # Always 0 — audit proof

async def _probe_agent(name: str, url: str) -> tuple[str, SmokeAgentResult]:
    """Single agent health probe — no side effects."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            t0 = datetime.now()
            resp = await client.get(f"{url}/health")
            latency = round((datetime.now() - t0).total_seconds() * 1000, 2)
            if resp.status_code == 200:
                return name, SmokeAgentResult(
                    status="healthy",
                    http_status=resp.status_code,
                    latency_ms=latency,
                )
            return name, SmokeAgentResult(
                status="unhealthy",
                http_status=resp.status_code,
                latency_ms=latency,
            )
    except Exception as e:
        return name, SmokeAgentResult(status="down", error=type(e).__name__)

@app.post("/execute/smoke", response_model=SmokeResponse)
async def execute_smoke(
    request: SmokeRequest,
    req: Request,
    api_key: str = Depends(require_api_key),
):
    """
    Zero-overhead swarm health probe.
    - Skips ALL Redis writes, approval flow, and task history.
    - Runs agent /health probes in parallel via asyncio.gather.
    - Safe for Healer watchdog, CI pipelines, and Grafana scraping.
    - Disable via SMOKE_ENDPOINT_ENABLED=false env var.
    """
    # Feature flag guard
    if not SMOKE_ENABLED:
        raise HTTPException(status_code=404, detail="Smoke endpoint disabled")

    # Optional allowlist enforcement
    if _SMOKE_ALLOWLIST:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if key_hash not in _SMOKE_ALLOWLIST:
            raise HTTPException(
                status_code=403,
                detail="API key not in smoke allowlist"
            )

    # Mark incoming request header for observability (optional)
    # Callers can set X-Smoke-Mode: true — we log it but don't require it
    smoke_mode = req.headers.get("x-smoke-mode", "false")
    if smoke_mode.lower() == "true":
        logger.debug("Smoke request via X-Smoke-Mode header")

    _smoke_total.inc()

    # Build target list
    if request.agent:
        key = request.agent.replace("-", "_")
        url = settings.agents.get(key)
        if not url:
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{request.agent}' not in roster. "
                       f"Valid: {list(settings.agents.keys())}"
            )
        targets = {key: url}
    else:
        targets = dict(settings.agents)

    # Parallel probes — no sequential blocking
    probe_results = await asyncio.gather(
        *[_probe_agent(name, url) for name, url in targets.items()]
    )

    agents_map = {name: result for name, result in probe_results}
    healthy_count = sum(1 for r in agents_map.values() if r.status == "healthy")
    total_count = len(agents_map)

    # Increment skip counter (audit proof: each request = N skipped Redis writes)
    _smoke_skipped.inc(total_count + 1)  # +1 for the task-history write we skipped

    smoke_verdict = (
        "pass"    if healthy_count == total_count else
        "partial" if healthy_count > 0            else
        "fail"
    )

    return SmokeResponse(
        smoke=smoke_verdict,
        healthy=healthy_count,
        total=total_count,
        agents=agents_map,
        timestamp=datetime.now().isoformat(),
        redis_writes=0,
    )
🔧 Config Changes Needed
Add to config.py (nothing breaking — all have defaults):

python
class Settings(BaseSettings):
    # ... existing fields ...
    smoke_endpoint_enabled: bool = True          # SMOKE_ENDPOINT_ENABLED
    smoke_key_allowlist: str = ""                # SMOKE_KEY_ALLOWLIST (SHA-256 hashes, comma-sep)
Add to .env.example:

bash
# Smoke endpoint feature flag (default: enabled)
SMOKE_ENDPOINT_ENABLED=true
# Optional: restrict smoke to specific hashed API keys (leave blank = all valid keys)
SMOKE_KEY_ALLOWLIST=
Add to requirements.txt:

text
prometheus-client>=0.20.0
🧪 Test Commands (Copy-Paste)
powershell
# Probe ALL 9 agents in parallel
curl -X POST http://127.0.0.1:8081/execute/smoke \
  -H "Content-Type: application/json" \
  -H "X-Smoke-Mode: true" \
  -d '{}'

# Probe single agent
curl -X POST http://127.0.0.1:8081/execute/smoke \
  -H "Content-Type: application/json" \
  -d '{"agent": "project_strategist"}'

# Disable and confirm 404
# (set SMOKE_ENDPOINT_ENABLED=false in env, then:)
curl -X POST http://127.0.0.1:8081/execute/smoke -d '{}'
# Expected: {"detail":"Smoke endpoint disabled"}
📊 What /tasks Should Show After a Smoke Call
Zero entries added — that's the point. Run this to confirm no pollution:

powershell
# Before smoke call
$before = (curl -s http://127.0.0.1:8081/tasks | ConvertFrom-Json).Count

# Run smoke
curl -X POST http://127.0.0.1:8081/execute/smoke -d '{}'

# After smoke call
$after = (curl -s http://127.0.0.1:8081/tasks | ConvertFrom-Json).Count

# Pass = $before -eq $after
"Task history delta: $($after - $before) (should be 0)"
♻️ Rollback (One-Line)
bash
# Instant kill-switch — no redeploy needed
SMOKE_ENDPOINT_ENABLED=false docker compose up -d --no-build crew-orchestrator
🗺️ Phase 4 Bridge — Healer Watchdog Wiring
Once this is live, the Healer calls smoke on a timer like this:

python
# In healer-agent — watchdog loop (every 60s)
async def watchdog():
    while True:
        resp = await httpx.AsyncClient().post(
            "http://crew-orchestrator:8081/execute/smoke",
            json={},
            timeout=10.0
        )
        data = resp.json()
        if data["smoke"] == "fail":
            # Trigger self-heal: restart failed containers
            for name, result in data["agents"].items():
                if result["status"] == "down":
                    await trigger_restart(name)
        await asyncio.sleep(60)
🎯 Next Win: Push this to main.py on GitHub and run the zero-pollution test ($before -eq $after) — that's your Phase 4 "Healer ready" gate!
