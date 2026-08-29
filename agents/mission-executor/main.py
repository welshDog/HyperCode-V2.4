# agents/mission-executor/main.py
"""
mission-executor -- Phase 3 Live Execution Engine.

Receives approved MissionProposals via Redis pub/sub and executes them
using specialist agents. Has ZERO LLM interpretation capability - only
executes predefined plans from mission-director.

Maintains strict separation: execution engine only executes, never interprets LLMs.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, Optional

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent_delegator import AgentDelegator, DelegationResult
from models import ExecutionRequest, ExecutionResult, ExecutionStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
EXECUTION_CHANNEL = os.getenv("MISSION_EXECUTION_CHANNEL", "mission_executions")
RESULT_CHANNEL = os.getenv("MISSION_RESULT_CHANNEL", "mission_results")
EXECUTION_TIMEOUT = int(os.getenv("MISSION_EXECUTION_TIMEOUT", "300"))  # 5 minutes default


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize resources on startup, cleanup on shutdown."""
    # Initialize Redis connection
    app.state.redis = redis.from_url(REDIS_URL)
    app.state.pubsub = app.state.redis.pubsub()

    # Initialize agent delegator
    app.state.agent_delegator = AgentDelegator()

    # Subscribe to execution channel
    await app.state.pubsub.subscribe(EXECUTION_CHANNEL)

    # Start background task to process execution requests
    app.state.execution_task = asyncio.create_task(
        _process_execution_requests(app.state)
    )

    logger.info("Mission Executor started")
    yield

    # Cleanup
    app.state.execution_task.cancel()
    try:
        await app.state.execution_task
    except asyncio.CancelledError:
        pass

    await app.state.pubsub.unsubscribe(EXECUTION_CHANNEL)
    await app.state.redis.close()
    logger.info("Mission Executor stopped")


app = FastAPI(
    title="mission-executor",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "agent": "mission-executor"}


@app.post("/execute", response_model=ExecutionResult)
async def execute_mission(request: ExecutionRequest) -> ExecutionResult:
    """
    Direct execution endpoint (for testing/manual triggering).
    In production, executions come via Redis pub/sub.
    """
    logger.info(f"Received direct execution request for mission {request.mission_id}")

    # Execute the mission plan
    result = await app.state.agent_delegator.execute_plan(
        mission_id=request.mission_id,
        plan_request=request.plan,
        timeout=EXECUTION_TIMEOUT
    )

    # Publish result to Redis for monitoring/ledger updates
    await _publish_result(result)

    return result


async def _process_execution_requests(state) -> None:
    """Background task to process execution requests from Redis."""
    logger.info(f"Listening for execution requests on channel: {EXECUTION_CHANNEL}")

    async for message in state.pubsub.listen():
        if message["type"] != "message":
            continue

        try:
            data = json.loads(message["data"])
            request = ExecutionRequest(**data)

            logger.info(
                f"Received execution request for mission {request.mission_id} "
                f"(goal: {request.goal[:50]}...)"
            )

            # Execute the mission plan
            result = await state.agent_delegator.execute_plan(
                mission_id=request.mission_id,
                plan_request=request.plan,
                timeout=EXECUTION_TIMEOUT
            )

            # Publish result
            await _publish_result(result, state.redis)

            logger.info(
                f"Completed execution for mission {request.mission_id} "
                f"with status: {result.status}"
            )

        except json.JSONDecodeError:
            logger.error("Failed to decode execution request JSON")
        except Exception as e:
            logger.error(f"Error processing execution request: {e}")
            # Publish error result if we have mission_id
            if 'data' in locals() and 'mission_id' in data:
                error_result = ExecutionResult(
                    mission_id=data["mission_id"],
                    status=ExecutionStatus.FAILED,
                    error_message=f"Execution engine error: {str(e)}",
                    executed_actions=[],
                    agent_outputs={}
                )
                await _publish_result(error_result, state.redis)


async def _publish_result(result: ExecutionResult, redis_client: Optional[redis.Redis] = None) -> None:
    """Publish execution result to Redis channel."""
    client = redis_client or redis.from_url(REDIS_URL)
    try:
        await client.publish(
            RESULT_CHANNEL,
            result.model_dump_json()
        )
    finally:
        if redis_client is None:
            await client.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)