"""
Agent Spawner Service — Lightweight Redis subscriber for on-demand container spawning.
Uses Docker SDK + docker compose plugin for spawning containers with proper settings.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Set

import docker
import redis.asyncio as redis

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DOCKER_COMPOSE_PROJECT = os.getenv("COMPOSE_PROJECT_NAME", "hypercode-v24")
COMPOSE_FILE = os.getenv("DOCKER_COMPOSE_FILE", "docker-compose.yml")
IDLE_SHUTDOWN_MINUTES = int(os.getenv("IDLE_SHUTDOWN_MINUTES", "5"))
ON_DEMAND_AGENTS = [a.strip() for a in os.getenv("ON_DEMAND_AGENTS", "").split(",") if a.strip()]
COMPOSE_CWD = os.getenv("COMPOSE_CWD", "/workspace")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Docker client
try:
    docker_client = docker.from_env()
    logger.info("Docker client initialized")
except Exception as e:
    logger.error(f"Failed to initialize Docker client: {e}")
    docker_client = None

# Track agent activity: {agent_name: last_activity_timestamp}
agent_activity: Dict[str, float] = {}
agent_spawn_lock: Set[str] = set()  # Prevent concurrent spawns


async def spawn_agent(agent_name: str) -> bool:
    """Spawn an on-demand agent by starting via docker compose."""
    if agent_name in agent_spawn_lock:
        logger.info(f"[{agent_name}] Already spawning, skipping duplicate request")
        return False

    agent_spawn_lock.add(agent_name)
    try:
        logger.info(f"[{agent_name}] Spawning agent via docker compose...")
        
        # Use docker compose to start the service
        cmd = [
            "docker", "compose",
            "-f", COMPOSE_FILE,
            "-f", "docker-compose.on-demand.yml",
            "-f", "docker-compose.spawner.yml",
            "-p", DOCKER_COMPOSE_PROJECT,
            "up", "-d",
            agent_name
        ]
        
        logger.info(f"[{agent_name}] Executing: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=COMPOSE_CWD,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"[{agent_name}] Spawned successfully")
                logger.info(f"[{agent_name}] Output: {result.stdout}")
                agent_activity[agent_name] = time.time()
                return True
            else:
                logger.error(f"[{agent_name}] Failed with code {result.returncode}")
                logger.error(f"[{agent_name}] stdout: {result.stdout}")
                logger.error(f"[{agent_name}] stderr: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"[{agent_name}] docker compose timed out")
            return False
        except Exception as e:
            logger.error(f"[{agent_name}] docker compose error: {e}")
            return False

    except Exception as e:
        logger.error(f"[{agent_name}] Spawn error: {e}")
        return False
    finally:
        agent_spawn_lock.discard(agent_name)


async def shutdown_agent(agent_name: str) -> bool:
    """Stop an on-demand agent."""
    if docker_client is None:
        return False
        
    try:
        logger.info(f"[{agent_name}] Shutting down due to inactivity...")
        container_name = f"{DOCKER_COMPOSE_PROJECT}_{agent_name}_1"
        
        # Try multiple naming conventions
        for name_variant in [agent_name, container_name]:
            try:
                container = docker_client.containers.get(name_variant)
                if container.status == "running":
                    container.stop(timeout=10)
                    logger.info(f"[{agent_name}] Shut down successfully")
                    agent_activity.pop(agent_name, None)
                    return True
            except docker.errors.NotFound:
                continue
            except Exception as e:
                logger.error(f"[{agent_name}] Error with {name_variant}: {e}")
                continue
                
        logger.info(f"[{agent_name}] Container not found for shutdown")
        agent_activity.pop(agent_name, None)
        return True
        
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
    try:
        logger.info("Initializing pubsub...")
        pubsub = r.pubsub()
        pattern = "agent:spawn:*"
        
        logger.info(f"Subscribing to pattern: {pattern}")
        await pubsub.psubscribe(pattern)
        logger.info(f"Successfully listening on pattern: {pattern}")

        async for message in pubsub.listen():
            logger.info(f"Message received: {message}")
            
            if message["type"] == "pmessage":
                channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
                data = message["data"].decode() if isinstance(message["data"], bytes) else message["data"]

                # Extract agent name from channel: "agent:spawn:coder-agent" -> "coder-agent"
                agent_name = channel.split(":")[-1]
                logger.info(f"[{agent_name}] Spawn request received")

                if agent_name not in ON_DEMAND_AGENTS:
                    logger.warning(f"[{agent_name}] Not in ON_DEMAND_AGENTS list, ignoring")
                    continue

                logger.info(f"[{agent_name}] Processing spawn request: {data}")

                # Check if already running
                if docker_client is not None:
                    try:
                        for name_variant in [agent_name, f"{DOCKER_COMPOSE_PROJECT}_{agent_name}_1"]:
                            try:
                                container = docker_client.containers.get(name_variant)
                                if container.status == "running":
                                    logger.info(f"[{agent_name}] Already running, updating activity")
                                    agent_activity[agent_name] = time.time()
                                    break
                            except docker.errors.NotFound:
                                continue
                        else:
                            # Not found, proceed to spawn
                            await spawn_agent(agent_name)
                            agent_activity[agent_name] = time.time()
                    except Exception as e:
                        logger.warning(f"[{agent_name}] Failed to check status: {e}")
                        await spawn_agent(agent_name)
                        agent_activity[agent_name] = time.time()
                else:
                    # No docker client, just spawn
                    await spawn_agent(agent_name)
                    agent_activity[agent_name] = time.time()

    except Exception as e:
        logger.error(f"Spawn listener error: {e}")
        raise
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
        logger.info(f"Connecting to Redis: {REDIS_URL}")
        r = await redis.from_url(REDIS_URL)
        logger.info("Connected to Redis")
        logger.info(f"ON_DEMAND_AGENTS: {ON_DEMAND_AGENTS}")
        logger.info(f"COMPOSE_CWD: {COMPOSE_CWD}")
        logger.info(f"COMPOSE_PROJECT: {DOCKER_COMPOSE_PROJECT}")

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
