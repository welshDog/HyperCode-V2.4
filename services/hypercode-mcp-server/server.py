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
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP

# ── Config ────────────────────────────────────────────────────────────────────
CORE_URL    = os.getenv("HYPERCODE_CORE_URL", "http://hypercode-core:8000")
ORCH_URL    = os.getenv("HYPERCODE_ORCH_URL", "http://crew-orchestrator:8080")
API_PREFIX  = "/api/v1"
TIMEOUT     = 10.0

mcp = FastMCP(
    "HyperCode",
    instructions=(
        "HyperCode is an AI agent stack with self-healing, planning, and BROski$ economy. "
        "Use these tools to inspect running agents, manage tasks, generate implementation "
        "plans, and query the system health. Always check system_health first if unsure."
    ),
)

# ── HTTP helper ───────────────────────────────────────────────────────────────

async def _get(path: str, base: str = CORE_URL, **params: Any) -> Any:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{base}{path}", params=params or None)
        r.raise_for_status()
        return r.json()


async def _post(path: str, body: dict, base: str = CORE_URL) -> Any:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{base}{path}", json=body)
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
    Returns agent IDs, names, health state, XP, level, and coin balance.
    Use this to see what agents are active and whether any need attention.
    """
    return await _get(f"{API_PREFIX}/orchestrator/agents")


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


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    sse_app = mcp.sse_app()
    uvicorn.run(sse_app, host="0.0.0.0", port=8823, log_level="info")
