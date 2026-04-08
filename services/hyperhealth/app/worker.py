# Worker skeleton — runs checks async
import asyncio
from datetime import datetime, timedelta

async def execute_check(check_def):
    print(f"Running check: {check_def['name']}")
    await asyncio.sleep(0.1)  # simulate work
    return {"status": "OK", "latency_ms": 25.0}

async def scheduler():
    # TODO: load from DB
    sample_checks = [
        {"name": "http_core", "interval_seconds": 15},
        {"name": "db_postgres", "interval_seconds": 30}
    ]
    
    print("🧠 HyperHealth Worker starting...")
    while True:
        now = datetime.utcnow()
        tasks = []
        for c in sample_checks:
            tasks.append(asyncio.create_task(execute_check(c)))
        if tasks:
            results = await asyncio.gather(*tasks)
            print(f"✅ Completed {len(results)} checks")
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(scheduler())
