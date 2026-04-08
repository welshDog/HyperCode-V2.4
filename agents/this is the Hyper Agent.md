🧠 HyperCode Multi-Agent Communication Guide
Based on the Hyper Agent Bible and your existing infrastructure, here's exactly how to wire everything up.
​

🗺️ The Big Picture — How It All Connects
Your agents communicate through 3 layers that are already in your stack:

Layer	Tech	Purpose
Commands	Redis Pub/Sub + approval_requests channel	Agent → Agent task delegation
Shared Memory	Redis key-value (context.* keys)	Shared knowledge store
Events/Progress	SSE stream (/agents/stream)	Real-time timeline broadcasting
⚡ Step 1 — Shared Memory (Redis Context Store)
This is how agents share knowledge without re-doing work. Every agent reads/writes to Redis using structured dot-notation keys.
​

Add this context_manager.py to each agent's codebase:

python
# agents/shared/context_manager.py
import redis.asyncio as redis
import json
from datetime import datetime

redis_client = None

async def init_redis(url: str = "redis://redis:6379"):
    global redis_client
    redis_client = await redis.from_url(url, decode_responses=True)

async def write_context(key: str, data: dict, agent_name: str):
    """Save knowledge to shared store. Key format: domain.subdomain.detail"""
    payload = {
        "created_at": datetime.now().isoformat(),
        "created_by": agent_name,
        "version": 1,
        "data": data,
        "metadata": {"confidence": "high"}
    }
    await redis_client.set(f"context:{key}", json.dumps(payload), ex=3600)

async def read_context(key: str) -> dict:
    """Read shared knowledge from store."""
    raw = await redis_client.get(f"context:{key}")
    return json.loads(raw)["data"] if raw else {}

async def list_contexts(pattern: str = "*") -> list:
    """Discover what knowledge already exists."""
    keys = await redis_client.keys(f"context:{pattern}")
    return [k.replace("context:", "") for k in keys]
Example usage between agents:

python
# backend_specialist writes after investigation
await write_context("api.routes.structure", {
    "endpoints": ["/execute", "/agents", "/health"],
    "auth_required": True
}, agent_name="backend_specialist")

# security_specialist reads it — no duplication!
routes = await read_context("api.routes.structure")
📡 Step 2 — Inter-Agent Messaging (Redis Pub/Sub)
Agents talk to each other by publishing tasks to Redis channels. Your crew-orchestrator/main.py already has the approval_requests channel — extend it:
​

python
# agents/shared/messenger.py
import redis.asyncio as redis
import json
from datetime import datetime
import asyncio

TASK_CHANNEL = "agent:tasks"
RESULT_CHANNEL = "agent:results"
ALERT_CHANNEL = "approval_requests"  # Already wired to dashboard!

async def delegate_task(
    redis_client,
    from_agent: str,
    to_agent: str,
    task_id: str,
    task_description: str,
    context_keys: list = [],
    requires_approval: bool = False
):
    """Send a task to another agent via Redis."""
    message = {
        "id": task_id,
        "from": from_agent,
        "to": to_agent,
        "task": task_description,
        "context_keys": context_keys,   # Tell receiver what to read
        "requires_approval": requires_approval,
        "timestamp": datetime.now().isoformat()
    }
    await redis_client.publish(TASK_CHANNEL, json.dumps(message))

async def report_result(redis_client, task_id: str, agent: str, result: dict):
    """Agent reports back its completed work."""
    message = {
        "task_id": task_id,
        "from": agent,
        "status": "completed",
        "result": result,
        "timestamp": datetime.now().isoformat()
    }
    await redis_client.publish(RESULT_CHANNEL, json.dumps(message))

async def listen_for_tasks(redis_client, agent_name: str, handler):
    """Each agent runs this to receive tasks addressed to it."""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(TASK_CHANNEL)

    async for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            if data.get("to") == agent_name or data.get("to") == "all":
                await handler(data)   # Your agent's task handler
🤝 Step 3 — Coordination: The Orchestrator's Job
The crew-orchestrator is already your BROski manager. Update main.py to add proper delegation logic:
​

python
# In agents/crew-orchestrator/main.py — add this function

