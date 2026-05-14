import docker
import logging
import os
import asyncio
from typing import Optional
import redis.asyncio as redis
from ..models import ContainerStatus
from .discord_notifier import DiscordNotifier

logger = logging.getLogger("healer.docker")


class DockerAdapter:
    def __init__(self, redis_url: str = "redis://redis:6379"):
        """
        Initialize Docker Adapter with Redis connection for state tracking.
        """
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.client = None

        self.redis_url = redis_url
        self.redis = None
        self.notifier = DiscordNotifier()

    async def get_redis(self):
        """Lazy initialization of async redis client"""
        if not self.redis:
            self.redis = await redis.from_url(self.redis_url, decode_responses=True)
        return self.redis

    def get_container(self, name: str) -> Optional[ContainerStatus]:
        """
        Get current status of a container by name.
        """
        if not self.client:
            return None

        try:
            container = self.client.containers.get(name)
            state = container.attrs["State"]
            health_status = state.get("Health", {}).get("Status", "none")
            return ContainerStatus(
                name=name,
                status=state["Status"],
                health=health_status,
                started_at=state["StartedAt"],
                restart_count=container.attrs["RestartCount"]
            )
        except docker.errors.NotFound:
            logger.warning(f"Container {name} not found.")
            return None
        except Exception as e:
            logger.error(f"Error checking container {name}: {e}")
            return None

    async def check_all_containers(self) -> dict:
        """
        Scan all running containers and return their health status.
        Also detects OOM kills (exit 137 / OOMKilled flag) and fires Discord alerts.
        """
        if not self.client:
            return {"error": "Docker client not initialized"}

        report = {}
        try:
            containers = self.client.containers.list(all=True)
            for container in containers:
                name = container.name
                state = container.attrs["State"]
                health_status = state.get("Health", {}).get("Status", "none")
                oom_killed = state.get("OOMKilled", False)
                exit_code = state.get("ExitCode", 0)

                report[name] = {
                    "status": state["Status"],
                    "health": health_status,
                    "restarts": container.attrs["RestartCount"],
                    "oom_killed": oom_killed,
                    "exit_code": exit_code,
                }

                # OOM detected — flag is set OR exit code 137 on an exited container
                is_oom = oom_killed or (
                    state["Status"] in ("exited", "dead") and exit_code == 137
                )
                if is_oom:
                    await self._handle_oom(name, exit_code, container.attrs.get("RestartCount", 0))

        except Exception as e:
            logger.error(f"Error scanning containers: {e}")
            return {"error": str(e)}

        return report

    async def _handle_oom(self, name: str, exit_code: int, restart_count: int) -> None:
        """
        Called when a container is detected as OOM-killed.
        Deduplicates via Redis (one alert per container per 10 min window).
        Fires a Discord alert — never prints the webhook URL.
        """
        redis_client = await self.get_redis()
        dedup_key = f"healer:oom_alert:{name}"

        # Deduplicate — only alert once per 10-minute window per container
        already_alerted = await redis_client.get(dedup_key)
        if already_alerted:
            logger.debug(f"OOM alert for {name} already sent within dedup window, skipping.")
            return

        logger.warning(f"OOM kill detected: container={name} exit_code={exit_code} restarts={restart_count}")

        await self.notifier.send_oom_alert(
            container_name=name,
            exit_code=exit_code,
            restart_count=restart_count,
        )

        # Mark as alerted for 10 minutes
        await redis_client.setex(dedup_key, 600, "1")

    async def restart_container(self, name: str, force: bool = False) -> bool:
        """
        Restart a container with threshold checks (max 3 restarts in 5 mins).
        force=True bypasses the threshold check.
        """
        if not self.client:
            return False

        redis_client = await self.get_redis()
        key = f"healer:restarts:{name}"

        # Check thresholds unless forced
        if not force:
            count = await redis_client.get(key)
            if count and int(count) >= 3:
                logger.warning(f"Container {name} has reached max restart limit (3/5min). Skipping restart.")
                return False

        try:
            logger.info(f"Attempting to restart container: {name}")
            container = self.client.containers.get(name)
            container.restart()

            # Update restart counter with 5 min expiry
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, 300)  # 5 minutes TTL
            await pipe.execute()

            logger.info(f"Container {name} restarted successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to restart {name}: {e}")
            return False

    def get_logs(self, name: str, lines: int = 100) -> str:
        """
        Get recent logs from a container.
        """
        if not self.client:
            return "Docker client not initialized"

        try:
            container = self.client.containers.get(name)
            logs = container.logs(tail=lines).decode("utf-8", errors="replace")
            return logs
        except Exception as e:
            return f"Error fetching logs for {name}: {e}"
