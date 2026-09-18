"""
SkillWeaver FastAPI Server
==========================

HTTP API for SkillWeaver, enabling agents to:
- Register skills
- Discover skills
- Compose skills
- Monitor system health
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from .skillweaver import (
    SkillWeaver,
    SkillRegistry,
    SkillMetadata,
    SkillSignature,
    SkillCategory,
    SkillMatch,
)

# Logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="SkillWeaver",
    description="Autonomous skill synthesis engine for agent evolution",
    version="1.1.0"
)

# Redis client (singleton)
_redis_client = None


async def get_redis() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        _redis_client = await redis.from_url(redis_url)
        logger.info(f"Connected to Redis: {redis_url}")
    return _redis_client


# ============================================================================
# Request/Response Models
# ============================================================================

_VALID_STRATEGIES = {"linear", "parallel", "conditional"}


class SkillMetadataRequest(BaseModel):
    """Register a new skill."""
    skill_id: str = Field(..., min_length=1)
    agent_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    category: str
    inputs: Dict[str, str]
    outputs: Dict[str, str]
    timeout_seconds: float = 30.0
    examples: List[str] = Field(default_factory=list)
    version: str = "1.0.0"

    @field_validator("category")
    @classmethod
    def _valid_category(cls, v: str) -> str:
        try:
            SkillCategory(v)
        except ValueError as exc:
            raise ValueError(f"invalid category: {v!r}") from exc
        return v


class BatchRegisterRequest(BaseModel):
    """Register multiple skills in one round-trip."""
    skills: List[SkillMetadataRequest] = Field(..., min_length=1, max_length=100)


class SkillDiscoveryRequest(BaseModel):
    """Discover relevant skills."""
    query: str
    category: Optional[str] = None
    top_k: int = 5

    @field_validator("category")
    @classmethod
    def _valid_category_opt(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            SkillCategory(v)
        except ValueError as exc:
            raise ValueError(f"invalid category: {v!r}") from exc
        return v


class SkillCompositionRequest(BaseModel):
    """Compose multiple skills into one."""
    skill_ids: List[str] = Field(..., min_length=1)
    strategy: str = "linear"

    @field_validator("strategy")
    @classmethod
    def _valid_strategy(cls, v: str) -> str:
        if v not in _VALID_STRATEGIES:
            raise ValueError(f"invalid strategy: {v!r} (expected one of {sorted(_VALID_STRATEGIES)})")
        return v


class SkillMatchResponse(BaseModel):
    """A discovered skill."""
    skill_id: str
    agent_id: str
    name: str
    description: str
    version: str
    category: str
    relevance_score: float
    reason: str


class CompositionResponse(BaseModel):
    """Result of skill composition."""
    composite_id: str
    component_skills: List[str]
    strategy: str
    status: str


class HealthResponse(BaseModel):
    """System health."""
    status: str
    timestamp: str
    redis_connected: bool
    skills_registered: int
    compositions_created: int


# ============================================================================
# Internal helpers
# ============================================================================


def _metadata_from_request(req: SkillMetadataRequest) -> SkillMetadata:
    """Convert a request into the canonical SkillMetadata domain object."""
    return SkillMetadata(
        skill_id=req.skill_id,
        agent_id=req.agent_id,
        name=req.name,
        description=req.description,
        category=SkillCategory(req.category),
        signature=SkillSignature(
            inputs=req.inputs,
            outputs=req.outputs,
        ),
        timeout_seconds=req.timeout_seconds,
        examples=req.examples,
        version=req.version,
    )


async def _register_one(
    registry: SkillRegistry,
    req: SkillMetadataRequest,
) -> Tuple[bool, Optional[str]]:
    """Register a single skill. Returns (was_replaced?, error_message|None)."""
    redis_client = registry.redis
    key = f"{registry.registry_key}:{req.skill_id}"
    existing = await redis_client.exists(key)
    try:
        await registry.register_skill(_metadata_from_request(req))
    except ValueError as exc:
        return False, str(exc)
    return (existing > 0), None


# ============================================================================
# Endpoints
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize on startup (explicit Redis ping so startup = fully online)."""
    redis_client = await get_redis()
    await redis_client.ping()
    logger.info("SkillWeaver server started — Redis ping OK")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("SkillWeaver server stopped")


@app.get("/health")
async def health() -> HealthResponse:
    """Health check endpoint."""
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        redis_ok = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_ok = False

    try:
        skills_count = len(await redis_client.smembers("skillweaver:registry:all_ids"))
        compositions_count = await redis_client.llen("skillweaver:compositions")
    except Exception:
        skills_count = 0
        compositions_count = 0

    return HealthResponse(
        status="healthy" if redis_ok else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        redis_connected=redis_ok,
        skills_registered=skills_count,
        compositions_created=compositions_count,
    )


