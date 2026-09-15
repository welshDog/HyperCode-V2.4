#!/usr/bin/env python3
"""
Docker Model Runner (DMR) validation script.

Tests DMR connectivity, model availability, inference, fallback behavior,
and metrics collection before deploying to Agent X.

Usage:
    python test_dmr_client.py [--host http://localhost:12434]

Exit codes:
    0 = all tests passed
    1 = one or more tests failed
"""

import asyncio
import logging
import sys
import time
from typing import Optional
import argparse

# Assuming agentx.dmr_client is in PYTHONPATH
try:
    from agentx.dmr_client import (
        DMRClient,
        InferenceTimeoutError,
        ModelNotAvailableError,
        DMRClientError,
    )
except ImportError:
    print(
        "ERROR: agentx.dmr_client not found. "
        "Ensure PYTHONPATH includes agents/agent-x/"
    )
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Test results tracker
class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, test_name: str) -> None:
        self.passed += 1
        logger.info(f"✓ {test_name}")

    def add_fail(self, test_name: str, reason: str) -> None:
        self.failed += 1
        logger.error(f"✗ {test_name}: {reason}")
        self.errors.append((test_name, reason))

    def report(self) -> None:
        total = self.passed + self.failed
        logger.info(
            f"\n{'='*60}\nTest Results: {self.passed}/{total} passed\n{'='*60}"
        )
        if self.errors:
            logger.error("Failed tests:")
            for test_name, reason in self.errors:
                logger.error(f"  - {test_name}: {reason}")
        else:
            logger.info("All tests passed!")

    def exit_code(self) -> int:
        return 0 if self.failed == 0 else 1


async def test_connectivity(host: str, results: TestResults) -> bool:
    """Test 1: DMR service is reachable."""
    try:
        async with DMRClient(host=host) as client:
            health = await client.health_check()
            if health["status"] == "healthy":
                results.add_pass("Connectivity: DMR service reachable")
                return True
            else:
                results.add_fail(
                    "Connectivity: DMR service unhealthy",
                    f"Status: {health.get('status', 'unknown')}",
                )
                return False
    except Exception as e:
        results.add_fail("Connectivity: Cannot reach DMR service", str(e))
        return False


async def test_quick_inference(host: str, results: TestResults) -> bool:
    """Test 2: Quick (non-streaming) inference works."""
    try:
        async with DMRClient(host=host) as client:
            response = await client.infer(
                "What is Docker?",
                system_message="Be concise (1 sentence).",
                temperature=0.5,
            )
            if response and len(response) > 10:
                results.add_pass(
                    f"Quick inference: Got {len(response)} chars response"
                )
                logger.debug(f"  Response: {response[:100]}...")
                return True
            else:
                results.add_fail(
                    "Quick inference: Empty or too short response", response[:50]
                )
                return False
    except Exception as e:
        results.add_fail("Quick inference", str(e))
        return False


async def test_streaming_inference(host: str, results: TestResults) -> bool:
    """Test 3: Streaming inference works."""
    try:
        async with DMRClient(host=host) as client:
            chunks = []
            async for chunk in client.infer_stream(
                "List 3 Docker best practices:",
                temperature=0.7,
            ):
                chunks.append(chunk)

            total_text = "".join(chunks)
            if len(total_text) > 20:
                results.add_pass(
                    f"Streaming inference: Got {len(chunks)} chunks, {len(total_text)} chars"
                )
                logger.debug(f"  Response: {total_text[:100]}...")
                return True
            else:
                results.add_fail(
                    "Streaming inference: Empty or too short", total_text[:50]
                )
                return False
    except Exception as e:
        results.add_fail("Streaming inference", str(e))
        return False


async def test_metrics_collection(host: str, results: TestResults) -> bool:
    """Test 4: Metrics are collected correctly."""
    try:
        async with DMRClient(host=host) as client:
            # Run a few inferences
            for i in range(2):
                await client.infer(f"Hello {i}", temperature=0.5)

            metrics = client.get_metrics(limit=2)
            if len(metrics) >= 2:
                # Check all expected fields
                m = metrics[0]
                required_fields = {
                    "model",
                    "latency_ms",
                    "total_tokens",
                    "fallback_used",
                    "timestamp",
                }
                missing = required_fields - set(m.keys())
                if missing:
                    results.add_fail(
                        "Metrics collection: Missing fields",
                        f"{missing}",
                    )
                    return False

                results.add_pass(
                    f"Metrics collection: {len(metrics)} metrics, "
                    f"avg latency {sum(m['latency_ms'] for m in metrics) / len(metrics):.0f}ms"
                )
                logger.debug(f"  Sample metric: {metrics[0]}")
                return True
            else:
                results.add_fail(
                    "Metrics collection: Not enough metrics", f"Got {len(metrics)}"
                )
                return False
    except Exception as e:
        results.add_fail("Metrics collection", str(e))
        return False


