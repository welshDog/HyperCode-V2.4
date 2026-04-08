from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Dict, Optional

import httpx

from .config import SmokeRunConfig
from .reporting import CheckResult, SmokeSuiteReport, utc_now_iso


logger = logging.getLogger("smoke-framework")


@dataclass(frozen=True)
class SmokeProgressEvent:
    check: str
    status: str
    detail: str = ""


class SmokeSuiteRunner:
    def __init__(self, config: SmokeRunConfig):
        self.config = config
        self._semaphore = asyncio.Semaphore(config.concurrency)
        self._orchestrator_base = str(config.orchestrator_url).rstrip("/")
        self._core_base = str(config.core_url).rstrip("/")
        self._healer_base = str(config.healer_url).rstrip("/") if config.healer_url else None
        self._dashboard_base = (
            str(config.dashboard_url).rstrip("/") if config.dashboard_url else None
        )

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> tuple[int, str, float]:
        async with self._semaphore:
            attempt = 0
            last_exc: Optional[Exception] = None
            while attempt <= self.config.retries:
                attempt += 1
                t0 = perf_counter()
                try:
                    async with httpx.AsyncClient(
                        timeout=self.config.timeout_seconds
                    ) as client:
                        resp = await client.request(
                            method, url, headers=headers, json=json_body
                        )
                    latency_ms = (perf_counter() - t0) * 1000.0
                    return resp.status_code, resp.text, latency_ms
                except Exception as e:
                    last_exc = e
                    latency_ms = (perf_counter() - t0) * 1000.0
                    logger.warning(
                        "request_failed",
                        extra={
                            "method": method,
                            "url": url,
                            "attempt": attempt,
                            "latency_ms": round(latency_ms, 2),
                            "error": type(e).__name__,
                        },
                    )
                    if attempt > self.config.retries:
                        break
                    await asyncio.sleep(self.config.retry_backoff_seconds * attempt)
            raise last_exc or RuntimeError("request failed")

    def _smoke_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.config.smoke_mode_header_required:
            headers["X-Smoke-Mode"] = "true"
        if self.config.smoke_api_key:
            headers["X-API-Key"] = self.config.smoke_api_key
        return headers

    async def _tasks_count(self) -> Optional[int]:
        url = f"{self._orchestrator_base}/tasks"
        try:
            status, body, _ = await self._request(
                "GET", str(url), headers=self._smoke_headers()
            )
            if status != 200:
                return None
            data = httpx.Response(status_code=200, content=body).json()
            if isinstance(data, list):
                return len(data)
            return None
        except Exception:
            return None

    async def _redis_snapshot(self) -> Optional[Dict[str, int]]:
        if not self.config.redis_url:
            return None
        try:
            import redis.asyncio as redis  # type: ignore

            client = redis.from_url(self.config.redis_url)
            try:
                task_keys = 0
                async for _ in client.scan_iter(match="task:*", count=200):
                    task_keys += 1
                    if task_keys > 2000:
                        break
                tasks_history_len = await client.llen("tasks:history")
                return {"task_keys": task_keys, "tasks_history_len": int(tasks_history_len)}
            finally:
                await client.aclose()
        except Exception:
            return None

    async def run(
        self, progress_queue: Optional[asyncio.Queue[SmokeProgressEvent]] = None
    ) -> SmokeSuiteReport:
        started_at = utc_now_iso()
        t0 = perf_counter()

        async def emit(check: str, status: str, detail: str = "") -> None:
            if progress_queue is not None:
                await progress_queue.put(
                    SmokeProgressEvent(check=check, status=status, detail=detail)
                )

        results: list[CheckResult] = []

        async def check_health(name: str, url: str) -> None:
            await emit(name, "running")
            try:
                status, body, latency_ms = await self._request("GET", url)
                passed = status == 200
                results.append(
                    CheckResult(
                        name=name,
                        passed=passed,
                        latency_ms=round(latency_ms, 2),
                        status_code=status,
                        detail=None if passed else body[:500],
                    )
                )
                await emit(name, "passed" if passed else "failed")
            except Exception as e:
                results.append(
                    CheckResult(name=name, passed=False, detail=f"{type(e).__name__}")
                )
                await emit(name, "failed", type(e).__name__)

        orchestrator_health = f"{self._orchestrator_base}/health"
        core_health = f"{self._core_base}/health"

        checks = [
            check_health("core_health", str(core_health)),
            check_health("orchestrator_health", str(orchestrator_health)),
        ]

        if self._healer_base:
            checks.append(check_health("healer_health", f"{self._healer_base}/health"))
        if self._dashboard_base:
            checks.append(check_health("dashboard_http", str(self._dashboard_base)))

        await asyncio.gather(*checks)

        tasks_before = (
            await self._tasks_count()
            if self.config.verify_no_task_history_pollution
            else None
        )
        redis_before = await self._redis_snapshot() if self.config.verify_no_redis_writes else None

        await emit("execute_smoke_noop", "running")
        try:
            smoke_url = f"{self._orchestrator_base}/execute/smoke"
            status, body, latency_ms = await self._request(
                "POST",
                str(smoke_url),
                headers=self._smoke_headers(),
                json_body={"mode": "noop"},
            )
            passed = status == 200
            results.append(
                CheckResult(
                    name="execute_smoke_noop",
                    passed=passed,
                    latency_ms=round(latency_ms, 2),
                    status_code=status,
                    detail=None if passed else body[:500],
                )
            )
            await emit("execute_smoke_noop", "passed" if passed else "failed")
        except Exception as e:
            results.append(
                CheckResult(
                    name="execute_smoke_noop",
                    passed=False,
                    detail=f"{type(e).__name__}",
                )
            )
            await emit("execute_smoke_noop", "failed", type(e).__name__)

        if self.config.verify_no_task_history_pollution:
            await emit("no_task_history_pollution", "running")
            tasks_after = await self._tasks_count()
            passed = (
                tasks_before is not None
                and tasks_after is not None
                and tasks_before == tasks_after
            )
            results.append(
                CheckResult(
                    name="no_task_history_pollution",
                    passed=passed,
                    detail=None if passed else f"tasks_before={tasks_before} tasks_after={tasks_after}",
                    meta={"tasks_before": tasks_before, "tasks_after": tasks_after},
                )
            )
            await emit("no_task_history_pollution", "passed" if passed else "failed")

        if self.config.verify_no_redis_writes:
            await emit("no_redis_writes", "running")
            redis_after = await self._redis_snapshot()
            passed = redis_before is not None and redis_after is not None and redis_before == redis_after
            results.append(
                CheckResult(
                    name="no_redis_writes",
                    passed=passed,
                    detail=None if passed else f"redis_before={redis_before} redis_after={redis_after}",
                    meta={"redis_before": redis_before, "redis_after": redis_after},
                )
            )
            await emit("no_redis_writes", "passed" if passed else "failed")

        finished_at = utc_now_iso()
        duration_ms = (perf_counter() - t0) * 1000.0
        return SmokeSuiteReport(
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=round(duration_ms, 2),
            environment=self.config.env,
            results=results,
        )
