"""
Agent X — Docker Operations
============================
All Docker build / deploy / rollback logic lives here.
Uses Docker CLI via subprocess (matches existing devops-engineer pattern).
Requires /var/run/docker.sock mounted into the container.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Repo root mounted into Agent X container
WORKSPACE = os.getenv("WORKSPACE_PATH", "/workspace")
COMPOSE_FILE = os.getenv(
    "HYPER_AGENTS_COMPOSE",
    f"{WORKSPACE}/docker-compose.hyper-agents.yml",
)
AGENTS_COMPOSE_FILE = os.getenv(
    "AGENTS_COMPOSE",
    f"{WORKSPACE}/docker-compose.agents.yml",
)


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    success: bool = field(init=False)

    def __post_init__(self) -> None:
        self.success = self.returncode == 0

    @property
    def output(self) -> str:
        return self.stdout or self.stderr


@dataclass
class BuildResult:
    image_tag: str
    success: bool
    duration_seconds: float
    logs: str
    error: Optional[str] = None


@dataclass
class DeployResult:
    service_name: str
    success: bool
    old_image: Optional[str]
    new_image: str
    logs: str
    error: Optional[str] = None


async def _run(cmd: list[str], cwd: Optional[str] = None) -> CommandResult:
    """Run a shell command asynchronously and capture output."""
    logger.debug(f"Running: {' '.join(cmd)}")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd or WORKSPACE,
    )
    stdout, stderr = await proc.communicate()
    return CommandResult(
        returncode=proc.returncode or 0,
        stdout=stdout.decode("utf-8", errors="replace"),
        stderr=stderr.decode("utf-8", errors="replace"),
    )


# ── Container inventory ───────────────────────────────────────────────────────

async def list_containers(label: Optional[str] = None) -> list[dict[str, Any]]:
    """List running containers. Optionally filter by Docker label."""
    cmd = [
        "docker", "ps", "--format",
        "{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}",
    ]
    if label:
        cmd += ["--filter", f"label={label}"]
    result = await _run(cmd)
    if not result.success:
        return []
    containers = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            containers.append({
                "name": parts[0],
                "image": parts[1],
                "status": parts[2] if len(parts) > 2 else "",
                "ports": parts[3] if len(parts) > 3 else "",
            })
    return containers


async def get_container_image(container_name: str) -> Optional[str]:
    """Return the current image tag for a running container."""
    result = await _run([
        "docker", "inspect", "--format", "{{.Config.Image}}", container_name
    ])
    return result.stdout.strip() if result.success else None


async def container_health(container_name: str) -> dict[str, Any]:
    """Return health status for a container."""
    result = await _run([
        "docker", "inspect",
        "--format", "{{.State.Health.Status}}\t{{.State.Status}}",
        container_name,
    ])
    if not result.success:
        return {"container": container_name, "reachable": False}
    parts = result.stdout.strip().split("\t")
    return {
        "container": container_name,
        "health": parts[0] if len(parts) > 0 else "unknown",
        "state": parts[1] if len(parts) > 1 else "unknown",
        "reachable": True,
    }


# ── Image build ───────────────────────────────────────────────────────────────

async def build_image(
    name: str,
    version: str,
    dockerfile_path: str,
    context_path: str = WORKSPACE,
) -> BuildResult:
    """Build a Docker image and tag it.

    Args:
        name: Agent name (e.g. 'hyper-worker')
        version: Version string (e.g. 'v2.1.0')
        dockerfile_path: Path to Dockerfile, relative to context or absolute
        context_path: Docker build context directory
    """
    tag = f"hypercode/{name}:{version}"
    tag_latest = f"hypercode/{name}:latest"

    start = asyncio.get_event_loop().time()
    result = await _run(
        [
            "docker", "build",
            "--tag", tag,
            "--tag", tag_latest,
            "--file", dockerfile_path,
            "--label", "hypercode.agent=true",
            "--label", f"hypercode.agent.name={name}",
            "--label", f"hypercode.agent.version={version}",
            "--label", f"hypercode.built_at={datetime.utcnow().isoformat()}",
            context_path,
        ],
        cwd=context_path,
    )
    duration = asyncio.get_event_loop().time() - start

    if result.success:
        logger.info(f"[DockerOps] Built {tag} in {duration:.1f}s")
        return BuildResult(
            image_tag=tag,
            success=True,
            duration_seconds=round(duration, 2),
            logs=result.output,
        )

    logger.error(f"[DockerOps] Build FAILED for {tag}: {result.stderr[:500]}")
    return BuildResult(
        image_tag=tag,
        success=False,
        duration_seconds=round(duration, 2),
        logs=result.output,
        error=result.stderr[:1000],
    )


# ── Deploy / restart ──────────────────────────────────────────────────────────

async def deploy_service(
    service_name: str,
    compose_file: str = COMPOSE_FILE,
    build: bool = False,
) -> DeployResult:
    """Deploy (or redeploy) a single service in a compose stack.

    Uses `docker compose up -d --no-deps` for zero-downtime single-service restart.
    """
    old_image = await get_container_image(service_name)

    cmd = [
        "docker", "compose",
        "-f", compose_file,
        "up", "-d", "--no-deps",
    ]
    if build:
        cmd.append("--build")
    cmd.append(service_name)

    result = await _run(cmd, cwd=WORKSPACE)
    new_image = await get_container_image(service_name) or "unknown"

    if result.success:
        logger.info(f"[DockerOps] Deployed {service_name}: {old_image} → {new_image}")
        return DeployResult(
            service_name=service_name,
            success=True,
            old_image=old_image,
            new_image=new_image,
            logs=result.output,
        )

    logger.error(f"[DockerOps] Deploy FAILED for {service_name}: {result.stderr[:500]}")
    return DeployResult(
        service_name=service_name,
        success=False,
        old_image=old_image,
        new_image=new_image,
        logs=result.output,
        error=result.stderr[:1000],
    )


async def restart_service(service_name: str) -> CommandResult:
    """Quick restart a container without rebuilding."""
    return await _run(["docker", "restart", service_name])


async def pull_image(image: str) -> CommandResult:
    """Pull an image from the registry."""
    return await _run(["docker", "pull", image])


# ── Health verification ───────────────────────────────────────────────────────

async def wait_for_healthy(
    container_name: str,
    timeout_seconds: int = 60,
    poll_interval: int = 5,
) -> bool:
    """Poll container health until healthy or timeout.

    Returns True if container becomes healthy within timeout.
    """
    deadline = asyncio.get_event_loop().time() + timeout_seconds
    while asyncio.get_event_loop().time() < deadline:
        health = await container_health(container_name)
        if health.get("health") == "healthy":
            return True
        if health.get("state") == "exited":
            logger.warning(f"[DockerOps] {container_name} exited — aborting health wait")
            return False
        await asyncio.sleep(poll_interval)
    logger.warning(f"[DockerOps] {container_name} did not become healthy within {timeout_seconds}s")
    return False


# ── Rollback ──────────────────────────────────────────────────────────────────

async def rollback_to_image(container_name: str, previous_image: str) -> CommandResult:
    """Force a container to use a specific previous image by re-tagging and restarting."""
    # Tag the previous image as latest for this service
    service = container_name.lstrip("hyper-")
    retag = await _run([
        "docker", "tag", previous_image, f"hypercode/{service}:latest"
    ])
    if not retag.success:
        return retag
    return await restart_service(container_name)


# ── Code writing ──────────────────────────────────────────────────────────────

def write_agent_file(relative_path: str, content: str) -> str:
    """Write generated agent code to the workspace.

    Returns the absolute path written.
    Raises if path tries to escape the workspace (safety check).
    """
    abs_path = os.path.normpath(os.path.join(WORKSPACE, relative_path))
    if not abs_path.startswith(os.path.normpath(WORKSPACE)):
        raise ValueError(f"Path escape attempt blocked: {relative_path}")
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"[DockerOps] Wrote {len(content)} bytes → {abs_path}")
    return abs_path