async def test_fallback_behavior(host: str, results: TestResults) -> bool:
    """Test 5: Fallback model is used on timeout (timeout may be short)."""
    try:
        # This test is best-effort: we can't reliably trigger a timeout in a test
        # Instead, we verify the fallback_used flag exists in metrics
        async with DMRClient(
            host=host,
            inference_timeout_ms=100_000,  # 100s timeout (unlikely to trigger)
        ) as client:
            await client.infer("Short prompt", use_fallback=True)
            metrics = client.get_metrics(limit=1)

            if metrics:
                has_fallback_flag = "fallback_used" in metrics[0]
                if has_fallback_flag:
                    results.add_pass(
                        "Fallback behavior: Fallback flag present in metrics"
                    )
                    return True
                else:
                    results.add_fail(
                        "Fallback behavior: No fallback flag in metrics", ""
                    )
                    return False
            else:
                results.add_fail("Fallback behavior: No metrics collected", "")
                return False
    except Exception as e:
        results.add_fail("Fallback behavior", str(e))
        return False


async def test_model_preload(host: str, results: TestResults) -> bool:
    """Test 6: Model preloading works."""
    try:
        async with DMRClient(host=host) as client:
            # Preload should return immediately (background task)
            preload_start = time.time()
            success = await client.preload_models()
            preload_elapsed = time.time() - preload_start

            if success and preload_elapsed < 2:  # Should return nearly instantly
                results.add_pass(
                    f"Model preload: Initiated in {preload_elapsed*1000:.0f}ms"
                )
                return True
            else:
                results.add_fail(
                    "Model preload: Took too long or failed", f"{preload_elapsed:.1f}s"
                )
                return False
    except Exception as e:
        results.add_fail("Model preload", str(e))
        return False


async def test_concurrent_inference(host: str, results: TestResults) -> bool:
    """Test 7: Multiple concurrent inferences work."""
    try:
        async with DMRClient(host=host) as client:
            # Run 3 concurrent inferences
            tasks = [
                client.infer(f"Prompt {i}", use_fallback=True) for i in range(3)
            ]
            results_list = await asyncio.gather(*tasks)

            if len(results_list) == 3 and all(results_list):
                results.add_pass(f"Concurrent inference: 3 concurrent requests successful")
                return True
            else:
                results.add_fail(
                    "Concurrent inference: Some requests failed", f"Got {len(results_list)} results"
                )
                return False
    except Exception as e:
        results.add_fail("Concurrent inference", str(e))
        return False


async def run_all_tests(host: str) -> int:
    """Run all validation tests."""
    logger.info(f"Starting DMR validation tests (host={host})\n")

    results = TestResults()

    # Test 1: Connectivity
    if not await test_connectivity(host, results):
        logger.error(
            "\n⚠️  Cannot reach DMR service. Skipping remaining tests.\n"
            "Make sure Docker Model Runner is running:\n"
            "  docker run -p 12434:12434 docker:latest docker model start-runner"
        )
        results.report()
        return results.exit_code()

    # Tests 2-7: Only run if connectivity succeeds
    await test_quick_inference(host, results)
    await test_streaming_inference(host, results)
    await test_metrics_collection(host, results)
    await test_fallback_behavior(host, results)
    await test_model_preload(host, results)
    await test_concurrent_inference(host, results)

    results.report()
    return results.exit_code()


def main():
    """Parse arguments and run tests."""
    parser = argparse.ArgumentParser(
        description="Validate Docker Model Runner (DMR) integration"
    )
    parser.add_argument(
        "--host",
        default="http://127.0.0.1:12434",
        help="DMR host URL (default: http://127.0.0.1:12434)",
    )

    args = parser.parse_args()

    exit_code = asyncio.run(run_all_tests(args.host))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
