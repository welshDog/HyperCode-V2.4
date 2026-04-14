"""
Phase 10D — Agent API Key management endpoints (superuser only).

POST   /api/v1/agent-keys             — generate/rotate a key for an agent
GET    /api/v1/agent-keys             — list all registered agent keys
DELETE /api/v1/agent-keys/{agent_name} — revoke a key
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.api.deps import get_current_active_superuser
from app.db.session import AsyncSessionLocal
from app.middleware.agent_auth import generate_agent_key, hash_agent_key

logger = logging.getLogger(__name__)
router = APIRouter()


class AgentKeyCreate(BaseModel):
    agent_name: str = Field(..., min_length=1, max_length=64)
    rate_limit_rpm: int = Field(default=200, ge=1, le=10_000)


class AgentKeyRow(BaseModel):
    agent_name: str
    key_prefix: str
    rate_limit_rpm: int
    is_active: bool


# ── POST /api/v1/agent-keys ───────────────────────────────────────────────────

@router.post("/agent-keys", tags=["agent-keys"])
async def create_agent_key(
    body: AgentKeyCreate,
    _=Depends(get_current_active_superuser),
):
    """
    Generate (or rotate) an API key for a named internal agent.

    The raw key is returned **once** — store it securely (e.g. Docker secret).
    Calling this endpoint for an existing agent_name replaces the previous key.
    """
    raw = generate_agent_key()
    key_hash = hash_agent_key(raw)
    key_prefix = raw[:10]

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    INSERT INTO agent_api_keys
                        (agent_name, key_prefix, key_hash, rate_limit_rpm, is_active)
                    VALUES
                        (:name, :prefix, :hash, :rpm, true)
                    ON CONFLICT (agent_name) DO UPDATE
                        SET key_prefix     = EXCLUDED.key_prefix,
                            key_hash       = EXCLUDED.key_hash,
                            rate_limit_rpm = EXCLUDED.rate_limit_rpm,
                            is_active      = true
                """),
                {
                    "name":   body.agent_name,
                    "prefix": key_prefix,
                    "hash":   key_hash,
                    "rpm":    body.rate_limit_rpm,
                },
            )
            await db.commit()
    except Exception as exc:
        logger.error("Failed to store agent key: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to store agent key")

    logger.info("Agent key issued/rotated for %s", body.agent_name)
    return {
        "agent_name":    body.agent_name,
        "api_key":       raw,
        "key_prefix":    key_prefix,
        "rate_limit_rpm": body.rate_limit_rpm,
        "note": "Store this key securely — it will not be shown again.",
    }


# ── GET /api/v1/agent-keys ────────────────────────────────────────────────────

@router.get("/agent-keys", response_model=list[AgentKeyRow], tags=["agent-keys"])
async def list_agent_keys(_=Depends(get_current_active_superuser)):
    """List all registered agent keys (hashed — raw keys are never stored)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("""
                SELECT agent_name, key_prefix, rate_limit_rpm, is_active
                FROM   agent_api_keys
                ORDER  BY agent_name
            """)
        )
        return [dict(r) for r in result.mappings().all()]


# ── DELETE /api/v1/agent-keys/{agent_name} ────────────────────────────────────

@router.delete("/agent-keys/{agent_name}", tags=["agent-keys"])
async def revoke_agent_key(
    agent_name: str,
    _=Depends(get_current_active_superuser),
):
    """Revoke (soft-delete) an agent API key by agent name."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("""
                UPDATE agent_api_keys
                SET    is_active = false
                WHERE  agent_name = :name
            """),
            {"name": agent_name},
        )
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"No key found for agent '{agent_name}'")

    logger.info("Agent key revoked for %s", agent_name)
    return {"revoked": agent_name}
