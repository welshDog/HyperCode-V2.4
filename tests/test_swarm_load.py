#!/usr/bin/env python3
# ════════════════════════════════════════════════════════════════════════════════
# tests/test_swarm_load.py — LOAD TEST 25-AGENT SWARM
# Usage: pytest test_swarm_load.py -v --duration=300
# Created: May 21, 2026
# ════════════════════════════════════════════════════════════════════════════════

import asyncio
import time
import pytest
import httpx
from typing import List
import statistics

# Configuration
ORCHESTRATOR_URL = "http://localhost:8081"
CORE_URL = "http://localhost:8000"
NUM_TASKS = 500
CONCURRENT_TASKS = 50
TASK_TIMEOUT = 30

@pytest.mark.asyncio
async def test_swarm_formation():
    """Test all 25 agents can form swarm"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ORCHESTRATOR_URL}/swarm/form",
            json={"num_agents": 25, "timeout": 60},
            headers={"X-API-Key": "dev"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["agents_formed"] == 25


@pytest.mark.asyncio
async def test_concurrent_task_dispatch(num_tasks: int = 500):
    """Load test: dispatch 500 concurrent tasks to 25 agents"""
    
    async def dispatch_task(client: httpx.AsyncClient, task_id: int):
        """Dispatch a single task"""
        start = time.time()
        try:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/execute",
                json={
                    "task_id": f"load_test_{task_id}",
                    "task": f"Process data batch {task_id}",
                    "timeout": TASK_TIMEOUT
                },
                headers={"X-API-Key": "dev"},
                timeout=TASK_TIMEOUT + 5
            )
            duration = time.time() - start
            return {
                "task_id": task_id,
                "status": "success" if response.status_code == 200 else "failed",
                "duration": duration,
                "status_code": response.status_code
            }
        except asyncio.TimeoutError:
            return {"task_id": task_id, "status": "timeout", "duration": TASK_TIMEOUT + 5}
        except Exception as e:
            return {"task_id": task_id, "status": "error", "error": str(e)}

    async with httpx.AsyncClient() as client:
        # Dispatch in batches
        all_results = []
        for batch_start in range(0, num_tasks, CONCURRENT_TASKS):
            batch_end = min(batch_start + CONCURRENT_TASKS, num_tasks)
            tasks = [
                dispatch_task(client, i)
                for i in range(batch_start, batch_end)
            ]
            batch_results = await asyncio.gather(*tasks)
            all_results.extend(batch_results)
            
            # Progress
            print(f"Completed batch {batch_end}/{num_tasks}")

    # Analyze results
    successful = [r for r in all_results if r["status"] == "success"]
    failed = [r for r in all_results if r["status"] != "success"]
    durations = [r["duration"] for r in successful if "duration" in r]

    success_rate = len(successful) / len(all_results) * 100
    avg_duration = statistics.mean(durations) if durations else 0
    p95_duration = sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 20 else 0
    p99_duration = sorted(durations)[int(len(durations) * 0.99)] if len(durations) > 100 else 0

    print(f"""
    LOAD TEST RESULTS
    ═════════════════════════════════════════════
    Total tasks:        {len(all_results)}
    Successful:         {len(successful)} ({success_rate:.1f}%)
    Failed:             {len(failed)}
    
    Response times:
    - Average:          {avg_duration:.2f}s
    - P95:              {p95_duration:.2f}s
    - P99:              {p99_duration:.2f}s
    
    Throughput:         {len(successful) / sum(durations) * 100:.1f} tasks/sec
    """)

    # Assert success rate > 95%
    assert success_rate >= 95, f"Success rate {success_rate}% below 95% threshold"


@pytest.mark.asyncio
async def test_agent_health_under_load():
    """Monitor agent health during load test"""
    async with httpx.AsyncClient() as client:
        # Get baseline health
        health_checks = [
            ("crew-orchestrator", 8081),
            ("agent-x", 8083),
            ("brain-agent", 8082),
            ("coder-agent", 8002),
            ("tips-tricks-writer", 8011),
        ]

        print("\nBaseline Health Check:")
        baseline = {}
        for name, port in health_checks:
            response = await client.get(f"http://localhost:{port}/health", timeout=5)
            baseline[name] = response.json()
            print(f"  {name}: {response.json()['status']}")

        # Run load test
        print("\nRunning load test...")
        await test_concurrent_task_dispatch(num_tasks=100)

        # Check health again
        print("\nPost-Load Health Check:")
        for name, port in health_checks:
            response = await client.get(f"http://localhost:{port}/health", timeout=5)
            health = response.json()
            status = "✅" if health["status"] == "healthy" else "⚠️"
            print(f"  {status} {name}: {health['status']}")
            assert health["status"] == "healthy", f"{name} unhealthy after load test"


@pytest.mark.asyncio
async def test_agent_memory_under_load():
    """Check memory usage doesn't spike dangerously"""
    import docker
    
    client_docker = docker.from_env()
    
    # Get baseline memory
    print("\nBaseline Memory Usage:")
    baseline_mem = {}
    for container in client_docker.containers.list(filters={"label": "com.hypercode.tier"}):
        stats = container.stats(stream=False)
        mem_bytes = stats["memory_stats"]["usage"]
        mem_mb = mem_bytes / 1024 / 1024
        baseline_mem[container.name] = mem_mb
        print(f"  {container.name}: {mem_mb:.1f}MB")

    # Run load test
    print("\nRunning memory load test...")
    await test_concurrent_task_dispatch(num_tasks=200)

    # Check memory again
    print("\nPost-Load Memory Usage:")
    spike_alerts = []
    for container in client_docker.containers.list(filters={"label": "com.hypercode.tier"}):
        stats = container.stats(stream=False)
        mem_bytes = stats["memory_stats"]["usage"]
        mem_mb = mem_bytes / 1024 / 1024
        baseline = baseline_mem.get(container.name, 0)
        spike_pct = ((mem_mb - baseline) / baseline * 100) if baseline > 0 else 0
        
        status = "✅" if spike_pct < 50 else "⚠️"
        print(f"  {status} {container.name}: {mem_mb:.1f}MB (baseline {baseline:.1f}MB, +{spike_pct:.1f}%)")
        
        if spike_pct > 100:
            spike_alerts.append(f"{container.name} spiked {spike_pct:.1f}%")

    assert len(spike_alerts) == 0, f"Memory spikes detected: {spike_alerts}"


@pytest.mark.asyncio
async def test_agent_error_recovery():
    """Test agents recover from errors gracefully"""
    async with httpx.AsyncClient() as client:
        # Send invalid tasks
        invalid_tasks = [
            {"task": ""},  # Empty task
            {"task": None},  # None task
            {"task": "x" * 10000},  # Extremely long task
        ]

        for task in invalid_tasks:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/execute",
                json=task,
                headers={"X-API-Key": "dev"},
                timeout=10
            )
            # Should return 400/422, not 500
            assert response.status_code in [400, 422], \
                f"Invalid task should return 4xx, got {response.status_code}"

        # Verify orchestrator is still healthy
        response = await client.get(f"{ORCHESTRATOR_URL}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


if __name__ == "__main__":
    asyncio.run(test_concurrent_task_dispatch(500))