@app.post("/api/v1/skills/register")
async def register_skill(req: SkillMetadataRequest) -> dict:
    """Register a new skill from an agent."""
    try:
        redis_client = await get_redis()
        registry = SkillRegistry(redis_client)
        was_replaced, err = await _register_one(registry, req)
        if err is not None:
            raise ValueError(err)
        logger.info(f"Skill registered: {req.skill_id} from {req.agent_id} (replaced={was_replaced})")
        return {
            "status": "registered",
            "skill_id": req.skill_id,
            "agent_id": req.agent_id,
            "version": req.version,
            "replaced_previous_version": was_replaced,
            "message": f"Skill '{req.name}' registered successfully",
        }
    except ValueError as e:
        logger.error(f"Invalid skill registration: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error registering skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/skills/register_batch")
async def register_skills_batch(req: BatchRegisterRequest) -> dict:
    """Register many skills for an agent in one RTT.

    Returns per-skill results so the caller can spot-check which ones
    replaced an older version and which ones errored. All valid skills in
    a single request succeed atomically with respect to the Redis keys
    (best-effort — there's no cross-key transaction here, but a partially
    written batch is still recoverable via the per-skill results array).
    """
    try:
        redis_client = await get_redis()
        registry = SkillRegistry(redis_client)
        results: List[Dict[str, Any]] = []
        for idx, skill_req in enumerate(req.skills):
            was_replaced, err = await _register_one(registry, skill_req)
            entry: Dict[str, Any] = {
                "index": idx,
                "skill_id": skill_req.skill_id,
                "agent_id": skill_req.agent_id,
                "version": skill_req.version,
                "registered": err is None,
            }
            if err is None:
                entry["replaced_previous_version"] = was_replaced
                entry["message"] = f"Skill '{skill_req.name}' registered"
            else:
                entry["error"] = err
            results.append(entry)
        registered_count = sum(1 for r in results if r["registered"])
        logger.info(f"Batch register complete: {registered_count}/{len(results)} registered")
        return {
            "status": "completed",
            "registered": registered_count,
            "total": len(results),
            "results": results,
        }
    except Exception as e:
        logger.error(f"Error in batch register: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/skills/{skill_id}")
async def get_single_skill(skill_id: str) -> dict:
    """Inspect one registered skill."""
    try:
        redis_client = await get_redis()
        registry = SkillRegistry(redis_client)
        meta = await registry.get_skill(skill_id)
        if meta is None:
            raise HTTPException(status_code=404, detail=f"Skill {skill_id!r} not found")
        return meta.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting skill {skill_id!r}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/skills/agent/{agent_id}")
async def deregister_all_for_agent(agent_id: str) -> dict:
    """Deregister every skill owned by `agent_id` (graceful decommission path).

    Idempotent: if the agent has no skills registered we still 200 with
    removed=0. This is the path called by `base_agent.shutdown()` via the
    `SkillWeaverClient.deregister_agent(agent_id)` SDK wrapper so long as
    `SKILLWEAVER_URL` is set in the agent's environment.
    """
    try:
        redis_client = await get_redis()
        registry = SkillRegistry(redis_client)
        by_agent_key = f"{registry.registry_key}:by_agent:{agent_id}"
        skill_ids_raw = await redis_client.smembers(by_agent_key)
        skill_ids: List[str] = [
            s.decode() if isinstance(s, bytes) else s
            for s in skill_ids_raw
        ]
        removed = 0
        for sid in skill_ids:
            meta = await registry.get_skill(sid)
            if meta is not None:
                await redis_client.delete(f"{registry.registry_key}:{sid}")
                await redis_client.srem(
                    f"{registry.registry_key}:by_category:{meta.category.value}", sid
                )
                await redis_client.srem("skillweaver:registry:all_ids", sid)
                removed += 1
        await redis_client.delete(by_agent_key)
        logger.info(f"Deregistered {removed} skills for agent={agent_id!r}")
        return {
            "status": "completed",
            "agent_id": agent_id,
            "removed": removed,
        }
    except Exception as e:
        logger.error(f"Error deregistering agent {agent_id!r}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/skills/discover")
async def discover_skills(req: SkillDiscoveryRequest) -> List[SkillMatchResponse]:
    """Discover relevant skills based on query."""
    try:
        redis_client = await get_redis()
        weaver = SkillWeaver(redis_client)

        # 10% boost performance guard: if global skill set is already huge
        # (>= 5000), short-circuit rather than scanning every one. The real
        # fix is RediSearch FT.CREATE + per-category bloom filters, but this
        # guard prevents us from silently falling over as the fleet grows.
        if req.category is None:
            total_size = await redis_client.scard("skillweaver:registry:all_ids")
            if total_size >= 5000:
                logger.warning(
                    "discover_skills: total_skills=%d >= 5000, early-return [] "
                    "to avoid N*per-skill scan. Install RediSearch for full-text "
                    "routing at this scale.",
                    total_size,
                )
                return []

        category = SkillCategory(req.category) if req.category else None
        if req.top_k <= 0:
            return []
        matches: List[SkillMatch] = await weaver.discover_skills(
            query=req.query,
            category=category,
            top_k=req.top_k,
        )
        logger.info(f"Skill discovery: query='{req.query}', found={len(matches)}")
        return [
            SkillMatchResponse(
                skill_id=m.metadata.skill_id,
                agent_id=m.metadata.agent_id,
                name=m.metadata.name,
                description=m.metadata.description,
                version=m.metadata.version,
                category=m.metadata.category.value,
                relevance_score=m.relevance_score,
                reason=m.reason,
            )
            for m in matches
        ]
    except ValueError as e:
        logger.error(f"Invalid discovery request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error discovering skills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/skills/compose")
