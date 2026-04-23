"""
🦅 GoalKeeper Agent - Self-Improving System Orchestrator

Runs the continuous self-improvement loops for the entire agent crew.
Monitors metrics, detects opportunities, proposes improvements, runs A/B tests.
"""

import asyncio
import os
import sys
import secrets
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Dict, Any

import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import structlog
import json

# Add shared modules
sys.path.insert(0, "/app")
from agents.goal_keeper.self_improvement_framework import (
    GoalKeeper,
    MetricsEngine,
    ImprovementType,
)
try:
    from shared.logging_config import setup_logging
except Exception:
    setup_logging = None

logger = structlog.get_logger()

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str = Security(_api_key_header)) -> str:
    expected = os.getenv("GOAL_KEEPER_API_KEY", "").strip()
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    if not expected:
        if environment == "development":
            if api_key and secrets.compare_digest(api_key, "dev-key"):
                return "dev-key"
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service misconfigured: GOAL_KEEPER_API_KEY is not set",
        )
    if not api_key or not secrets.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key


# ============================================================================
# CONFIG & MODELS
# ============================================================================

class ImprovementStatusRequest(BaseModel):
    """Request improvement status"""
    pass


class MetricsQueryRequest(BaseModel):
    """Query metrics for an agent"""
    agent_name: Optional[str] = None
    metric_type: str = "summary"  # summary, detailed, trends


class SkillQueryRequest(BaseModel):
    """Query skills for an agent"""
    agent_name: str


class FailureAnalysisRequest(BaseModel):
    """Analyze failure patterns"""
    agent_name: Optional[str] = None


class ImprovementHistoryRequest(BaseModel):
    """Get improvement history"""
    agent_name: Optional[str] = None
    limit: int = 50


# ============================================================================
# GOAL KEEPER AGENT
# ============================================================================

