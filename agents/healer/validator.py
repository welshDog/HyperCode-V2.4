"""
Healer Agent Mission: Health Check Validator (Local Mode)
Systematically verifies all documented health checks in the HyperCode ecosystem.
Supports both internal Docker networking and localhost for dev.
"""
from __future__ import annotations

import asyncio
import logging
import os
import socket
from datetime import datetime, timezone

import httpx
import redis.asyncio as aioredis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("healer.validator")

_Target = dict[str, str]
_Result = dict[str, object]


class HealthCheckValidator:
    """Validates all HyperCode service health endpoints and generates a report."""

    redis_url: str
    redis: aioredis.Redis | None
    results: list[_Result]
    _boot_time: datetime

    def __init__(self, redis_url: str = "redis://localhost:6379") -> None:
        """Initialise validator with an optional Redis URL."""
        self.redis_url = redis_url
        self.redis = None
        self.results: list[_Result] = []
        self._boot_time = datetime.now(timezone.utc)

    async def initialize(self) -> None:
        """Connect to Redis; falls back to limited mode if unavailable."""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url, decode_responses=True
            )
            if self.redis is not None:
                _ = await self.redis.ping()
            logger.info("Validator connected to Redis. BRO, let's go! 🚀")
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Could not connect to Redis at %s. Using limited mode. %s",
                self.redis_url, e,
            )
            self.redis = None

    async def run_mission(self) -> None:
        """
        Main mission loop.

        1. Identify targets (from docs/guides)
        2. Execute health checks (Normal, Edge, Failure)
        3. Benchmark performance
        4. Generate report
        """
        logger.info("🎯 Starting Mission: HYPERCODE_HEALTH_CHECK_VALIDATION_001")

        targets: list[_Target] = [
            {"name": "super-hyper-broski-agent", "url": "http://localhost:8015/health", "type": "Agent"},
            {"name": "throttle-agent",           "url": "http://localhost:8014/health", "type": "Agent"},
            {"name": "test-agent",               "url": "http://localhost:8013/health", "type": "Agent"},
            {"name": "healer-agent",             "url": "http://localhost:8010/health", "type": "Healer"},
            {"name": "backend-specialist",       "url": "http://localhost:8003/health", "type": "Specialist"},
            {"name": "crew-orchestrator",        "url": "http://localhost:8081/health", "type": "Orchestrator"},
            {"name": "openshell-cluster",        "url": "http://localhost:8080/health", "type": "Cluster"},
            {"name": "tips-tricks-writer",       "url": "http://localhost:8011/health", "type": "Agent"},
        ]

        for target in targets:
            logger.info("Checking %s...", target["name"])
            result = await self.validate_target(target)
            self.results.append(result)

        await self.generate_report()

    async def validate_target(self, target: _Target) -> _Result:
        """Validate a single target with timing and status checks."""
        _start_time = datetime.now(timezone.utc)
        status = "FAIL"
        details = ""
        latency: float = 0.0

        try:
            if target["type"] in {"FastAPI", "Agent", "Orchestrator", "Healer", "Specialist", "Cluster"}:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    t0 = datetime.now(timezone.utc)
                    r: httpx.Response = await client.get(target["url"])
                    t1 = datetime.now(timezone.utc)
                    latency = (t1 - t0).total_seconds() * 1000
                    if r.status_code == 200:
                        status = "PASS"
                        details = "Healthy response"
                    else:
                        details = f"Status code: {r.status_code}"

            elif target["type"] == "Redis":
                if self.redis is not None:
                    t0 = datetime.now(timezone.utc)
                    raw_ping = await self.redis.ping()
                    ping: bool = bool(raw_ping)
                    t1 = datetime.now(timezone.utc)
                    latency = (t1 - t0).total_seconds() * 1000
                    if ping:
                        status = "PASS"
                        details = "Redis PONG successful"
                    else:
                        details = "Redis did not respond"
                else:
                    details = "Redis client not initialized"

            elif target["type"] == "Postgres":
                t0 = datetime.now(timezone.utc)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                tcp_result: int = sock.connect_ex(("localhost", 5432))
                t1 = datetime.now(timezone.utc)
                latency = (t1 - t0).total_seconds() * 1000
                if tcp_result == 0:
                    status = "PASS"
                    details = "Postgres TCP port open"
                else:
                    details = f"Port 5432 closed or unreachable (Error {tcp_result})"
                sock.close()

        except Exception as e:  # noqa: BLE001
            details = f"Unreachable: {type(e).__name__}"
            logger.error("Validation failed for %s: %s", target["name"], e)

        return {
            "target": target["name"],
            "type": target["type"],
            "status": status,
            "latency_ms": latency,
            "details": details,
            "indicator": "🟢" if status == "PASS" else "🔴",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def generate_report(self) -> None:
        """Generate a neurodivergent-friendly markdown report."""
        report_path = "docs/reports/HEALTH_CHECK_VALIDATION_REPORT.md"
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        passed = [r for r in self.results if r["status"] == "PASS"]
        failed = [r for r in self.results if r["status"] == "FAIL"]
        overall = "🟢 HEALTHY" if len(failed) == 0 else "🟡 DEGRADED"

        rows: list[str] = []
        for r in self.results:
            lms = r["latency_ms"]
            latency_str = (
                f"{float(str(lms)):.2f}ms"
                if isinstance(lms, (int, float)) and float(str(lms)) > 0
                else "N/A"
            )
            rows.append(
                f"| {r['indicator']} {r['target']} | **{r['status']}** | {latency_str} | {r['details']} |"
            )

        table = "\n".join(rows)

        content = (
            f"# 🛡️ Health Check Validation Report\n"
            f"**Mission ID**: HYPERCODE_HEALTH_CHECK_VALIDATION_001\n"
            f"**Date**: {now_str}\n"
            f"**Status**: {overall}\n\n---\n\n"
            f"## 🟢 1. Summary (Low Complexity)\n"
            f"Bro, we just swept the entire infrastructure to make sure our new "
            f"**Tips Architect** guides match reality.\n\n"
            f"- **Targets Scanned**: {len(self.results)}\n"
            f"- **Passed**: {len(passed)}\n"
            f"- **Failed**: {len(failed)}\n\n---\n\n"
            f"## 🟡 2. Detailed Results (Medium Complexity)\n\n"
            f"| Target | Status | Latency (ms) | Details |\n"
            f"| :--- | :--- | :--- | :--- |\n"
            f"{table}\n\n---\n\n"
            f"## 🔴 3. Discrepancies & Recommendations (High Complexity)\n"
            f"**Edge Case Analysis**:\n"
            f"- **Latency Spikes**: Any target over 200ms needs optimization (see TIPS_04).\n"
            f"- **Zombie Risk**: If status is PASS but latency is high, the agent might be struggling.\n\n"
            f"**Recommendations**:\n"
            f"1. **Optimize Healer**: If the Healer itself is slow, it might miss alerts.\n"
            f"2. **Update Docs**: If any endpoint returned a structure different from our guides, "
            f"update the TIPS_XX files immediately.\n\n---\n\n"
            f"**Mission Complete, Bro. 🚀**\n"
        )

        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            _ = f.write(content)

        logger.info("Report generated at %s", report_path)


async def main() -> None:
    """Entry point — run the health check mission."""
    validator = HealthCheckValidator()
    await validator.initialize()
    await validator.run_mission()


if __name__ == "__main__":
    asyncio.run(main())
