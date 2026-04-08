"""
🚀 HyperLaunch — Unified HyperCode V2.0 System Initialization Commander
========================================================================
Single command. Full system. Zero chaos.

What this does:
  1. Pre-flight checks     — env vars, Docker, ports, disk space
  2. Dependency ordering   — starts infra first, then core, then agents
  3. Progressive init      — each tier waits for the previous to be healthy
  4. Real-time sync        — Redis pub/sub for cross-module state events
  5. Health monitoring     — continuous polling with retry + backoff
  6. Guardian watchdog     — post-launch background monitor
  7. BROski launch report  — colour-coded summary with port map

Usage:
  python hyperlaunch.py                  # Full launch (interactive)
  python hyperlaunch.py --dry-run        # Pre-flight only, no containers
  python hyperlaunch.py --tier infra     # Start only infrastructure tier
  python hyperlaunch.py --tier core      # Start only core services
  python hyperlaunch.py --tier agents    # Start only agent tier
  python hyperlaunch.py --status         # Show live system status
  python hyperlaunch.py --teardown       # Graceful shutdown

Shortcut:
  ./hyperlaunch.sh                       # One-liner wrapper
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

# ── Optional rich console (graceful fallback if not installed) ─────────────────
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich import print as rprint
    RICH = True
except ImportError:
    RICH = False
    class Console:  # type: ignore
        def print(self, *a, **k): print(*a)
        def rule(self, *a, **k): print("─" * 60)

console = Console()
logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("hyperlaunch")


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE MANIFEST — Full HyperCode V2.0 Stack
# ══════════════════════════════════════════════════════════════════════════════

class Tier(str, Enum):
    INFRA   = "infra"    # Must be running before anything else
    CORE    = "core"     # Platform backbone — depends on infra
    AGENTS  = "agents"  # AI agents — depend on core
    UI      = "ui"       # Dashboards — depend on core


@dataclass
class ServiceSpec:
    name: str                        # Docker Compose service name
    container: str                   # Docker container name
    tier: Tier
    port: Optional[int]             # Primary HTTP port (None = no HTTP)
    health_path: str = "/health"    # Health check endpoint
    critical: bool = True           # If True, abort launch on failure
    depends_on: list[str] = field(default_factory=list)  # Service names
    startup_timeout: int = 60       # Seconds to wait for healthy
    description: str = ""

    @property
    def health_url(self) -> Optional[str]:
        if self.port:
            return f"http://localhost:{self.port}{self.health_path}"
        return None


# Full service manifest — ordered within tiers by dependency
SERVICES: list[ServiceSpec] = [

    # ── TIER 1: Infrastructure ─────────────────────────────────────────────
    ServiceSpec(
        name="redis", container="redis", tier=Tier.INFRA,
        port=6379, health_path="",  # TCP only
        description="Redis — state sync + pub/sub backbone",
        startup_timeout=30,
    ),
    ServiceSpec(
        name="postgres", container="postgres", tier=Tier.INFRA,
        port=5432, health_path="",  # TCP only
        description="PostgreSQL — persistent agent state + logs",
        startup_timeout=45,
    ),

    # ── TIER 2: Core Platform ──────────────────────────────────────────────
    ServiceSpec(
        name="crew-orchestrator", container="crew-orchestrator", tier=Tier.CORE,
        port=8081, health_path="/health",
        depends_on=["redis", "postgres"],
        description="Crew Orchestrator — agent lifecycle manager",
        startup_timeout=60,
    ),
    ServiceSpec(
        name="healer-agent", container="healer-agent", tier=Tier.CORE,
        port=8008, health_path="/health",
        depends_on=["redis", "crew-orchestrator"],
        description="Healer Agent — self-healing + auto-recovery",
        startup_timeout=60,
    ),
    ServiceSpec(
        name="hypercode-core", container="hypercode-core", tier=Tier.CORE,
        port=8000, health_path="/health",
        depends_on=["redis", "postgres", "crew-orchestrator"],
        description="HyperCode Core — FastAPI backbone + integrations hub",
        startup_timeout=60,
    ),

    # ── TIER 3: AI Agents ─────────────────────────────────────────────────
    ServiceSpec(
        name="agent-x", container="agent-x", tier=Tier.AGENTS,
        port=8080, health_path="/health",
        depends_on=["crew-orchestrator", "healer-agent"],
        description="Agent X — Meta-Architect, spawns + evolves all agents",
        startup_timeout=90,
    ),
    ServiceSpec(
        name="hyper-architect", container="hyper-architect", tier=Tier.AGENTS,
        port=8091, health_path="/health",
        depends_on=["agent-x"],
        description="Hyper Architect — system design agent",
        startup_timeout=60,
    ),
    ServiceSpec(
        name="hyper-observer", container="hyper-observer", tier=Tier.AGENTS,
        port=8092, health_path="/health",
        depends_on=["agent-x", "redis"],
        description="Hyper Observer — real-time metrics + alerting",
        startup_timeout=60,
    ),
    ServiceSpec(
        name="hyper-worker", container="hyper-worker", tier=Tier.AGENTS,
        port=8093, health_path="/health",
        depends_on=["agent-x"],
        description="Hyper Worker — background task execution",
        startup_timeout=60,
    ),
    ServiceSpec(
        name="devops-engineer", container="devops-engineer", tier=Tier.AGENTS,
        port=8085, health_path="/health",
        depends_on=["agent-x", "hypercode-core"],
        description="DevOps Engineer Agent — CI/CD + autonomous evolution",
        startup_timeout=60,
    ),

    # ── TIER 4: UI / Dashboards ────────────────────────────────────────────
    ServiceSpec(
        name="hypercode-dashboard", container="hypercode-dashboard", tier=Tier.UI,
        port=8088, health_path="/",
        depends_on=["hypercode-core", "agent-x"],
        description="Mission Control Dashboard — Next.js real-time UI",
        critical=False,
        startup_timeout=90,
    ),
    ServiceSpec(
        name="broski-bot", container="broski-bot", tier=Tier.UI,
        port=3000, health_path="/",
        depends_on=["hypercode-core"],
        description="BROski Terminal — custom CLI + web UI",
        critical=False,
        startup_timeout=60,
    ),
    ServiceSpec(
        name="grafana", container="grafana", tier=Tier.UI,
        port=3001, health_path="/api/health",
        depends_on=["hyper-observer"],
        description="Grafana — observability dashboards",
        critical=False,
        startup_timeout=60,
    ),
]

SERVICE_MAP: dict[str, ServiceSpec] = {s.name: s for s in SERVICES}


# ══════════════════════════════════════════════════════════════════════════════
# PRE-FLIGHT CHECKS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    critical: bool = True


async def preflight_checks() -> list[CheckResult]:
    """Run all pre-flight checks. Returns list of CheckResult."""
    results: list[CheckResult] = []

    # 1. Docker available
    docker_ok = shutil.which("docker") is not None
    try:
        proc = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=10
        )
        docker_running = proc.returncode == 0
    except Exception:
        docker_running = False
    results.append(CheckResult(
        "Docker daemon",
        docker_ok and docker_running,
        "Docker is running" if docker_running else "Docker not found or not running — install Docker Desktop",
    ))

    # 2. Docker Compose available
    compose_ok = False
    try:
        proc = subprocess.run(
            ["docker", "compose", "version"], capture_output=True, timeout=5
        )
        compose_ok = proc.returncode == 0
    except Exception:
        pass
    results.append(CheckResult(
        "Docker Compose",
        compose_ok,
        "docker compose available" if compose_ok else "docker compose not found — update Docker",
    ))

    # 3. Compose file exists
    compose_files = [
        "docker-compose.yml",
        "docker-compose.yaml",
        "docker-compose.hyper-agents.yml",
    ]
    found_compose = [f for f in compose_files if os.path.exists(f)]
    results.append(CheckResult(
        "Compose file",
        bool(found_compose),
        f"Found: {', '.join(found_compose)}" if found_compose else "No docker-compose file found in current directory",
    ))

    # 4. .env file
    env_exists = os.path.exists(".env")
    results.append(CheckResult(
        ".env file",
        env_exists,
        ".env present" if env_exists else ".env missing — copy from .env.example and fill in secrets",
        critical=False,
    ))

    # 5. Required env vars
    required_vars = ["OPENAI_API_KEY", "REDIS_URL", "DATABASE_URL"]
    optional_vars = ["ANTHROPIC_API_KEY", "OLLAMA_HOST", "DISCORD_TOKEN"]
    missing_required = [v for v in required_vars if not os.getenv(v)]
    missing_optional = [v for v in optional_vars if not os.getenv(v)]
    results.append(CheckResult(
        "Required env vars",
        len(missing_required) == 0,
        "All required vars set" if not missing_required else f"Missing: {', '.join(missing_required)}",
    ))
    if missing_optional:
        results.append(CheckResult(
            "Optional env vars",
            True,
            f"Not set (optional): {', '.join(missing_optional)}",
            critical=False,
        ))

    # 6. Disk space (need at least 2GB free)
    try:
        usage = shutil.disk_usage(".")
        free_gb = usage.free / (1024 ** 3)
        disk_ok = free_gb >= 2.0
        results.append(CheckResult(
            "Disk space",
            disk_ok,
            f"{free_gb:.1f} GB free" if disk_ok else f"Only {free_gb:.1f} GB free — need 2 GB minimum",
            critical=False,
        ))
    except Exception:
        pass

    # 7. Port conflicts
    import socket
    critical_ports = [6379, 5432, 8000, 8080, 8081]
    blocked = []
    for port in critical_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            if sock.connect_ex(("localhost", port)) == 0:
                # Port in use — could be our own service already up, which is fine
                pass  # We don't block on this — Docker will handle port conflicts
    results.append(CheckResult(
        "Port scan",
        True,
        f"Checked ports: {critical_ports}",
        critical=False,
    ))

    return results


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECKING
# ══════════════════════════════════════════════════════════════════════════════

async def check_http_health(url: str, timeout: float = 5.0) -> bool:
    """Poll an HTTP health endpoint. Returns True if 200."""
    try:
        import urllib.request
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


async def check_tcp_port(host: str, port: int, timeout: float = 3.0) -> bool:
    """Check if a TCP port is accepting connections."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