class GoalKeeperAgent:
    """Main agent implementation"""
    
    def __init__(self):
        self.config = {
            "name": os.getenv("AGENT_NAME", "goal-keeper"),
            "role": "Self-Improvement Orchestrator",
            "port": int(os.getenv("AGENT_PORT", "8050")),
            "core_url": os.getenv("CORE_URL", "http://hypercode-core:8000"),
            "redis_url": os.getenv("REDIS_URL", "redis://redis:6379"),
        }
        
        self.logger = logger
        self.redis = None
        self.goal_keeper = None
        self.goal_keeper_task: asyncio.Task[None] | None = None
        self.app = None
        self.agent_registry = {}
    
    def _setup_app(self):
        """Setup FastAPI app"""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await self.startup()
            yield
            await self.shutdown()
        
        self.app = FastAPI(
            title=f"{self.config['name']} Agent",
            lifespan=lifespan
        )
        
        # Routes
        @self.app.get("/")
        async def root():
            return {
                "agent": self.config["name"],
                "role": self.config["role"],
                "status": "ready"
            }
        
        @self.app.get("/health")
        async def health():
            try:
                if self.redis:
                    await self.redis.ping()
                return {"status": "healthy"}
            except Exception as e:
                raise HTTPException(status_code=503, detail=str(e))
        
        @self.app.post("/improvements/status")
        async def get_improvement_status(
            request: ImprovementStatusRequest, api_key: str = Depends(require_api_key)
        ):
            """Get current improvement status"""
            if not self.goal_keeper:
                raise HTTPException(status_code=503, detail="GoalKeeper not initialized")
            
            status = await self.goal_keeper.get_improvement_status()
            return status
        
        @self.app.post("/metrics/query")
        async def query_metrics(request: MetricsQueryRequest, api_key: str = Depends(require_api_key)):
            """Query agent metrics"""
            if not self.goal_keeper:
                raise HTTPException(status_code=503, detail="GoalKeeper not initialized")
            
            if request.agent_name:
                metrics = await self.goal_keeper.metrics_engine.get_agent_metrics(request.agent_name)
                if not metrics:
                    raise HTTPException(status_code=404, detail="Agent not found")
                
                return {
                    "agent": request.agent_name,
                    "metrics": {
                        "success_rate": metrics.success_rate,
                        "avg_quality": metrics.avg_quality_score,
                        "avg_duration_ms": metrics.avg_task_duration_ms,
                        "cost_per_task": metrics.cost_per_task_usd,
                        "total_cost": metrics.total_cost_usd,
                        "tasks_completed": metrics.tasks_completed,
                        "tasks_failed": metrics.tasks_failed,
                    }
                }
            else:
                system_metrics = await self.goal_keeper.metrics_engine.get_system_metrics()
                return {
                    "system": {
                        "timestamp": system_metrics.timestamp.isoformat(),
                        "overall_success_rate": system_metrics.overall_success_rate,
                        "total_tasks": system_metrics.total_tasks,
                        "tasks_per_minute": system_metrics.tasks_per_minute,
                        "total_cost_usd": system_metrics.total_cost_usd,
                        "healthy_agents": system_metrics.healthy_agents,
                        "degraded_agents": system_metrics.degraded_agents,
                        "failed_agents": system_metrics.failed_agents,
                    }
                }
        
        @self.app.post("/skills/query")
        async def query_skills(request: SkillQueryRequest, api_key: str = Depends(require_api_key)):
            """Get skills for an agent"""
            if not self.goal_keeper:
                raise HTTPException(status_code=503, detail="GoalKeeper not initialized")
            
            skills = await self.goal_keeper.skill_registry.get_agent_skills(request.agent_name)
            
            return {
                "agent": request.agent_name,
                "skills": [
                    {
                        "skill_id": s.skill_id,
                        "name": s.name,
                        "category": s.category,
                        "proficiency": s.proficiency_level,
                        "times_used": s.times_used,
                        "success_rate": s.success_rate,
                    }
                    for s in skills
                ]
            }
        
        @self.app.post("/failures/analyze")
        async def analyze_failures(
            request: FailureAnalysisRequest, api_key: str = Depends(require_api_key)
        ):
            """Analyze failure patterns"""
            if not self.goal_keeper:
                raise HTTPException(status_code=503, detail="GoalKeeper not initialized")
            
            if request.agent_name:
                # Analyze specific agent
                patterns = {}
                for key, pattern in self.goal_keeper.failure_detector.failure_patterns.items():
                    if pattern.agent_name == request.agent_name:
                        patterns[key] = {
                            "task_type": pattern.task_type,
                            "frequency": pattern.frequency,
                            "last_seen": pattern.last_seen.isoformat(),
                            "symptoms": pattern.symptoms,
                            "recovery_successful": pattern.recovery_successful,
                        }
                
                return {
                    "agent": request.agent_name,
                    "patterns": patterns
                }
            else:
                # System-wide analysis
                return {
                    "total_patterns": len(self.goal_keeper.failure_detector.failure_patterns),
                    "total_failures": len(self.goal_keeper.failure_detector.failure_history),
                    "patterns": [
                        {
                            "agent": p.agent_name,
                            "task_type": p.task_type,
                            "frequency": p.frequency,
                        }
                        for p in self.goal_keeper.failure_detector.failure_patterns.values()
                    ]
                }
        
        @self.app.post("/improvements/history")
        async def get_improvement_history(
            request: ImprovementHistoryRequest, api_key: str = Depends(require_api_key)
        ):
            """Get improvement history"""
            if not self.goal_keeper:
                raise HTTPException(status_code=503, detail="GoalKeeper not initialized")
            
            proposals = list(self.goal_keeper.proposal_engine.proposals.values())
            
            if request.agent_name:
                proposals = [p for p in proposals if p.agent_name == request.agent_name]
            
            # Sort by creation date, most recent first
            proposals.sort(key=lambda p: p.created_at, reverse=True)
            proposals = proposals[:request.limit]
            
            return {
                "improvements": [
                    {
                        "proposal_id": p.proposal_id,
                        "agent": p.agent_name,
                        "type": p.improvement_type.value,
                        "description": p.description,
                        "status": p.status,
                        "created_at": p.created_at.isoformat(),
                        "expected_impact": p.expected_impact,
                        "risk_level": p.risk_level,
                    }
                    for p in proposals
                ]
            }
        
        @self.app.get("/stream/improvements")
        async def stream_improvements(api_key: str = Depends(require_api_key)):
            """Stream real-time improvement events"""
            async def event_generator():
                last_id = "0-0"
                try:
                    while True:
                        if self.redis is None:
                            yield f"data: {json.dumps({'error': 'Redis not connected'})}\n\n"
                            return
                        entries = await self.redis.xread(
                            streams={"goal_keeper:events": last_id},
                            count=50,
                            block=15000,
                        )
                        if not entries:
                            continue
                        for _, messages in entries:
                            for message_id, fields in messages:
                                last_id = message_id
                                payload = fields.get("data")
                                if payload is None:
                                    continue
                                yield f"data: {payload}\n\n"
                except asyncio.CancelledError:
                    return
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return StreamingResponse(event_generator(), media_type="text/event-stream")
    
    async def startup(self):
        """Initialize on startup"""
        logger.info("goal_keeper_startup")
        
        # Connect to Redis
        try:
            self.redis = await redis.from_url(
                self.config["redis_url"],
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("redis_connected")
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            raise
        
        # Discover agents from Docker
        try:
            # Simple discovery: connect to core API and get agent list
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config['core_url']}/agents/registry"
                )
                if response.status_code == 200:
                    self.agent_registry = response.json().get("agents", {})
        except Exception as e:
            logger.error("agent_discovery_failed", error=str(e))
            # Continue anyway, can work with partial registry
        
        # Initialize GoalKeeper
        self.goal_keeper = GoalKeeper(self.redis, self.agent_registry)
        
        # Start improvement loops
        self.goal_keeper_task = asyncio.create_task(self.goal_keeper.start())
        
        logger.info("goal_keeper_initialized")
    
    async def shutdown(self):
        """Cleanup on shutdown"""
        if self.goal_keeper:
            await self.goal_keeper.stop()
        if self.goal_keeper_task:
            self.goal_keeper_task.cancel()
            try:
                await self.goal_keeper_task
            except asyncio.CancelledError:
                pass
        
        if self.redis:
            await self.redis.close()
        
        logger.info("goal_keeper_shutdown")
    
    def run(self):
        """Run the agent"""
        self._setup_app()
        
        import uvicorn
        uvicorn.run(
            self.app,
            host="0.0.0.0",
            port=self.config["port"],
            log_config=None
        )


# ============================================================================
# ENTRYPOINT
# ============================================================================

if __name__ == "__main__":
    agent = GoalKeeperAgent()
    agent.run()
