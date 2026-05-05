"""
Agent spawn trigger — helper module for hypercode-core to request on-demand agent spawning.
Call: spawn_agent("coder-agent", task_context="analyze this code")
"""

import redis
import json
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AgentSpawner:
    def __init__(self, redis_url: str = "redis://redis:6379/0"):
        self.redis_url = redis_url
        self.r = redis.from_url(redis_url, decode_responses=True)

    def spawn_agent(
        self,
        agent_name: str,
        task_context: Optional[str] = None,
        priority: str = "normal",
        timeout_seconds: int = 120,
    ) -> bool:
        """
        Request spawning of an on-demand agent.
        
        Args:
            agent_name: Name of the agent (coder-agent, hyper-architect, etc.)
            task_context: Optional task description (used by agent-spawner for logging)
            priority: 'high' or 'normal' (for future queue implementation)
            timeout_seconds: How long to wait for agent to become ready
            
        Returns:
            True if spawn request published successfully
        """
        try:
            payload = {
                "agent": agent_name,
                "context": task_context,
                "priority": priority,
                "timeout": timeout_seconds,
            }
            
            channel = f"agent:spawn:{agent_name}"
            self.r.publish(channel, json.dumps(payload))
            logger.info(f"Spawned {agent_name} with context: {task_context}")
            return True
        except Exception as e:
            logger.error(f"Failed to spawn {agent_name}: {e}")
            return False

    def keep_alive(self, agent_name: str) -> bool:
        """Update agent's last-activity timestamp to prevent idle shutdown."""
        try:
            key = f"agent:activity:{agent_name}"
            self.r.set(key, redis.time(), ex=3600)  # 1-hour expiry
            return True
        except Exception as e:
            logger.error(f"Failed to keep-alive {agent_name}: {e}")
            return False

    def shutdown_agent(self, agent_name: str) -> bool:
        """Manually request shutdown of an on-demand agent."""
        try:
            channel = f"agent:shutdown:{agent_name}"
            self.r.publish(channel, json.dumps({"agent": agent_name}))
            logger.info(f"Shutdown requested for {agent_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to shutdown {agent_name}: {e}")
            return False


# Usage in hypercode-core FastAPI endpoints:
# 
# from spawner import AgentSpawner
# 
# spawner = AgentSpawner()
# 
# @app.post("/api/agents/{agent_name}/spawn")
# async def spawn_agent(agent_name: str, task: TaskRequest):
#     if spawner.spawn_agent(agent_name, task_context=task.description):
#         return {"status": "spawning", "agent": agent_name}
#     return {"status": "failed", "agent": agent_name}, 500
#
# @app.post("/api/agents/{agent_name}/keep-alive")
# async def keep_alive(agent_name: str):
#     spawner.keep_alive(agent_name)
#     return {"status": "ok"}
