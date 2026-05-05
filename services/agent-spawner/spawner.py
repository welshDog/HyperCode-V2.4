"""
Agent Spawner Service — Lightweight Redis subscriber for on-demand container spawning.
Listens on 'agent:spawn:<agent_name>' channels and boots containers via docker-compose.
Implements auto-shutdown after configurable idle time.
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, Set

import redis.asyncio as redis

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DOCKER_COMPOSE_FILE = os.getenv("DOCKER_COMPOSE_FILE", "docker-compose.yml")
COMPOSE_PROJECT = os.getenv("COMPOSE_PROJECT_NAME", "hypercode-v24")
IDLE_SHUTDOWN_MINUTES = int(os.getenv("IDLE_SHUTDOWN_MINUTES", "5"))
ON_DEMAND_AGENTS = os.getenv("ON_DEMAND_AGENTS", "").split(",")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Track agent activity: {agent_name: last_activity_timestamp}
agent_activity: Dict[str, float] = {}
agent_spawn_lock: Set[str] = set()  # Prevent concurrent spawns


async def spawn_agent(agent_name: str) -> bool:
    """Spawn an on-demand agent via docker-compose."""
    if agent_name in agent_spawn_lock:
        logger.info(f"[{agent_name}] Already spawning, skipping duplicate request")
        return False

    agent_spawn_lock.add(agent_name)
    try:
        logger.info(f"[{agent_name}] Spawning agent...")
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                DOCKER_COMPOSE_FILE,
                "-p",
                COMPOSE_PROJECT,
                "up",
                "-d",
                "--profile",
                "on-demand",
                agent_name,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            logger.info(f"[{agent_name}] Spawned successfully")
            agent_activity[agent_name] = time.time()
            return True
        else:
            logger.error(
                f"[{agent_name}] Spawn failed: {result.stderr}"
            )
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"[{agent_name}] Spawn timed out")
        return False
    except Exception as e:
        logger.error(f"[{agent_name}] Spawn error: {e}")
        return False
    finally:
        agent_spawn_lock.discard(agent_name)


async def shutdown_agent(agent_name: str) -> bool:
    """Shutdown an on-demand agent via docker-compose."""
    try:
        logger.info(f"[{agent_name}] Shutting down due to inactivity...")
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                DOCKER_COMPOSE_FILE,
                "-p",
                COMPOSE_PROJECT,
                "stop",
                agent_name,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode == 0:
            logger.info(f"[{agent_name}] Shut down successfully")
            agent_activity.pop(agent_name, None)
            return True
        else:
            logger.error(f"[{agent_name}] Shutdown failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"[{agent_name}] Shutdown error: {e}")
        return False


async def check_idle_agents():
    """Periodically check for idle agents and shut them down."""
    while True:
        try:
            await asyncio.sleep(30)  # Check every 30 seconds
            now = time.time()
            idle_threshold = now - (IDLE_SHUTDOWN_MINUTES * 60)

            for agent_name, last_activity in list(agent_activity.items()):
                if last_activity < idle_threshold and agent_name not in agent_spawn_lock:
                    await shutdown_agent(agent_name)

        except Exception as e:
            logger.error(f"Idle check error: {e}")


async def spawn_listener(r: redis.Redis):
    """Subscribe to agent spawn requests and process them."""
    pubsub = r.pubsub()
    pattern = "agent:spawn:*"

    await pubsub.psubscribe(pattern)
    logger.info(f"Listening on pattern: {pattern}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
                data = message["data"].decode() if isinstance(message["data"], bytes) else message["data"]

                # Extract agent name from channel: "agent:spawn:coder-agent" -> "coder-agent"
                agent_name = channel.split(":")[-1]

                if agent_name not in ON_DEMAND_AGENTS:
                    logger.warning(f"[{agent_name}] Not in ON_DEMAND_AGENTS list, ignoring")
                    continue

                logger.info(f"[{agent_name}] Spawn request received: {data}")

                # Check if already running
                try:
                    result = subprocess.run(
                        [
                            "docker",
                            "compose",
                            "-f",
                            DOCKER_COMPOSE_FILE,
                            "-p",
                            COMPOSE_PROJECT,
                            "ps",
                            agent_name,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if "Up" in result.stdout:
                        logger.info(f"[{agent_name}] Already running, updating activity")
                        agent_activity[agent_name] = time.time()
                        continue
                except Exception as e:
                    logger.warning(f"[{agent_name}] Failed to check status: {e}")

                # Spawn the agent
                await spawn_agent(agent_name)
                agent_activity[agent_name] = time.time()

    except Exception as e:
        logger.error(f"Spawn listener error: {e}")
    finally:
        await pubsub.close()


async def health_check(r: redis.Redis):
    """Simple health endpoint (for Docker healthcheck)."""
    while True:
        try:
            await r.ping()
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise


async def main():
    """Main spawner loop."""
    try:
        r = await redis.from_url(REDIS_URL)
        logger.info("Connected to Redis")

        # Start spawner and idle checker concurrently
        await asyncio.gather(
            spawn_listener(r),
            check_idle_agents(),
            health_check(r),
        )
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
