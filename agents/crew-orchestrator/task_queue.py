from arq.connections import RedisSettings
import httpx
import json
import logging

logger = logging.getLogger(__name__)

# Task definitions
async def execute_agent_task(ctx, agent_name: str, task: dict):
    """Worker function that executes agent tasks"""
    logger.info(f"Executing task {task.get('id')} on {agent_name}")
    
    agent_url = f"http://{agent_name}:8000" if ":" not in agent_name else agent_name
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(f"{agent_url}/execute", json=task)
            response.raise_for_status()
            result = response.json()
        
        # Store result in Redis
        task_id = task.get('id', 'unknown')
        await ctx['redis'].set(
            f"task_result:{task_id}", 
            json.dumps(result),
            ex=3600 * 24  # Expire after 24 hours
        )
        
        return result
    except Exception as e:
        logger.error(f"Task {task.get('id')} failed: {e}")
        # Could implement retry logic here or let ARQ handle it via retry_jobs
        raise

# Worker settings
class WorkerSettings:
    # Use environment variable or fallback to localhost for local dev, 'redis' for docker
    import os
    redis_host = os.getenv('ORCHESTRATOR_REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('ORCHESTRATOR_REDIS_PORT', 6379))
    
    redis_settings = RedisSettings(host=redis_host, port=redis_port)
    functions = [execute_agent_task]
    max_jobs = 10
    job_timeout = 600  # 10 minutes
    allow_abort_jobs = True

async def get_redis_pool():
    import os
    import redis.asyncio as aioredis

    redis_host = os.getenv('ORCHESTRATOR_REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('ORCHESTRATOR_REDIS_PORT', 6379))

    return await aioredis.from_url(
        f"redis://{redis_host}:{redis_port}",
        encoding="utf-8",
        decode_responses=True,
    )