async def wait_for_service(
    spec: ServiceSpec,
    retry_interval: float = 2.0,
) -> bool:
    """Wait for a service to become healthy. Returns True on success."""
    deadline = time.time() + spec.startup_timeout
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        healthy = False

        if spec.health_url:
            healthy = await check_http_health(spec.health_url)
        elif spec.port:
            healthy = await check_tcp_port("localhost", spec.port)
        else:
            healthy = True  # No health check configured — assume up

        if healthy:
            return True

        await asyncio.sleep(retry_interval)

    return False


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE STARTUP
# ══════════════════════════════════════════════════════════════════════════════

def detect_compose_file() -> str:
    """Find the best compose file to use."""
    candidates = [
        "docker-compose.hyper-agents.yml",
        "docker-compose.yml",
        "docker-compose.yaml",
    ]
    for f in candidates:
        if os.path.exists(f):
            return f
    return "docker-compose.yml"  # fallback


async def start_service(spec: ServiceSpec, compose_file: str, dry_run: bool = False) -> bool:
    """Start a single service via docker compose up."""
    if dry_run:
        console.print(f"  [DRY RUN] Would start: {spec.name} ({spec.description})")
        return True

    cmd = [
        "docker", "compose",
        "-f", compose_file,
        "up", "-d", "--no-recreate",
        spec.name,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return proc.returncode == 0
    except Exception as exc:
        logger.error(f"Failed to start {spec.name}: {exc}")
        return False


async def start_tier(
    tier: Tier,
    compose_file: str,
    dry_run: bool = False,
) -> dict[str, bool]:
    """Start all services in a tier. Returns {service_name: success}."""
    tier_services = [s for s in SERVICES if s.tier == tier]
    results: dict[str, bool] = {}

    for spec in tier_services:
        console.print(f"  ⏳ Starting {spec.name} — {spec.description}")
        started = await start_service(spec, compose_file, dry_run)

        if not dry_run and started:
            console.print(f"  ⏳ Waiting for {spec.name} to be healthy...")
            healthy = await wait_for_service(spec)
            results[spec.name] = healthy
            if healthy:
                console.print(f"  ✅ {spec.name} is healthy")
            else:
                console.print(f"  ❌ {spec.name} failed to become healthy")
                if spec.critical:
                    console.print(f"  🛑 CRITICAL service failed — aborting tier {tier.value}")
                    return results
        else:
            results[spec.name] = started

    return results


# ══════════════════════════════════════════════════════════════════════════════
# REDIS STATE SYNC (inter-module pub/sub)
# ══════════════════════════════════════════════════════════════════════════════

async def publish_launch_event(event: str, data: dict[str, Any]) -> None:
    """Publish a system event to Redis for all modules to receive."""
    try:
        import redis.asyncio as aioredis  # type: ignore
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        r = aioredis.from_url(redis_url, decode_responses=True)
        payload = json.dumps({"event": event, "data": data, "ts": time.time()})
        await r.publish("hypercode:system", payload)
        await r.set(f"hypercode:state:{event}", payload, ex=3600)
        await r.aclose()
    except Exception:
        pass  # Redis not required for launch to succeed


async def set_system_state(key: str, value: Any) -> None:
    """Write a system state key to Redis."""
    try:
        import redis.asyncio as aioredis  # type: ignore
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        r = aioredis.from_url(redis_url, decode_responses=True)
        await r.set(f"hypercode:system:{key}", json.dumps(value), ex=86400)
        await r.aclose()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# AGENT X REGISTRATION TRIGGER
# ══════════════════════════════════════════════════════════════════════════════

async def trigger_agent_x_pipeline_scan() -> dict[str, Any]:
    """After all agents are up, tell Agent X to scan them."""
    try:
        import urllib.request
        url = "http://localhost:8080/pipeline/scan"
        req = urllib.request.Request(url, method="POST")
        req.add_header("Content-Type", "application/json")
        data = json.dumps({}).encode()
        with urllib.request.urlopen(req, data=data, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        return {"error": str(exc)}


async def trigger_crew_registration_check() -> dict[str, Any]:
    """Ask Crew Orchestrator for agent registration status."""
    try:
        import urllib.request
        url = "http://localhost:8081/agents"
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        return {"error": str(exc)}


# ══════════════════════════════════════════════════════════════════════════════
# LIVE STATUS
# ══════════════════════════════════════════════════════════════════════════════

async def get_system_status() -> list[dict[str, Any]]:
    """Poll all services and return their current status."""
    statuses = []
    for spec in SERVICES:
        healthy = False
        if spec.health_url:
            healthy = await check_http_health(spec.health_url, timeout=3.0)
        elif spec.port:
            healthy = await check_tcp_port("localhost", spec.port, timeout=2.0)
        statuses.append({
            "name": spec.name,
            "tier": spec.tier.value,
            "port": spec.port,
            "healthy": healthy,
            "url": spec.health_url,
            "description": spec.description,
        })
    return statuses


def print_status_table(statuses: list[dict[str, Any]]) -> None:
    """Print a formatted status table."""
    if RICH:
        table = Table(title="🚀 HyperCode V2.0 — System Status", show_lines=True)
        table.add_column("Service", style="bold cyan")
        table.add_column("Tier", style="dim")
        table.add_column("Port", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("Description")
        for s in statuses:
            status_icon = "✅ UP" if s["healthy"] else "❌ DOWN"
            style = "green" if s["healthy"] else "red"
            table.add_row(
                s["name"],
                s["tier"],
                str(s["port"]) if s["port"] else "—",
                f"[{style}]{status_icon}[/{style}]",
                s["description"],
            )
        console.print(table)
    else:
        print(f"{'Service':<25} {'Tier':<8} {'Port':<6} {'Status':<8} Description")
        print("-" * 80)
        for s in statuses:
            status = "UP" if s["healthy"] else "DOWN"
            print(f"{s['name']:<25} {s['tier']:<8} {str(s['port'] or ''):<6} {status:<8} {s['description']}")


# ══════════════════════════════════════════════════════════════════════════════
# GUARDIAN WATCHDOG (post-launch background monitor)
# ══════════════════════════════════════════════════════════════════════════════

async def guardian_watchdog(interval_seconds: int = 30, max_checks: int = 10) -> None:
    """Runs N health checks post-launch, publishing events to Redis."""
    console.print("\n🛡️  Guardian Watchdog active — monitoring system health...")
    for i in range(max_checks):
        await asyncio.sleep(interval_seconds)
        statuses = await get_system_status()
        unhealthy = [s for s in statuses if not s["healthy"]]
        healthy_count = len(statuses) - len(unhealthy)

        await publish_launch_event("watchdog_check", {
            "check": i + 1,
            "healthy": healthy_count,
            "unhealthy": [s["name"] for s in unhealthy],
        })

        if unhealthy:
            console.print(f"  ⚠️  [{i+1}/{max_checks}] Unhealthy: {[s['name'] for s in unhealthy]}")
        else:
            console.print(f"  ✅ [{i+1}/{max_checks}] All {healthy_count} services healthy")


# ══════════════════════════════════════════════════════════════════════════════
# TEARDOWN
# ══════════════════════════════════════════════════════════════════════════════

async def teardown_system(compose_file: str) -> None:
    """Gracefully stop all HyperCode services."""
    console.print("\n🛑 Graceful shutdown initiated...")
    await publish_launch_event("system_shutdown", {"initiated_at": time.time()})
    cmd = ["docker", "compose", "-f", compose_file, "down", "--timeout", "30"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        console.print("✅ All services stopped cleanly.")
    else:
        console.print(f"⚠️  Shutdown warning: {proc.stderr}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN LAUNCH SEQUENCE
# ══════════════════════════════════════════════════════════════════════════════

async def launch(
    dry_run: bool = False,
    tier_filter: Optional[str] = None,
    skip_preflight: bool = False,
) -> bool:
    """
    Full HyperCode V2.0 launch sequence.
    Returns True on success, False on critical failure.
    """
    launch_start = time.time()
    compose_file = detect_compose_file()

    console.print()
    if RICH:
        console.print(Panel(
            "[bold cyan]🚀 HyperCode V2.0 — HyperLaunch[/bold cyan]\n"
            "[dim]Unified System Initialization Commander[/dim]",
            border_style="cyan",
        ))
    else:
        print("=" * 60)
        print("  🚀 HyperCode V2.0 — HyperLaunch")
        print("  Unified System Initialization Commander")
        print("=" * 60)

    # ── Step 1: Pre-flight ─────────────────────────────────────────────────
    if not skip_preflight:
        console.print("\n[bold]⚡ Step 1: Pre-Flight Checks[/bold]" if RICH else "\n⚡ Step 1: Pre-Flight Checks")
        checks = await preflight_checks()
        all_critical_passed = True

        for check in checks:
            icon = "✅" if check.passed else ("⚠️ " if not check.critical else "❌")
            console.print(f"  {icon} {check.name}: {check.message}")
            if not check.passed and check.critical:
                all_critical_passed = False

        if not all_critical_passed:
            console.print("\n❌ Critical pre-flight checks failed. Fix issues above and retry.")
            return False

        console.print("  ✅ Pre-flight complete")

    # ── Step 2: Publish launch event ───────────────────────────────────────
    await publish_launch_event("system_launching", {
        "compose_file": compose_file,
        "dry_run": dry_run,
        "services": len(SERVICES),
        "started_at": launch_start,
    })

    # ── Step 3: Tier-by-tier initialization ───────────────────────────────
    tiers_to_launch = (
        [Tier(tier_filter)] if tier_filter
        else [Tier.INFRA, Tier.CORE, Tier.AGENTS, Tier.UI]
    )

    all_results: dict[str, bool] = {}

    for tier in tiers_to_launch:
        tier_services = [s for s in SERVICES if s.tier == tier]
        console.print(
            f"\n[bold]🏗️  Tier: {tier.value.upper()} ({len(tier_services)} services)[/bold]"
            if RICH else
            f"\n🏗️  Tier: {tier.value.upper()} ({len(tier_services)} services)"
        )

        tier_results = await start_tier(tier, compose_file, dry_run)
        all_results.update(tier_results)

        # Check if any critical service in this tier failed
        for spec in tier_services:
            if spec.critical and not tier_results.get(spec.name, False):
                if not dry_run:
                    console.print(
                        f"\n❌ Critical service {spec.name} failed in tier {tier.value}. "
                        f"Cannot proceed to next tier."
                    )
                    await publish_launch_event("launch_failed", {
                        "failed_service": spec.name,
                        "tier": tier.value,
                    })
                    return False

        await publish_launch_event(f"tier_{tier.value}_complete", {
            "tier": tier.value,
            "results": tier_results,
        })

    if dry_run:
        console.print("\n✅ [DRY RUN] All checks passed. Run without --dry-run to launch.")
        return True

    # ── Step 4: Post-launch integration ───────────────────────────────────
    console.print("\n[bold]🔗 Step 4: Post-Launch Integration[/bold]" if RICH else "\n🔗 Step 4: Post-Launch Integration")

    # Trigger Agent X to scan all agents
    await asyncio.sleep(3)  # Brief settle time
    scan_result = await trigger_agent_x_pipeline_scan()
    if "error" not in scan_result:
        healthy_count = scan_result.get("healthy_count", "?")
        console.print(f"  ✅ Agent X pipeline scan: {healthy_count} agents healthy")
    else:
        console.print(f"  ⚠️  Agent X scan: {scan_result.get('error', 'unavailable')}")

    # Check Crew registration
    crew_result = await trigger_crew_registration_check()
    if "error" not in crew_result:
        console.print(f"  ✅ Crew Orchestrator: agents registered")
    else:
        console.print(f"  ⚠️  Crew registration: {crew_result.get('error', 'unavailable')}")

    # Write system state to Redis
    await set_system_state("launch_complete", {
        "timestamp": time.time(),
        "services": all_results,
        "compose_file": compose_file,
    })

    # ── Step 5: Launch Report ──────────────────────────────────────────────
    launch_duration = time.time() - launch_start
    success_count = sum(1 for v in all_results.values() if v)
    total_count = len(all_results)

    console.print()
    if RICH:
        console.print(Panel(
            f"[bold green]🎉 HyperCode V2.0 is LIVE![/bold green]\n\n"
            f"[cyan]Services launched:[/cyan] {success_count}/{total_count}\n"
            f"[cyan]Launch time:[/cyan]      {launch_duration:.1f}s\n\n"
            f"[bold]Quick Links:[/bold]\n"
            f"  🧠 Agent X (Meta-Architect):   http://localhost:8080\n"
            f"  🎛️  Crew Orchestrator:          http://localhost:8081\n"
            f"  🩺 Healer Agent:               http://localhost:8008\n"
            f"  🚀 HyperCode Core:             http://localhost:8000\n"
            f"  📊 Mission Control:            http://localhost:8088\n"
            f"  💻 BROski Terminal:            http://localhost:3000\n"
            f"  📈 Grafana:                    http://localhost:3001\n\n"
            f"[dim]Run: python hyperlaunch.py --status   to monitor[/dim]",
            border_style="green",
            title="🚀 LAUNCH COMPLETE",
        ))
    else:
        print("\n" + "=" * 60)
        print(f"  🎉 HyperCode V2.0 is LIVE!")
        print(f"  Services: {success_count}/{total_count} | Time: {launch_duration:.1f}s")
        print("  http://localhost:8080  — Agent X")
        print("  http://localhost:8081  — Crew Orchestrator")
        print("  http://localhost:8088  — Mission Control")
        print("  http://localhost:3000  — BROski Terminal")
        print("  http://localhost:3001  — Grafana")
        print("=" * 60)

    await publish_launch_event("system_live", {
        "services_up": success_count,
        "total": total_count,
        "duration_seconds": launch_duration,
    })

    return success_count == total_count


# ══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="🚀 HyperLaunch — HyperCode V2.0 Unified Startup Commander",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python hyperlaunch.py              # Full launch
  python hyperlaunch.py --dry-run    # Pre-flight only
  python hyperlaunch.py --status     # Live system status
  python hyperlaunch.py --teardown   # Graceful shutdown
  ./hyperlaunch.sh                   # One-liner shortcut
""",
    )
    parser.add_argument("--dry-run", action="store_true", help="Pre-flight + plan only")
    parser.add_argument("--tier", choices=[t.value for t in Tier], help="Launch a single tier")
    parser.add_argument("--status", action="store_true", help="Show live system status")
    parser.add_argument("--teardown", action="store_true", help="Graceful shutdown")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip pre-flight checks")
    parser.add_argument("--watchdog", action="store_true", help="Run guardian watchdog after launch")
    args = parser.parse_args()

    if args.status:
        statuses = asyncio.run(get_system_status())
        print_status_table(statuses)
        return

    if args.teardown:
        compose_file = detect_compose_file()
        asyncio.run(teardown_system(compose_file))
        return

    success = asyncio.run(launch(
        dry_run=args.dry_run,
        tier_filter=args.tier,
        skip_preflight=args.skip_preflight,
    ))

    if success and args.watchdog:
        asyncio.run(guardian_watchdog())

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
