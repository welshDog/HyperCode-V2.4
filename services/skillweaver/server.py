"""
SkillWeaver FastAPI Server
==========================

HTTP API for SkillWeaver, enabling agents to:
- Register skills
- Discover skills
- Compose skills
- Monitor system health
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import List, Optional

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

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
    version="1.0.0"
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

class SkillMetadataRequest(BaseModel):
    """Register a new skill."""
    skill_id: str
    agent_id: str
    name: str
    description: str
    category: str  # "computation", "io", "orchestration", etc.
    inputs: dict  # {param_name: type}
    outputs: dict  # {field_name: type}
    timeout_seconds: float = 30.0
    retry_count: int = 1
    examples: List[str] = []
    version: str = "1.0.0"


class SkillDiscoveryRequest(BaseModel):
    """Discover relevant skills."""
    query: str
    category: Optional[str] = None
    top_k: int = 5


class SkillCompositionRequest(BaseModel):
    """Compose multiple skills into one."""
    skill_ids: List[str]
    strategy: str = "linear"  # "linear", "parallel", "conditional"


class SkillMatchResponse(BaseModel):
    """A discovered skill."""
    skill_id: str
    agent_id: str
    name: str
    description: str
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
# Endpoints
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    redis_client = await get_redis()
    logger.info("SkillWeaver server started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
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
    except:
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
        
        # Create SkillMetadata
        metadata = SkillMetadata(
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
            retry_count=req.retry_count,
            examples=req.examples,
            version=req.version,
        )
        
        # Register
        await registry.register_skill(metadata)
        
        # Add to global set for tracking
        await redis_client.sadd("skillweaver:registry:all_ids", req.skill_id)
        
        logger.info(f"Skill registered: {req.skill_id} from {req.agent_id}")
        
        return {
            "status": "registered",
            "skill_id": req.skill_id,
            "agent_id": req.agent_id,
            "message": f"Skill '{req.name}' registered successfully",
        }
    
    except ValueError as e:
        logger.error(f"Invalid skill registration: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error registering skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/skills/discover")
async def discover_skills(req: SkillDiscoveryRequest) -> List[SkillMatchResponse]:
    """Discover relevant skills based on query."""
    try:
        redis_client = await get_redis()
        weaver = SkillWeaver(redis_client)
        
        # Discover
        category = SkillCategory(req.category) if req.category else None
        matches = await weaver.discover_skills(
            query=req.query,
            category=category,
            top_k=req.top_k,
        )
        
        logger.info(f"Skill discovery: query='{req.query}', found={len(matches)}")
        
        # Convert to response
        return [
            SkillMatchResponse(
                skill_id=m.metadata.skill_id,
                agent_id=m.metadata.agent_id,
                name=m.metadata.name,
                description=m.metadata.description,
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
        
        # Validate
        valid, reason = await weaver.validate_composition(req.skill_ids)
        if not valid:
            logger.warning(f"Composition validation failed: {reason}")
            raise ValueError(f"Cannot compose: {reason}")
        
        # Compose
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
async def list_skills(agent_id: Optional[str] = None) -> dict:
    """List registered skills."""
    try:
        redis_client = await get_redis()
        registry = SkillRegistry(redis_client)
        
        if agent_id:
            skills = await registry.list_skills_by_agent(agent_id)
            logger.info(f"Listed {len(skills)} skills for agent {agent_id}")
        else:
            # List all
            all_skill_ids = await redis_client.smembers("skillweaver:registry:all_ids")
            skills = []
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
    
    except Exception as e:
        logger.error(f"Error listing skills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/compositions/history")
async def composition_history(limit: int = 10) -> dict:
    """Get recent composition history."""
    try:
        redis_client = await get_redis()
        weaver = SkillWeaver(redis_client)
        
        compositions = await redis_client.lrange(weaver.composition_log_key, 0, limit - 1)
        
        parsed = []
        for comp in compositions:
            parsed.append(json.loads(comp))
        
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
        
        # Count skills by category
        category_counts = {}
        for category in SkillCategory:
            count = len(await redis_client.smembers(f"skillweaver:registry:by_category:{category.value}"))
            category_counts[category.value] = count
        
        # Count skills by agent
        agent_counts = {}
        for skill_id in all_skill_ids:
            skill_id_str = skill_id.decode() if isinstance(skill_id, bytes) else skill_id
            skill = await registry.get_skill(skill_id_str)
            if skill:
                agent_id = skill.agent_id
                agent_counts[agent_id] = agent_counts.get(agent_id, 0) + 1
        
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


# ============================================================================
# WebSocket for real-time events (future enhancement)
# ============================================================================

@app.get("/stream/events")
async def stream_events():
    """Stream real-time SkillWeaver events (SSE)."""
    # TODO: Implement Server-Sent Events for real-time updates
    return {"status": "coming soon"}


# ============================================================================
# Root
# ============================================================================

@app.get("/")
async def root():
    """Welcome message."""
    return {
        "name": "SkillWeaver",
        "version": "1.0.0",
        "description": "Autonomous skill synthesis engine for agent evolution",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8051)