async def compose_skills(req: SkillCompositionRequest) -> CompositionResponse:
    """Compose multiple skills into one."""
    try:
        redis_client = await get_redis()
        weaver = SkillWeaver(redis_client)

        valid, reason = await weaver.validate_composition(req.skill_ids)
        if not valid:
            logger.warning(f"Composition validation failed: {reason}")
            raise ValueError(f"Cannot compose: {reason}")

        composite = await weaver.compose_skills(
            skill_ids=req.skill_ids,
            strategy=req.strategy,
        )
        logger.info(f"Composite skill created: {composite.composite_id}")
        return CompositionResponse(
            composite_id=composite.composite_id,
            component_skills=req.skill_ids,
            strategy=req.strategy,
            status="ready",
        )
    except ValueError as e:
        logger.error(f"Composition error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error composing skills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/skills/list")
async def list_skills(
    agent_id: Optional[str] = Query(default=None, min_length=1),
    category: Optional[str] = Query(default=None, min_length=1),
) -> dict:
    """List registered skills.

    Optionally filter by `agent_id`, `category`, or both.
    """
    try:
        redis_client = await get_redis()
        registry = SkillRegistry(redis_client)

        if category is not None:
            try:
                cat = SkillCategory(category)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"invalid category: {category!r}") from exc
        else:
            cat = None

        if agent_id and cat:
            from_agent = {s.skill_id for s in await registry.list_skills_by_agent(agent_id)}
            skills = [s for s in await registry.list_skills_by_category(cat) if s.skill_id in from_agent]
        elif agent_id:
            skills = await registry.list_skills_by_agent(agent_id)
        elif cat:
            skills = await registry.list_skills_by_category(cat)
        else:
            all_skill_ids = await redis_client.smembers("skillweaver:registry:all_ids")
            skills: List[SkillMetadata] = []
            for skill_id in all_skill_ids:
                skill_id_str = skill_id.decode() if isinstance(skill_id, bytes) else skill_id
                skill = await registry.get_skill(skill_id_str)
                if skill:
                    skills.append(skill)
            logger.info(f"Listed {len(skills)} total skills")

        return {
            "count": len(skills),
            "skills": [s.to_dict() for s in skills],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing skills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/compositions/history")
async def composition_history(limit: int = 10) -> dict:
    """Get recent composition history."""
    try:
        redis_client = await get_redis()
        weaver = SkillWeaver(redis_client)
        if limit < 1:
            limit = 1
        compositions = await redis_client.lrange(weaver.composition_log_key, 0, limit - 1)
        parsed = [json.loads(comp) for comp in compositions]
        logger.info(f"Returned {len(parsed)} compositions from history")
        return {
            "count": len(parsed),
            "compositions": parsed,
        }
    except Exception as e:
        logger.error(f"Error getting composition history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stats")
async def stats() -> dict:
    """Get system statistics."""
    try:
        redis_client = await get_redis()
        registry = SkillRegistry(redis_client)

        all_skill_ids = await redis_client.smembers("skillweaver:registry:all_ids")
        compositions_count = await redis_client.llen("skillweaver:compositions")

        category_counts = {}
        for category in SkillCategory:
            count = len(await redis_client.smembers(f"skillweaver:registry:by_category:{category.value}"))
            category_counts[category.value] = count

        agent_counts: Dict[str, int] = {}
        for skill_id in all_skill_ids:
            skill_id_str = skill_id.decode() if isinstance(skill_id, bytes) else skill_id
            skill = await registry.get_skill(skill_id_str)
            if skill:
                agent_counts[skill.agent_id] = agent_counts.get(skill.agent_id, 0) + 1

        return {
            "total_skills": len(all_skill_ids),
            "total_compositions": compositions_count,
            "skills_by_category": category_counts,
            "skills_by_agent": agent_counts,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root() -> dict:
    """Root: show docs and routes summary."""
    return {
        "name": "SkillWeaver",
        "version": app.version,
        "docs": "/docs",
        "routes": {
            "health": "/health",
            "register": "POST /api/v1/skills/register",
            "register_batch": "POST /api/v1/skills/register_batch",
            "get": "GET /api/v1/skills/{skill_id}",
            "list": "GET /api/v1/skills/list",
            "discover": "POST /api/v1/skills/discover",
            "compose": "POST /api/v1/skills/compose",
            "history": "GET /api/v1/compositions/history",
            "stats": "GET /api/v1/stats",
            "deregister_agent": "DELETE /api/v1/skills/agent/{agent_id}",
        },
    }
