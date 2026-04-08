import argparse
import asyncio
import time
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class BenchResult:
    requests: int
    concurrency: int
    duration_seconds: float
    rps: float
    p50_ms: float
    p90_ms: float
    p99_ms: float
    errors: int


def _percentile(values, p: float) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    k = (len(values_sorted) - 1) * p
    f = int(k)
    c = min(f + 1, len(values_sorted) - 1)
    if f == c:
        return float(values_sorted[f])
    d0 = values_sorted[f] * (c - k)
    d1 = values_sorted[c] * (k - f)
    return float(d0 + d1)


async def run_benchmark(
    base_url: str,
    api_key: str,
    requests: int,
    concurrency: int,
    timeout_seconds: float,
) -> BenchResult:
    latencies_ms = []
    errors = 0
    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        async def one() -> None:
            nonlocal errors
            async with sem:
                t0 = time.perf_counter()
                try:
                    r = await client.post(
                        f"{base_url}/execute/smoke",
                        headers={
                            "Content-Type": "application/json",
                            "X-API-Key": api_key,
                            "X-Smoke-Mode": "true",
                        },
                        json={"mode": "noop"},
                    )
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    if r.status_code != 200:
                        errors += 1
                        return
                    latencies_ms.append(latency_ms)
                except Exception:
                    errors += 1

        start = time.perf_counter()
        await asyncio.gather(*[one() for _ in range(requests)])
        duration = time.perf_counter() - start

    ok = len(latencies_ms)
    rps = (ok / duration) if duration > 0 else 0.0
    return BenchResult(
        requests=requests,
        concurrency=concurrency,
        duration_seconds=round(duration, 3),
        rps=round(rps, 2),
        p50_ms=round(_percentile(latencies_ms, 0.50), 2),
        p90_ms=round(_percentile(latencies_ms, 0.90), 2),
        p99_ms=round(_percentile(latencies_ms, 0.99), 2),
        errors=errors,
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8081")
    p.add_argument("--api-key", required=True)
    p.add_argument("--requests", type=int, default=2000)
    p.add_argument("--concurrency", type=int, default=100)
    p.add_argument("--timeout", type=float, default=5.0)
    args = p.parse_args()

    result = asyncio.run(
        run_benchmark(
            base_url=args.base_url,
            api_key=args.api_key,
            requests=args.requests,
            concurrency=args.concurrency,
            timeout_seconds=args.timeout,
        )
    )

    print(
        {
            "requests": result.requests,
            "concurrency": result.concurrency,
            "duration_seconds": result.duration_seconds,
            "rps": result.rps,
            "p50_ms": result.p50_ms,
            "p90_ms": result.p90_ms,
            "p99_ms": result.p99_ms,
            "errors": result.errors,
        }
    )
    return 0 if result.errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
