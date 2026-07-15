"""Unified Agent Registry for the HyperCode V2.4 swarm.

Tracks every agent in the fleet — name, role, status, last_ping, error_count,
memory_usage — and exposes live state at GET /agents/status.

Docker access goes through the two scoped socket proxies (sacred rule:
main proxy = read-only, healer proxy = write):
  - reads  → docker-socket-proxy        (container list / inspect / stats)
  - writes → docker-socket-proxy-healer (container restart only)

Auto-restart policy (crash = container transitions running → exited with a
non-zero exit code, or → dead):
  - every crash is recorded in a rolling CRASH_WINDOW_SECONDS (default 600s)
    window in Redis
  - while crashes-in-window < CRASH_THRESHOLD (default 3) the registry
    restarts the agent immediately (per-agent RESTART_COOLDOWN_SECONDS)
  - at the 3rd crash in 10 minutes it issues ONE more restart, then opens a
    circuit breaker for CIRCUIT_BREAK_SECONDS so a hard crash-loop can't
    hammer the daemon, and fires a Discord alert if DISCORD_WEBHOOK_URL is set
  - POST /agents/{name}/reset closes the breaker manually
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [agent-registry] %(message)s")
logger = logging.getLogger("agent-registry")

# ── Configuration ────────────────────────────────────────────────────────────

DOCKER_READ_HOST = os.getenv("DOCKER_READ_HOST", "http://docker-socket-proxy:2375").rstrip("/")
DOCKER_WRITE_HOST = os.getenv("DOCKER_WRITE_HOST", "http://docker-socket-proxy-healer:2375").rstrip("/")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
CRASH_WINDOW_SECONDS = int(os.getenv("CRASH_WINDOW_SECONDS", "600"))
CRASH_THRESHOLD = int(os.getenv("CRASH_THRESHOLD", "3"))
RESTART_COOLDOWN_SECONDS = int(os.getenv("RESTART_COOLDOWN_SECONDS", "60"))
CIRCUIT_BREAK_SECONDS = int(os.getenv("CIRCUIT_BREAK_SECONDS", "600"))
AUTO_RESTART_ENABLED = os.getenv("AUTO_RESTART_ENABLED", "true").lower() in ("1", "true", "yes")
STATS_CONCURRENCY = int(os.getenv("STATS_CONCURRENCY", "6"))

DOCKER_TIMEOUT = httpx.Timeout(15.0, connect=5.0)

# ── The swarm roster ─────────────────────────────────────────────────────────
# container name → (role, compose file / profile that owns it, expected?)
# expected=False means "fine if not deployed" (profile-gated or on-demand);
# those report status "not_deployed" instead of "missing".

ROSTER: dict[str, dict[str, Any]] = {
    # Always-on core agents (docker-compose.agents.yml, no profile)
    "healer-agent":            {"role": "Self-healing MAPE-K engine — watches + heals the fleet", "source": "agents.yml", "expected": True},
    "hypercode-dashboard":     {"role": "Web dashboard UI", "source": "agents.yml", "expected": True},
    "hypercode-mcp-server":    {"role": "MCP server exposing HyperCode tools", "source": "agents.yml", "expected": True},
    "github-sync":             {"role": "Brain vault → GitHub sync bridge", "source": "agents.yml", "expected": True},
    # Profile: agents
    "crew-orchestrator":       {"role": "Multi-agent crew orchestration (/execute, port 8081)", "source": "agents.yml [agents]", "expected": True},
    "coder-agent":             {"role": "Code-writing agent", "source": "agents.yml [agents]", "expected": True},
    "mcp-gateway":             {"role": "Docker MCP gateway", "source": "agents.yml [agents]", "expected": True},
    "mcp-rest-adapter":        {"role": "REST adapter in front of MCP gateway", "source": "agents.yml [agents]", "expected": True},
    "broski-pets-bridge":      {"role": "BROskiPets dNFT bridge (port 8098)", "source": "agents.yml [agents]", "expected": True},
    "nemoclaw-agent":          {"role": "Code-health sidecar — heartbeat/memory/voice/focus (port 8099)", "source": "agents.yml [agents]", "expected": True},
    "goal-keeper":             {"role": "Goal tracking + accountability agent", "source": "agents.yml [agents]", "expected": True},
    "project-strategist":      {"role": "Plans + delegates tasks to specialists (on-demand)", "source": "agents.yml [agents]", "expected": False, "auto_restart": False},
    "frontend-specialist":     {"role": "React/Tailwind/Vite specialist (port 8012)", "source": "agents.yml [agents]", "expected": True},
    "backend-specialist":      {"role": "Python/FastAPI specialist (port 8003)", "source": "agents.yml [agents]", "expected": True},
    "database-architect":      {"role": "Postgres/schema specialist (port 8004)", "source": "agents.yml [agents]", "expected": True},
    "qa-engineer":             {"role": "Testing + QA specialist (port 8005)", "source": "agents.yml [agents]", "expected": True},
    "devops-engineer":         {"role": "CI/CD + infra specialist (port 8006)", "source": "agents.yml [agents]", "expected": True},
    # Discord
    "broski-bot":              {"role": "ONE TRUE BOT — Discord economy/focus/missions", "source": "core.yml [discord]", "expected": True},
    # Brain stack (docker-compose.brain.yml)
    "hyper-brain":             {"role": "Hyper Brain monolith (port 8100)", "source": "brain.yml", "expected": True},
    "agent-hyper-brain-core":  {"role": "Brain core agent (port 3301)", "source": "brain.yml [brain-agents]", "expected": True},
    "agent-mcp-bridge":        {"role": "Brain MCP bridge + graph routes (port 3302)", "source": "brain.yml [brain-agents]", "expected": True},
    "agent-focus-tracker":     {"role": "Focus session tracker (port 3303)", "source": "brain.yml [brain-agents]", "expected": True},
    "agent-morning-briefing":  {"role": "Morning briefing generator (port 3304)", "source": "brain.yml [brain-briefing]", "expected": True},
    "obsidian-watcher":        {"role": "Crew results → Obsidian vault auto-push sidecar", "source": "obsidian-sync.yml [agents]", "expected": True},
    # Hyperhealth
    "hyperhealth-api":         {"role": "Health metrics API (port 8095)", "source": "agents.yml [health]", "expected": True},
    "hyperhealth-worker":      {"role": "Health metrics background worker", "source": "agents.yml [health]", "expected": True},
    # Hyper profile (agents.yml [hyper])
    "hyper-architect":         {"role": "Architecture planner agent", "source": "agents.yml [hyper]", "expected": False},
    "hyper-observer":          {"role": "Observability watcher agent", "source": "agents.yml [hyper]", "expected": False},
    "hyper-worker":            {"role": "General task execution agent", "source": "agents.yml [hyper]", "expected": False},
    "agent-x":                 {"role": "Experimental agent X", "source": "agents.yml [hyper]", "expected": False},
    # Full-roster extras (docker-compose.agents-full.yml only)
    "security-engineer":       {"role": "Security review specialist (port 8007)", "source": "agents-full.yml", "expected": False},
    "system-architect":        {"role": "System design specialist (port 8008)", "source": "agents-full.yml", "expected": False},
    "tips-tricks-writer":      {"role": "ND-friendly docs writer (port 8009)", "source": "agents-full.yml", "expected": False},
    "throttle-agent":          {"role": "Resource throttling governor", "source": "agents-full.yml", "expected": False},
    "super-hyper-broski-agent": {"role": "Vibe/energy action agent (port 8015)", "source": "agents-full.yml", "expected": False},
    "test-agent":              {"role": "Smoke-test agent (on-demand)", "source": "agents-full.yml", "expected": False, "auto_restart": False},
    "session-snapshot":        {"role": "Idle-triggered SESSION.md writer", "source": "agents-full.yml", "expected": False},
    "hyper-split-agent":       {"role": "ADHD task decomposer (Ollama-backed)", "source": "agents-full.yml", "expected": False},
    "coderabbit-webhook":      {"role": "CodeRabbit PR review webhook receiver", "source": "agents-full.yml", "expected": False},
    # New services from this audit
    "agent-factory":           {"role": "Spawns/wakes profile-gated agents via REST", "source": "registry.yml [agents]", "expected": False},
    "hyper-auto-assistant":    {"role": "Keyword intent router → broski actions (port 8016)", "source": "registry.yml [hyper]", "expected": False},
    "evolve-relay":            {"role": "Evolution relay service", "source": "compose (misc)", "expected": False},
}

_EXIT_CODE_RE = re.compile(r"Exited \((\d+)\)")

# ── Models ───────────────────────────────────────────────────────────────────


class AgentStatus(BaseModel):
    name: str
    role: str
    source: str
    status: str                      # healthy | running | unhealthy | starting | crashed | stopped | restarting | not_deployed | missing
    last_ping: Optional[str] = None  # ISO8601 — last time seen running (or explicit heartbeat)
    error_count: int = 0
    memory_usage_mb: Optional[float] = None
    restart_count: int = 0           # docker-reported RestartCount
    crashes_in_window: int = 0
    crash_loop: bool = False         # circuit breaker open
    auto_restarts_issued: int = 0


class PingRequest(BaseModel):
    name: str


class FleetSummary(BaseModel):
    total: int
    healthy: int
    running: int
    down: int
    not_deployed: int
    crash_looping: int
    auto_restart_enabled: bool
    generated_at: str


class StatusResponse(BaseModel):
    summary: FleetSummary
    agents: list[AgentStatus]


# ── State ────────────────────────────────────────────────────────────────────

redis: Optional[aioredis.Redis] = None
_prev_running: dict[str, bool] = {}
_last_restart_at: dict[str, float] = {}
_poll_task: Optional[asyncio.Task] = None
_stats_sem = asyncio.Semaphore(STATS_CONCURRENCY)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rkey(name: str) -> str:
    return f"registry:agent:{name}"


def _ckey(name: str) -> str:
    return f"registry:crashes:{name}"


# ── Docker helpers (via socket proxies) ──────────────────────────────────────


async def _docker_list_all() -> list[dict]:
    async with httpx.AsyncClient(timeout=DOCKER_TIMEOUT) as client:
        r = await client.get(f"{DOCKER_READ_HOST}/containers/json", params={"all": "true"})
        r.raise_for_status()
        return r.json()


async def _docker_inspect(name: str) -> Optional[dict]:
    async with httpx.AsyncClient(timeout=DOCKER_TIMEOUT) as client:
        r = await client.get(f"{DOCKER_READ_HOST}/containers/{name}/json")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()


async def _docker_memory_mb(name: str) -> Optional[float]:
    try:
        async with _stats_sem:
            async with httpx.AsyncClient(timeout=DOCKER_TIMEOUT) as client:
                r = await client.get(
                    f"{DOCKER_READ_HOST}/containers/{name}/stats",
                    params={"stream": "false", "one-shot": "true"},
                )
                if r.status_code != 200:
                    return None
                usage = r.json().get("memory_stats", {}).get("usage")
                return round(usage / (1024 * 1024), 1) if usage else None
    except httpx.HTTPError:
        return None


async def _docker_restart(name: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
            r = await client.post(f"{DOCKER_WRITE_HOST}/containers/{name}/restart", params={"t": 10})
            return r.status_code in (204, 304)
    except httpx.HTTPError as e:
        logger.error(f"Restart of {name} failed: {e}")
        return False


async def _discord_alert(message: str) -> None:
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(DISCORD_WEBHOOK_URL, json={"content": message})
    except httpx.HTTPError as e:
        logger.warning(f"Discord alert failed: {e}")


# ── Crash window bookkeeping (Redis-backed, survives registry restarts) ─────


async def _record_crash(name: str) -> int:
    """Record a crash timestamp; return crashes inside the rolling window."""
    assert redis is not None
    now = time.time()
    key = _ckey(name)
    pipe = redis.pipeline()
    pipe.zadd(key, {f"{now}": now})
    pipe.zremrangebyscore(key, 0, now - CRASH_WINDOW_SECONDS)
    pipe.zcard(key)
    pipe.expire(key, CRASH_WINDOW_SECONDS * 2)
    results = await pipe.execute()
    return int(results[2])


async def _crashes_in_window(name: str) -> int:
    assert redis is not None
    now = time.time()
    await redis.zremrangebyscore(_ckey(name), 0, now - CRASH_WINDOW_SECONDS)
    return int(await redis.zcard(_ckey(name)))


async def _circuit_open(name: str) -> bool:
    assert redis is not None
    return bool(await redis.exists(f"registry:circuit:{name}"))


async def _open_circuit(name: str) -> None:
    assert redis is not None
    await redis.set(f"registry:circuit:{name}", _now_iso(), ex=CIRCUIT_BREAK_SECONDS)


async def _close_circuit(name: str) -> None:
    assert redis is not None
    await redis.delete(f"registry:circuit:{name}")
    await redis.delete(_ckey(name))


# ── Core poll cycle ──────────────────────────────────────────────────────────


def _derive_status(state: str, status_text: str) -> str:
    if state == "running":
        if "(healthy)" in status_text:
            return "healthy"
        if "(unhealthy)" in status_text:
            return "unhealthy"
        if "(health: starting)" in status_text:
            return "starting"
        return "running"
    if state == "restarting":
        return "restarting"
    if state in ("exited", "dead"):
        m = _EXIT_CODE_RE.search(status_text)
        exit_code = int(m.group(1)) if m else -1
        return "stopped" if exit_code == 0 else "crashed"
    return state or "unknown"


async def _handle_crash(name: str) -> None:
    """Apply the auto-restart policy to a freshly-crashed agent."""
    assert redis is not None
    crashes = await _record_crash(name)
    await redis.hincrby(_rkey(name), "error_count", 1)
    logger.warning(f"Crash detected: {name} ({crashes} in last {CRASH_WINDOW_SECONDS}s)")

    if not AUTO_RESTART_ENABLED:
        return
    if await _circuit_open(name):
        logger.info(f"Circuit open for {name} — not restarting")
        return

    now = time.time()
    if now - _last_restart_at.get(name, 0) < RESTART_COOLDOWN_SECONDS:
        return

    if crashes >= CRASH_THRESHOLD:
        # Final attempt, then open the breaker and alert.
        ok = await _docker_restart(name)
        _last_restart_at[name] = now
        await _open_circuit(name)
        await redis.hincrby(_rkey(name), "auto_restarts_issued", 1)
        await _discord_alert(
            f"🚨 **agent-registry**: `{name}` crashed {crashes}x in "
            f"{CRASH_WINDOW_SECONDS // 60} min. Final restart "
            f"{'issued' if ok else 'FAILED'} — circuit breaker open for "
            f"{CIRCUIT_BREAK_SECONDS // 60} min."
        )
        logger.error(f"{name} is crash-looping — breaker opened (restart {'ok' if ok else 'failed'})")
    else:
        ok = await _docker_restart(name)
        _last_restart_at[name] = now
        if ok:
            await redis.hincrby(_rkey(name), "auto_restarts_issued", 1)
            logger.info(f"Auto-restarted {name}")


async def _poll_once() -> None:
    assert redis is not None
    containers = await _docker_list_all()
    by_name: dict[str, dict] = {}
    for c in containers:
        for raw in c.get("Names", []):
            by_name[raw.lstrip("/")] = c

    for name, meta in ROSTER.items():
        key = _rkey(name)
        c = by_name.get(name)

        if c is None:
            status = "not_deployed" if not meta["expected"] else "missing"
            await redis.hset(key, mapping={"status": status})
            _prev_running.pop(name, None)
            continue

        state = c.get("State", "")
        status_text = c.get("Status", "")
        status = _derive_status(state, status_text)
        is_running = state == "running"

        fields: dict[str, str] = {"status": status}
        if is_running:
            fields["last_ping"] = _now_iso()
            mem = await _docker_memory_mb(name)
            if mem is not None:
                fields["memory_usage_mb"] = str(mem)
        await redis.hset(key, mapping=fields)

        # crash detection: was running last cycle, now exited non-zero / dead.
        # Agents flagged auto_restart=False (on-demand one-shots like
        # project-strategist) are observed but never revived.
        was_running = _prev_running.get(name)
        if meta.get("auto_restart", True):
            if was_running and not is_running and status == "crashed":
                await _handle_crash(name)
            elif not was_running and was_running is not None and status == "crashed":
                # still down and crashed — keep nudging it (cooldown-limited)
                if AUTO_RESTART_ENABLED and not await _circuit_open(name):
                    if time.time() - _last_restart_at.get(name, 0) >= RESTART_COOLDOWN_SECONDS:
                        await _handle_crash(name)

        _prev_running[name] = is_running


async def _poll_loop() -> None:
    while True:
        try:
            await _poll_once()
        except Exception as e:
            logger.error(f"Poll cycle failed: {e}")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


# ── FastAPI app ──────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis, _poll_task
    redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    await redis.ping()
    _poll_task = asyncio.create_task(_poll_loop())
    logger.info(
        f"Agent registry up — {len(ROSTER)} agents tracked, poll every "
        f"{POLL_INTERVAL_SECONDS}s, auto-restart={'ON' if AUTO_RESTART_ENABLED else 'OFF'}"
    )
    yield
    if _poll_task:
        _poll_task.cancel()
    if redis:
        await redis.aclose()


app = FastAPI(title="HyperCode Agent Registry", version="1.0.0", lifespan=lifespan)


async def _agent_status(name: str) -> AgentStatus:
    assert redis is not None
    meta = ROSTER[name]
    data = await redis.hgetall(_rkey(name))
    crashes = await _crashes_in_window(name)
    return AgentStatus(
        name=name,
        role=meta["role"],
        source=meta["source"],
        status=data.get("status", "unknown"),
        last_ping=data.get("last_ping"),
        error_count=int(data.get("error_count", 0)),
        memory_usage_mb=float(data["memory_usage_mb"]) if data.get("memory_usage_mb") else None,
        restart_count=int(data.get("restart_count", 0)),
        crashes_in_window=crashes,
        crash_loop=await _circuit_open(name),
        auto_restarts_issued=int(data.get("auto_restarts_issued", 0)),
    )


@app.get("/health")
async def health() -> dict[str, Any]:
    try:
        assert redis is not None
        await redis.ping()
    except Exception:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return {"status": "healthy", "agents_tracked": len(ROSTER)}


@app.get("/agents/status", response_model=StatusResponse)
async def agents_status() -> StatusResponse:
    """Live state of the whole swarm."""
    agents = [await _agent_status(name) for name in sorted(ROSTER)]
    healthy = sum(1 for a in agents if a.status == "healthy")
    running = sum(1 for a in agents if a.status in ("running", "starting"))
    down = sum(1 for a in agents if a.status in ("crashed", "missing", "unhealthy", "restarting"))
    not_deployed = sum(1 for a in agents if a.status in ("not_deployed", "stopped"))
    return StatusResponse(
        summary=FleetSummary(
            total=len(agents),
            healthy=healthy,
            running=running,
            down=down,
            not_deployed=not_deployed,
            crash_looping=sum(1 for a in agents if a.crash_loop),
            auto_restart_enabled=AUTO_RESTART_ENABLED,
            generated_at=_now_iso(),
        ),
        agents=agents,
    )


@app.get("/agents/status/{name}", response_model=AgentStatus)
async def agent_status(name: str) -> AgentStatus:
    if name not in ROSTER:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {name}")
    return await _agent_status(name)


@app.post("/agents/ping")
async def agent_ping(req: PingRequest) -> dict[str, str]:
    """Optional self-heartbeat — agents may POST here to prove liveness."""
    if req.name not in ROSTER:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {req.name}")
    assert redis is not None
    await redis.hset(_rkey(req.name), mapping={"last_ping": _now_iso()})
    return {"status": "ok", "agent": req.name}


@app.post("/agents/{name}/restart")
async def manual_restart(name: str) -> dict[str, Any]:
    """Manually restart an agent container (bypasses the circuit breaker)."""
    if name not in ROSTER:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {name}")
    info = await _docker_inspect(name)
    if info is None:
        raise HTTPException(status_code=409, detail=f"Container '{name}' does not exist")
    ok = await _docker_restart(name)
    if not ok:
        raise HTTPException(status_code=502, detail=f"Docker restart of '{name}' failed")
    return {"status": "restarted", "agent": name}


@app.post("/agents/{name}/reset")
async def reset_agent(name: str) -> dict[str, str]:
    """Clear error count, crash window, and circuit breaker for an agent."""
    if name not in ROSTER:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {name}")
    assert redis is not None
    await _close_circuit(name)
    await redis.hset(_rkey(name), mapping={"error_count": "0", "auto_restarts_issued": "0"})
    return {"status": "reset", "agent": name}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8077)))
