"""
HyperCode MCP Server
──────────────────────────────────────────────────────────────────────────────
Exposes HyperCode's core capabilities as MCP tools so any AI IDE
(Claude Code, Cursor, Windsurf, etc.) can interact with the stack natively.

Transport: SSE (HTTP) — runs on port 8823
Connect from Claude Code:  add to .mcp.json → "url": "http://localhost:8823/sse"

Tools exposed:
  hypercode_system_health   — overall stack health
  hypercode_list_agents     — all running agents + status
  hypercode_list_tasks      — task list (filterable)
  hypercode_create_task     — create a new task
  hypercode_generate_plan   — run the planning pipeline on a document
  hypercode_get_logs        — recent system log entries
  hypercode_broski_wallet   — BROski$ token balance + level
  hypercode_execute_agent   — send a command to the crew orchestrator
  hypercode_inspect         — start a read-only stack inspection (background task)
  hypercode_recover         — start a recovery diagnosis (background task, proposes only)
  hypercode_crew_start      — start a HyperCrew run from a goal (plan gate, then propose-only build/verify/guard)
  hypercode_crew_status     — AG-UI-shaped events + Calm Card for a crew run (replay with `after`)
  hypercode_task_get        — poll a background task
  hypercode_task_cancel     — cancel a background task
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

# ── Config ────────────────────────────────────────────────────────────────────
CORE_URL    = os.getenv("HYPERCODE_CORE_URL", "http://hypercode-core:8000")
ORCH_URL    = os.getenv("HYPERCODE_ORCH_URL", "http://crew-orchestrator:8080")
API_PREFIX  = "/api/v1"
TIMEOUT     = 10.0

# Agent key presented to hypercode-core's operator API (X-Agent-Key). Optional: without it
# operator calls return 401. Never logged; only ever sent to CORE_URL.
AGENT_KEY   = os.getenv("HYPERCODE_AGENT_KEY", "")


def _valid_task_id(task_id: Any) -> Optional[str]:
    """Canonical lowercase UUID string, or None. Rejects anything but a real UUID."""
    try:
        u = uuid.UUID(task_id)
    except (ValueError, AttributeError, TypeError):
        return None
    canonical = str(u)
    return canonical if canonical == task_id.lower() else None


# The mcp SDK (>=1.9) turns DNS-rebinding protection ON by default and only
# accepts Host headers matching 127.0.0.1:* / localhost:* / [::1]:* — so every
# request that arrives by Docker service name (the dashboard's MCP proxy hits
# http://hypercode-mcp-server:8823/sse) is rejected with 421 Misdirected
# Request. Re-allow the in-cluster name explicitly; the SDK defaults are kept so
# `http://localhost:8823/sse` from an IDE (Claude Code / Cursor) still works.
_ALLOWED_HOSTS = [
    "127.0.0.1:*", "localhost:*", "[::1]:*",   # SDK defaults
    "hypercode-mcp-server:*",                   # Docker service name (dashboard proxy, in-cluster clients)
    "0.0.0.0:*",
]

mcp = FastMCP(
    "HyperCode",
    instructions=(
        "HyperCode is an AI agent stack with self-healing, planning, and BROski$ economy. "
        "Use these tools to inspect running agents, manage tasks, generate implementation "
        "plans, and query the system health. Always check system_health first if unsure."
    ),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_ALLOWED_HOSTS,
        allowed_origins=(
            [f"http://{h}" for h in _ALLOWED_HOSTS]
            + [f"https://{h}" for h in _ALLOWED_HOSTS]
        ),
    ),
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> JSONResponse:
    """Cheap, non-streaming liveness probe for the Docker healthcheck and the
    dashboard's MCP Gateway panel. The real MCP endpoint (/sse) is a long-lived
    stream — probing *it* hangs the check until it times out (the old bug that
    left this container `unhealthy`)."""
    return JSONResponse({"status": "ok", "service": "hypercode-mcp-server", "transport": "sse"})

def _core_headers(base: str) -> dict:
    """X-Agent-Key for calls to hypercode-core only — never sent to any other host."""
    return {"X-Agent-Key": AGENT_KEY} if AGENT_KEY and base == CORE_URL else {}


async def _get(path: str, base: str = CORE_URL, **params: Any) -> Any:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{base}{path}", params=params or None, headers=_core_headers(base))
        r.raise_for_status()
        return r.json()


async def _post(path: str, body: dict, base: str = CORE_URL) -> Any:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{base}{path}", json=body, headers=_core_headers(base))
        r.raise_for_status()
        return r.json()


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def hypercode_system_health() -> dict:
    """
    Get the overall health of the HyperCode stack.
    Returns status, service name, version, and environment.
    Use this first to confirm the stack is reachable.
    """
    return await _get("/health")


@mcp.tool()
async def hypercode_list_agents() -> dict:
    """
    List all running agents and their current status.
    Returns agent IDs, names, online/health status, and last-seen time.
    Use this to see what agents are active and whether any need attention.
    """
    # Public agent roster. /orchestrator/agents is auth-gated (401 without a
    # user token); /agents/status is the unauthenticated feed the dashboard's
    # Agent Monitor uses too.
    return await _get(f"{API_PREFIX}/agents/status")


@mcp.tool()
async def hypercode_agent_system_health() -> dict:
    """
    Get deep system health from the orchestrator — CPU, memory, Redis, and
    per-agent metrics. More detailed than hypercode_system_health.
    """
    return await _get(f"{API_PREFIX}/orchestrator/system/health")


@mcp.tool()
async def hypercode_list_tasks(
    status: Optional[str] = None,
    limit: int = 20,
) -> list:
    """
    List tasks in the HyperCode task system.

    Args:
        status: Filter by status — 'pending', 'in_progress', 'done', 'failed'.
                Leave empty to return all.
        limit:  Max number of tasks to return (default 20, max 100).
    """
    params: dict = {"limit": min(limit, 100)}
    if status:
        params["status"] = status
    return await _get(f"{API_PREFIX}/tasks/", **params)


@mcp.tool()
async def hypercode_create_task(
    title: str,
    description: str,
    priority: str = "medium",
    assigned_agent: Optional[str] = None,
) -> dict:
    """
    Create a new task in HyperCode.

    Args:
        title:          Short task title.
        description:    Full task description.
        priority:       'low', 'medium', 'high', or 'critical'. Default: 'medium'.
        assigned_agent: Optional agent ID to assign the task to.
    """
    body: dict = {
        "title": title,
        "description": description,
        "priority": priority,
    }
    if assigned_agent:
        body["assigned_agent"] = assigned_agent
    return await _post(f"{API_PREFIX}/tasks/", body)


@mcp.tool()
async def hypercode_generate_plan(
    document: str,
    document_type: str = "generic",
) -> dict:
    """
    Run the HyperCode planning pipeline on a document.
    Returns a structured implementation plan with phases, file changes,
    and follow-up instructions.

    Args:
        document:      The PRD, issue description, design doc, or free text to plan from.
        document_type: 'prd', 'issue', 'design', or 'generic'. Default: 'generic'.

    The response includes:
      - summary: one-paragraph overview
      - phases: numbered implementation phases with workflow steps
      - file_changes_summary: files to create/modify/delete
      - follow_up_instructions: post-implementation notes
    """
    return await _post(
        f"{API_PREFIX}/planning/generate",
        {"document": {"content": document, "document_type": document_type}},
    )


@mcp.tool()
async def hypercode_get_logs(limit: int = 50) -> list:
    """
    Get recent system log entries from all agents.
    Each entry has: time, level (DEBUG/INFO/WARNING/ERROR), agent name, message.

    Args:
        limit: Number of log lines to return (default 50, max 200).
    """
    return await _get(f"{API_PREFIX}/logs", limit=min(limit, 200))


@mcp.tool()
async def hypercode_broski_wallet(user_id: str = "system") -> dict:
    """
    Get a BROski$ wallet — token balance, level, XP progress, and recent transactions.

    Args:
        user_id: The user/agent ID to look up. Use 'system' for the stack-wide wallet.
    """
    return await _get(f"{API_PREFIX}/broski/wallet")


@mcp.tool()
async def hypercode_broski_leaderboard() -> list:
    """
    Get the BROski$ leaderboard — top agents/users by coin balance and level.
    Great for gamified motivation and tracking agent performance.
    """
    return await _get(f"{API_PREFIX}/broski/leaderboard")


@mcp.tool()
async def hypercode_execute_agent(
    command: str,
    agent_id: Optional[str] = None,
    context: Optional[dict] = None,
) -> dict:
    """
    Send an execution command to the crew orchestrator.
    The orchestrator will route it to the appropriate agent.

    Args:
        command:  The instruction to execute (e.g. 'heal unhealthy agents',
                  'run security scan', 'generate daily report').
        agent_id: Optional — target a specific agent by ID.
        context:  Optional dict of additional context for the agent.
    """
    body: dict = {"command": command}
    if agent_id:
        body["agent_id"] = agent_id
    if context:
        body["context"] = context
    return await _post(f"{API_PREFIX}/orchestrator/execute", body)


# ── BROski operator tasks (async, durable) ────────────────────────────────────

@mcp.tool()
async def hypercode_inspect() -> dict:
    """
    Start a read-only stack health inspection as a background task.
    Returns a task handle immediately ({taskId, status:"working", pollInterval});
    poll it with hypercode_task_get. Never changes anything.
    """
    return await _post(
        f"{API_PREFIX}/operator/tasks", {"tool": "hypercode.inspect", "arguments": {}}
    )


@mcp.tool()
async def hypercode_recover() -> dict:
    """
    Start a read-only recovery diagnosis as a background task. It looks for broken containers,
    proposes at most ONE allow-listed restart, and waits for a human (superuser) to approve the
    exact plan in the dashboard/API. Phase 2a NEVER restarts anything — approval only seals the
    plan for the future governed executor. Returns a task handle; poll with hypercode_task_get.
    """
    return await _post(
        f"{API_PREFIX}/operator/tasks", {"tool": "hypercode.recover", "arguments": {}}
    )


@mcp.tool()
async def hypercode_crew_start(goal: str, idempotency_key: str = "") -> dict:
    """
    Start a HyperCrew run for a build goal, as a background task. The crew writes a PLAN and stops
    at a human gate: a person must approve the exact plan (by its hash) in the dashboard/API —
    approvals are not possible through this server by design. After approval the builder and
    verifier only PROPOSE text; nothing is written, run, built or deployed, and a guard decides
    ALLOW/BLOCK. Returns a task handle immediately; follow progress with hypercode_crew_status.

    idempotency_key (8-128 chars: letters, digits, . _ : -) makes a retry safe: the same key and
    goal returns the SAME task instead of starting a second one. Pass one when you might retry.
    """
    body: dict = {"tool": "hypercode.crew", "arguments": {"goal": goal}}
    if idempotency_key:
        body["idempotency_key"] = idempotency_key
    return await _post(f"{API_PREFIX}/operator/tasks", body)


@mcp.tool()
async def hypercode_crew_status(task_id: str, after: int = -1) -> dict:
    """
    Progress of a crew run: AG-UI-shaped events (RUN_STARTED, STEP_*, TOOL_CALL_*, CUSTOM
    hypercode.* such as approval.required / guard.verdict, RUN_FINISHED / RUN_ERROR), the current
    Calm Card (at most five lines and ONE next action) and a poll hint. Replay-safe: pass the
    `nextAfter` from the previous reply as `after` to receive only what you have not seen.
    """
    tid = _valid_task_id(task_id)
    if tid is None:
        return {"error": "invalid task_id"}
    try:
        cursor = int(after)
    except (TypeError, ValueError):
        return {"error": "invalid after"}
    if cursor < -1 or cursor > 10**9:
        return {"error": "invalid after"}
    return await _get(f"{API_PREFIX}/operator/tasks/{tid}/events", after=cursor)


@mcp.tool()
async def hypercode_task_get(task_id: str) -> dict:
    """
    Get a background task's status. status is one of working, input_required,
    completed, failed, cancelled. The result appears only when completed.
    input_required means a human must approve — approvals are not possible via this
    server by design.
    """
    tid = _valid_task_id(task_id)
    if tid is None:
        return {"error": "invalid task_id"}
    return await _get(f"{API_PREFIX}/operator/tasks/{tid}")


@mcp.tool()
async def hypercode_task_cancel(task_id: str, reason: str = "") -> dict:
    """Cancel a background task. Safe to call; already-finished tasks return a 409 error."""
    tid = _valid_task_id(task_id)
    if tid is None:
        return {"error": "invalid task_id"}
    return await _post(
        f"{API_PREFIX}/operator/tasks/{tid}/cancel", {"reason": (reason or "")[:200]}
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    sse_app = mcp.sse_app()
    uvicorn.run(sse_app, host="0.0.0.0", port=8823, log_level="info")
