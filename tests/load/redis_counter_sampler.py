import argparse
import asyncio
import json
import time
from datetime import datetime, timezone

import redis.asyncio as redis


async def sample(redis_url: str, interval: float, duration_seconds: int, out_path: str) -> int:
    client = redis.from_url(redis_url, decode_responses=True)
    samples = []
    end = time.monotonic() + duration_seconds

    try:
        while time.monotonic() < end:
            ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            tasks_history_len = int(await client.llen("tasks:history"))
            logs_len = int(await client.llen("logs:global"))
            samples.append(
                {
                    "ts": ts,
                    "tasks_history_len": tasks_history_len,
                    "logs_global_len": logs_len,
                }
            )
            await asyncio.sleep(interval)
    finally:
        await client.aclose()

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2)

    if not samples:
        return 1

    delta = samples[-1]["tasks_history_len"] - samples[0]["tasks_history_len"]
    return 0 if delta == 0 else 2


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--redis-url", default="redis://127.0.0.1:6379")
    p.add_argument("--interval", type=float, default=2.0)
    p.add_argument("--duration", type=int, default=120)
    p.add_argument("--out", default="artifacts/load/redis_samples.json")
    args = p.parse_args()

    return asyncio.run(sample(args.redis_url, args.interval, args.duration, args.out))


if __name__ == "__main__":
    raise SystemExit(main())
