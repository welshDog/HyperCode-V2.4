import docker
import logging
import os
import asyncio
from typing import Optional
import redis.asyncio as redis
from ..models import ContainerStatus
from .discord_notifier import DiscordNotifier

logger = logging.getLogger("healer.docker")

# Threshold: alert if a container restarts this many times within the Redis TTL window (5 min)
RESTART_LOOP_THRESHOLD = int(os.environ.get("RESTART_LOOP_THRESHOLD", "5"))


class DockerAdapter:
    def __init__(
        self,
        redis_url: str = "redis://redis:6379",
        redis_client: Optional[redis.Redis] = None,
    ):
        """
        Initialize Docker Adapter with Redis connection for state tracking.
        """
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.client = None

        self.redis_url = redis_url
        self.redis = redis_client
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
        Detects:
          - OOM kills (exit 137 / OOMKilled flag) -> Discord OOM alert
          - Restart loops (>= RESTART_LOOP_THRESHOLD restarts in 5 min) -> Discord loop alert
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
                total_restarts = container.attrs["RestartCount"]

                report[name] = {
                    "status": state["Status"],
                    "health": health_status,
                    "restarts": total_restarts,
                    "oom_killed": oom_killed,
                    "exit_code": exit_code,
                }

                # --- OOM detection ---
                is_oom = oom_killed or (
                    state["Status"] in ("exited", "dead") and exit_code == 137
                )
                if is_oom:
                    await self._handle_oom(name, exit_code, total_restarts)

                # --- Restart-loop detection (reads the same Redis counter restart_container writes) ---
                await self._check_restart_loop(name, total_restarts)

        except Exception as e:
            logger.error(f"Error scanning containers: {e}")
            return {"error": str(e)}

        return report

    # ------------------------------------------------------------------
    # OOM handler
    # ------------------------------------------------------------------

    async def _handle_oom(self, name: str, exit_code: int, restart_count: int) -> None:
        """
        Called when a container is detected as OOM-killed.
        Deduplicates via Redis (one alert per container per 10-min window).
        """
        redis_client = await self.get_redis()
        dedup_key = f"healer:oom_alert:{name}"

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

        await redis_client.setex(dedup_key, 600, "1")  # 10-min dedup window

    # ------------------------------------------------------------------
    # Restart-loop detector
    # ------------------------------------------------------------------

    async def _check_restart_loop(self, name: str, total_restarts: int) -> None:
        """
        Reads the healer:restarts:{name} counter that restart_container() maintains.
        If the container has been restarted >= RESTART_LOOP_THRESHOLD times within
        the 5-min rolling window, fire a Discord alert (deduplicated per 15 min).

        Why a separate dedup key from the OOM one?
          - OOM and crash-loop are different root causes.
          - Different dedup windows (10 min OOM vs 15 min loop) reduce noise.
          - Lets ops distinguish "out of memory" from "crashing for another reason".
        """
        redis_client = await self.get_redis()

        # Counter written by restart_container() — 5-min rolling window TTL
        restart_key = f"healer:restarts:{name}"
        recent_count_raw = await redis_client.get(restart_key)
        recent_count = int(recent_count_raw) if recent_count_raw else 0

        if recent_count < RESTART_LOOP_THRESHOLD:
            return  # Not looping yet

        # Deduplicate — only one alert per 15-minute window per container
        dedup_key = f"healer:loop_alert:{name}"
        already_alerted = await redis_client.get(dedup_key)
        if already_alerted:
            logger.debug(f"Restart-loop alert for {name} already sent within dedup window, skipping.")
            return

        logger.warning(
            f"Restart loop detected: container={name} recent_restarts={recent_count} "
            f"(threshold={RESTART_LOOP_THRESHOLD}/5min) total_lifetime={total_restarts}"
        )

        await self.notifier.send_custom_alert(
            title="🔁 Crash-Loop Detected",
            description=(
                f"Container **`{name}`** has restarted **{recent_count} times in the last 5 minutes**.\n"
                f"This is a crash loop — something is wrong beyond a one-off failure."
            ),
            color=0xFF8800,  # Orange (different from OOM red so ops can tell them apart at a glance)
            fields=[
                {
                    "name": "Container",
                    "value": f"`{name}`",
                    "inline": True,
                },
                {
                    "name": "Restarts (last 5 min)",
                    "value": str(recent_count),
                    "inline": True,
                },
                {
                    "name": "Lifetime Restarts",
                    "value": str(total_restarts),
                    "inline": True,
                },
                {
                    "name": "What to do",
                    "value": (
                        f"1️⃣ `docker logs {name} --tail 50` to see the crash reason\n"
                        f"2️⃣ Check env vars / secrets are mounted correctly\n"
                        f"3️⃣ Check healthcheck command is correct\n"
                        f"4️⃣ Consider raising memory or CPU limits if resource-starved"
                    ),
                    "inline": False,
                },
            ],
        )

        await redis_client.setex(dedup_key, 900, "1")  # 15-min dedup window

    # ------------------------------------------------------------------
    # restart_container — unchanged logic, kept here for reference
    # ------------------------------------------------------------------

    async def restart_container(self, name: str, force: bool = False) -> bool:
        """
        Restart a container with threshold checks (max 3 restarts in 5 mins).
        force=True bypasses the threshold check.
        """
        if not self.client:
            return False

        redis_client = await self.get_redis()
        key = f"healer:restarts:{name}"

        if not force:
            count = await redis_client.get(key)
            if count and int(count) >= 3:
                logger.warning(f"Container {name} has reached max restart limit (3/5min). Skipping restart.")
                return False

        try:
            logger.info(f"Attempting to restart container: {name}")
            container = self.client.containers.get(name)
            container.restart()

            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, 300)  # 5-minute rolling window
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