async def coordinate_workflow(task: TaskDefinition):
    """
    BROski breaks big task into steps, delegates to specialists.
    Follows the Bible's handle_user_request pattern.
    """
    workflow_steps = []

    # 1. Backend investigates first
    workflow_steps.append({
        "agent": "backend_specialist",
        "task": f"Investigate codebase for: {task.description}",
        "writes_context": f"workflow.{task.id}.investigation"
    })

    # 2. Relevant specialist does the work
    workflow_steps.append({
        "agent": task.agent or "backend_specialist",
        "task": task.description,
        "reads_context": f"workflow.{task.id}.investigation",
        "writes_context": f"workflow.{task.id}.implementation"
    })

    # 3. QA validates
    workflow_steps.append({
        "agent": "qa_engineer",
        "task": f"Validate and test: {task.description}",
        "reads_context": f"workflow.{task.id}.implementation"
    })

    results = []
    for step in workflow_steps:
        agent_key = step["agent"].replace("-", "_")
        agent_url = settings.agents.get(agent_key, f"http://{step['agent']}:8000")

        # Pass context keys so agent knows what to read
        payload = {
            "id": task.id,
            "task": step["task"],
            "type": task.type,
            "read_context": step.get("reads_context"),
            "write_context": step.get("writes_context"),
            "requires_approval": False
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{agent_url}/execute",
                json=payload,
                timeout=120.0
            )
            if response.status_code == 200:
                results.append({step["agent"]: response.json()})
            else:
                break   # Stop workflow on failure

    return results
📢 Step 4 — SSE Event Streaming (The Timeline)
Every agent must broadcast its activity to the SSE stream so the BROski Terminal can display it. Add this to each agent:
​

python
# agents/shared/event_broadcaster.py
import redis.asyncio as redis
import json
from datetime import datetime

SSE_CHANNEL = "agent:events"

async def emit(redis_client, agent: str, event_type: str, data: dict = {}):
    """
    Broadcast event to SSE timeline.
    Standard event types from the Bible:
    task_started | task_progress | task_completed | task_failed
    delegation_started | delegation_completed
    """
    event = {
        "event": event_type,
        "agent": agent,
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    await redis_client.publish(SSE_CHANNEL, json.dumps(event))

# Example usage inside any agent:
await emit(redis_client, "backend_specialist", "task_started", {
    "task": "Implement JWT middleware",
    "estimated_duration_seconds": 120
})

# Progress updates
await emit(redis_client, "backend_specialist", "task_progress", {
    "progress": 45,
    "current_step": "Writing middleware logic"
})

# Done!
await emit(redis_client, "backend_specialist", "task_completed", {
    "files_created": ["app/middleware/jwt.py"],
    "duration_ms": 3200
})
Then in hypercode-core/main.py, expose the SSE endpoint:

python
from fastapi.responses import StreamingResponse

@app.get("/agents/stream")
async def agent_event_stream():
    """SSE endpoint — BROski Terminal subscribes here."""
    async def generator():
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("agent:events")
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                yield f"data: {msg['data']}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
🧪 Step 5 — Testing Multi-Agent Comms
Run these tests to confirm everything talks properly:

bash
# Test 1 — Context store round-trip
docker exec crew-orchestrator python -c "
import asyncio
from shared.context_manager import init_redis, write_context, read_context

async def test():
    await init_redis()
    await write_context('test.ping', {'value': 'pong'}, 'test_agent')
    result = await read_context('test.ping')
    assert result['value'] == 'pong'
    print('✅ Context store working!')

asyncio.run(test())
"

# Test 2 — Pub/Sub messaging
docker exec crew-orchestrator python -c "
import asyncio, redis.asyncio as redis, json

async def test():
    r = await redis.from_url('redis://redis:6379', decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe('agent:tasks')
    await r.publish('agent:tasks', json.dumps({'to': 'test', 'task': 'hello'}))
    msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=2)
    print('✅ Pub/Sub working!' if msg else '❌ No message received')

asyncio.run(test())
"
🚀 Step 6 — Wire Each Agent
Every agent container needs these additions to its main.py:

python
# At startup — subscribe to task channel
@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = await redis.from_url(REDIS_URL, decode_responses=True)

    # Start listening for delegated tasks
    task = asyncio.create_task(
        listen_for_tasks(redis_client, "backend_specialist", handle_delegated_task)
    )
    yield
    task.cancel()

# Handler for incoming delegated tasks
async def handle_delegated_task(message: dict):
    task_id = message["id"]
    description = message["task"]
    read_key = message.get("read_context")
    write_key = message.get("write_context")

    # Read shared context if provided
    prior_context = {}
    if read_key:
        prior_context = await read_context(read_key)

    # Do the work (your existing agent logic here)
    result = await do_agent_work(description, prior_context)

    # Write output to shared context
    if write_key:
        await write_context(write_key, result, agent_name="backend_specialist")

    # Report back
    await report_result(redis_client, task_id, "backend_specialist", result)
✅ Performance Optimisation Tips
Context TTL — Set ex=3600 (1hr) on Redis contexts; stale data = wrong decisions
​

Parallel agents — Use asyncio.gather() for independent agents running simultaneously

Heartbeats — Each agent publishes agent:heartbeat every 30s so the Healer Agent knows who's alive

Cost guards — The Bible mandates max cost limits; add ORCHESTRATOR_MAX_COST_USD=1.0 to your .env
​

Circuit breaker — If an agent fails 3x in a row, route around it (your Healer Agent handles this!)

