from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path

from .config import SmokeRunConfig
from .reporting import write_junit_report, write_json_report, write_markdown_report
from .runner import SmokeProgressEvent, SmokeSuiteRunner


def _configure_logging(json_logs: bool) -> None:
    level = os.getenv("SMOKE_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level)
    if json_logs:
        root = logging.getLogger()
        for handler in root.handlers:
            handler.setFormatter(logging.Formatter("%(message)s"))


async def _consume_progress(
    queue: asyncio.Queue[SmokeProgressEvent], json_progress: bool
) -> None:
    while True:
        ev = await queue.get()
        if ev.status == "__done__":
            return
        if json_progress:
            print(
                json.dumps(
                    {"check": ev.check, "status": ev.status, "detail": ev.detail}
                )
            )
        else:
            suffix = f" ({ev.detail})" if ev.detail else ""
            print(f"{ev.check}: {ev.status}{suffix}")


async def main_async() -> int:
    parser = argparse.ArgumentParser(
        description="HyperCode Smoke Test Execution Framework"
    )
    parser.add_argument(
        "--env",
        choices=["dev", "staging", "production"],
        default=os.getenv("SMOKE_ENV", "dev"),
    )
    parser.add_argument(
        "--orchestrator-url",
        default=os.getenv("SMOKE_ORCHESTRATOR_URL", "http://127.0.0.1:8081"),
    )
    parser.add_argument(
        "--core-url", default=os.getenv("SMOKE_CORE_URL", "http://127.0.0.1:8000")
    )
    parser.add_argument(
        "--dashboard-url",
        default=os.getenv("SMOKE_DASHBOARD_URL", "http://127.0.0.1:8088"),
    )
    parser.add_argument(
        "--healer-url", default=os.getenv("SMOKE_HEALER_URL", "http://127.0.0.1:8010")
    )
    parser.add_argument(
        "--smoke-api-key",
        default=os.getenv("SMOKE_API_KEY", ""),
        help="Benchmark API key (never logged)",
    )
    parser.add_argument(
        "--timeout", type=float, default=float(os.getenv("SMOKE_TIMEOUT", "5.0"))
    )
    parser.add_argument(
        "--retries", type=int, default=int(os.getenv("SMOKE_RETRIES", "2"))
    )
    parser.add_argument(
        "--concurrency", type=int, default=int(os.getenv("SMOKE_CONCURRENCY", "16"))
    )
    parser.add_argument("--redis-url", default=os.getenv("SMOKE_REDIS_URL", ""))
    parser.add_argument("--verify-no-redis-writes", action="store_true")
    parser.add_argument("--skip-task-history-check", action="store_true")
    parser.add_argument(
        "--out-dir", default=os.getenv("SMOKE_OUT_DIR", "artifacts/smoke")
    )
    parser.add_argument("--json-progress", action="store_true")
    parser.add_argument("--json-logs", action="store_true")
    args = parser.parse_args()

    _configure_logging(json_logs=args.json_logs)

    config = SmokeRunConfig(
        env=args.env,
        orchestrator_url=args.orchestrator_url,
        core_url=args.core_url,
        dashboard_url=args.dashboard_url or None,
        healer_url=args.healer_url or None,
        redis_url=args.redis_url or None,
        smoke_api_key=args.smoke_api_key,
        timeout_seconds=args.timeout,
        retries=args.retries,
        concurrency=args.concurrency,
        verify_no_task_history_pollution=not args.skip_task_history_check,
        verify_no_redis_writes=bool(args.verify_no_redis_writes),
        output_dir=Path(args.out_dir),
    )

    progress_queue: asyncio.Queue[SmokeProgressEvent] = asyncio.Queue()
    consumer = asyncio.create_task(
        _consume_progress(progress_queue, json_progress=args.json_progress)
    )

    runner = SmokeSuiteRunner(config)
    report = await runner.run(progress_queue=progress_queue)
    await progress_queue.put(SmokeProgressEvent(check="suite", status="__done__"))
    await consumer

    output_dir = config.safe_output_dir()
    stem = f"smoke_{config.env}"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"
    junit_path = output_dir / f"{stem}.junit.xml"

    if config.write_json:
        write_json_report(report, json_path)
    if config.write_markdown:
        write_markdown_report(report, md_path)
    if config.write_junit:
        write_junit_report(report, junit_path)

    return 0 if report.ok else 1


def main() -> None:
    raise SystemExit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
