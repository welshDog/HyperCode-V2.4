"""
BROski Economy MCP Server

Exposes BROski$ token economy as MCP tools and resources.

Tools:
  - award_tokens(discord_id, amount, reason)
  - spend_tokens(discord_id, amount, item_slug)
  - get_balance(discord_id)

Resources:
  - broski://balance/{discord_id}
  - broski://transactions/{discord_id}?limit=N
"""

import os
import json
from typing import Optional
from contextlib import asynccontextmanager

import asyncio
from asyncpg import create_pool, Pool

# MCP-style primitives (simplified; can be replaced with official MCP SDK later)
# Tools: callables with JSON Schema descriptions
# Resources: URI templates + handlers

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env var must be set")


@asynccontextmanager
async def get_db_pool():
    pool: Pool = await create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=10,
    )
    try:
        yield pool
    finally:
        await pool.close()


# ---------- Tool Implementations ----------


async def award_tokens(discord_id: str, amount: int, reason: str) -> dict:
    """
    Award BROski$ tokens to a user.
    Wraps the existing award_tokens() SQL function (SECURITY DEFINER).
    """
    async with get_db_pool() as pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT award_tokens($1, $2, $3) AS success;
                """,
                discord_id,
                amount,
                reason,
            )
            success = bool(row["success"])
            return {"success": success, "action": "award_tokens", "discord_id": discord_id, "amount": amount, "reason": reason}


async def spend_tokens(discord_id: str, amount: int, item_slug: str) -> dict:
    """
    Spend BROski$ tokens on a shop item or action.
    Wraps the existing spend_tokens() SQL function (SECURITY DEFINER).
    """
    async with get_db_pool() as pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT spend_tokens($1, $2, $3) AS success;
                """,
                discord_id,
                amount,
                item_slug,
            )
            success = bool(row["success"])
            return {"success": success, "action": "spend_tokens", "discord_id": discord_id, "amount": amount, "item_slug": item_slug}


async def get_balance(discord_id: str) -> dict:
    """
    Return the current broski_tokens balance for a user.
    """
    async with get_db_pool() as pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT broski_tokens AS balance
                FROM public.users
                WHERE discord_id = $1;
                """,
                discord_id,
            )
            balance = row["balance"] if row else 0
            return {"discord_id": discord_id, "balance": balance}


# ---------- Resource Implementations ----------


async def get_balance_resource(discord_id: str) -> dict:
    """
    Resource handler for broski://balance/{discord_id}
    """
    return await get_balance(discord_id)


async def get_transactions_resource(discord_id: str, limit: int = 10) -> list:
    """
    Resource handler for broski://transactions/{discord_id}?limit=N
    Returns recent token transactions for the user.
    """
    async with get_db_pool() as pool:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, discord_id, amount, balance_after, transaction_type,
                       item_slug, reason, created_at
                FROM public.token_transactions
                WHERE discord_id = $1
                ORDER BY created_at DESC
                LIMIT $2;
                """,
                discord_id,
                limit,
            )
            return [dict(r) for r in rows]


# ---------- MCP Server Skeleton ----------
# This is a simplified MCP-over-HTTP style server.
# In a later iteration, this can be replaced/wrapped by the official MCP SDK.

from fastapi import FastAPI, Request, Response
import uvicorn

app = FastAPI(title="BROski Economy MCP Server")

TOOLS = {
    "award_tokens": {
        "name": "award_tokens",
        "description": "Award BROski$ tokens to a user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "discord_id": {"type": "string"},
                "amount": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["discord_id", "amount", "reason"],
        },
    },
    "spend_tokens": {
        "name": "spend_tokens",
        "description": "Spend BROski$ tokens on a shop item or action.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "discord_id": {"type": "string"},
                "amount": {"type": "integer"},
                "item_slug": {"type": "string"},
            },
            "required": ["discord_id", "amount", "item_slug"],
        },
    },
    "get_balance": {
        "name": "get_balance",
        "description": "Return the current broski_tokens balance for a user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "discord_id": {"type": "string"},
            },
            "required": ["discord_id"],
        },
    },
}

RESOURCES = {
    "broski_balance": {
        "uriTemplate": "broski://balance/{discord_id}",
        "name": "broski_balance",
        "description": "Read-only resource exposing a user's BROski$ balance.",
    },
    "broski_transactions": {
        "uriTemplate": "broski://transactions/{discord_id}?limit=N",
        "name": "broski_transactions",
        "description": "Read-only resource exposing recent token transactions for a user.",
    },
}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/.well-known/mcp")
async def mcp_discovery():
    """
    MCP discovery endpoint (simplified).
    Returns tools and resources available on this server.
    """
    return {
        "tools": TOOLS,
        "resources": RESOURCES,
    }


@app.post("/mcp/tools/{tool_name}")
async def call_tool(tool_name: str, request: Request):
    """
    MCP tool invocation endpoint.
    Expects JSON body matching the tool's inputSchema.
    """
    body = await request.json()

    if tool_name == "award_tokens":
        result = await award_tokens(
            discord_id=body["discord_id"],
            amount=body["amount"],
            reason=body.get("reason", ""),
        )
    elif tool_name == "spend_tokens":
        result = await spend_tokens(
            discord_id=body["discord_id"],
            amount=body["amount"],
            item_slug=body["item_slug"],
        )
    elif tool_name == "get_balance":
        result = await get_balance(discord_id=body["discord_id"])
    else:
        return {"error": f"Unknown tool: {tool_name}"}, 404

    return {"result": result}


@app.get("/mcp/resources/broski://balance/{discord_id}")
async def resource_balance(discord_id: str):
    """
    MCP resource: broski://balance/{discord_id}
    """
    result = await get_balance_resource(discord_id)
    return result


@app.get("/mcp/resources/broski://transactions/{discord_id}")
async def resource_transactions(discord_id: str, limit: int = 10):
    """
    MCP resource: broski://transactions/{discord_id}?limit=N
    """
    result = await get_transactions_resource(discord_id, limit=limit)
    return result


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8099)
