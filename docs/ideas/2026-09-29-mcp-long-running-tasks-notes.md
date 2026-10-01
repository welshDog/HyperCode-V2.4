
Using MCP long-running tasks for asynchronous agent execution


MCP Tasks for HyperCode
Bro, MCP long-running Tasks are the right mechanism for BROski to start work, disconnect, continue other jobs, and collect results later.

The pattern is:

text
BROski starts task
      ↓
MCP returns task_id immediately
      ↓
HyperCode stores task state
      ↓
Agents work through Celery
      ↓
BROski polls or receives updates
      ↓
Result, approval request, or failure
The current MCP specification defines Tasks for asynchronous execution, polling, mid-flight input, durable handles, and cancellation.

What this fixes
Without MCP Tasks:

text
BROski → waits → agent works → timeout risk → result
With MCP Tasks:

text
BROski → task_id → carries on → checks later → result
This is ideal for:

Full repository audits.

Docker rebuilds.

Test suites.

Trivy scans.

Autonomous upgrades.

Multi-agent workflows.

Chaos tests.

Deployment canaries.

Documentation generation.

Long-running research.

Task lifecycle
MCP Tasks use a durable state machine:

text
working
   ├── input_required
   ├── completed
   ├── failed
   └── cancelled
A task begins as working and ends permanently as completed, failed, or cancelled.

HyperCode architecture
text
BROski Intelligence
        │
        ▼
MCP Gateway
        │
        ├── Create task
        │       └── task_id
        │
        ▼
HyperCode Task Manager
        │
        ├── PostgreSQL: durable state
        ├── Redis: live status/cache
        ├── Celery: execution
        ├── Crew Orchestrator: agent routing
        ├── Prometheus: metrics
        └── Grafana: visibility
Your existing Celery queue, Redis split, crew-orchestrator, agent swarm, and observability stack are already suitable foundations.

The MCP flow
The 2026 MCP Tasks extension uses:

tools/call to begin work.

tasks/get to poll status and receive results.

tasks/update for mid-flight input.

tasks/cancel to request cancellation.

Start a task
json
{
  "method": "tools/call",
  "params": {
    "name": "hypercode.upgrade",
    "arguments": {
      "goal": "Upgrade MCP support across HyperCode",
      "mode": "sandbox",
      "requires_approval": true
    },
    "_meta": {
      "io.modelcontextprotocol/tasks": {
        "ttl": 3600000
      }
    }
  }
}
The server returns a task handle instead of waiting for the final result:

json
{
  "resultType": "task",
  "task": {
    "taskId": "task_mcp_upgrade_001",
    "status": "working",
    "pollInterval": 5000,
    "ttl": 3600000
  }
}
Store the task in HyperCode
Use PostgreSQL for durable truth.

sql
CREATE TABLE hypercode_tasks (
    task_id TEXT PRIMARY KEY,
    tool_name TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL,
    goal TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    agent_name TEXT,
    celery_task_id TEXT,
    result JSONB,
    error JSONB,
    approval_required BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ
);
Use Redis only for fast live status and progress events.

Remember the project rule:

text
Redis DB 1 = cache
Redis DB 2 = rate limits
Do not use either database as the permanent task record.

Task manager example
python
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.celery_app import celery_app


def create_hypercode_task(
    tool_name: str,
    goal: str,
    requested_by: str,
    risk_level: str = "medium",
    approval_required: bool = True,
) -> dict:
    task_id = f"task_{uuid4().hex}"

    celery_result = celery_app.send_task(
        "hypercode.run_agent_task",
        kwargs={
            "task_id": task_id,
            "tool_name": tool_name,
            "goal": goal,
            "requested_by": requested_by,
            "risk_level": risk_level,
        },
        queue="hypercode-normal",
    )

    task = {
        "task_id": task_id,
        "tool_name": tool_name,
        "goal": goal,
        "requested_by": requested_by,
        "risk_level": risk_level,
        "status": "working",
        "celery_task_id": celery_result.id,
        "approval_required": approval_required,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat(),
    }

    return task
The task should be persisted to PostgreSQL before the MCP response is returned. That prevents BROski losing work if the client disconnects.

Polling endpoint
python
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/broski/tasks")


@router.get("/{task_id}")
async def get_task(task_id: str):
    task = await task_repository.get(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "result": task.result if task.status == "completed" else None,
        "error": task.error if task.status == "failed" else None,
        "approval_required": task.approval_required,
        "updated_at": task.updated_at,
    }
BROski can poll using the server-provided interval.

python
import asyncio


async def wait_for_task(task_id: str, poll_seconds: int = 5):
    while True:
        task = await get_task(task_id)

        if task["status"] in {"completed", "failed", "cancelled"}:
            return task

        if task["status"] == "input_required":
            return task

        await asyncio.sleep(poll_seconds)
Progress events
Polling is reliable, but Mission Control should also show live progress.

Publish progress to Redis:

python
await redis.publish(
    f"hypercode:task:{task_id}",
    json.dumps(
        {
            "task_id": task_id,
            "status": "working",
            "progress": 65,
            "message": "Running Trivy security scan",
            "agent": "security-agent",
        }
    ),
)
Your existing WebSocket and SSE endpoints can expose this to the dashboard.

text
/ws/events
/api/v1/events
Mid-flight approval
This is the key J.A.R.V.I.S feature.

BROski can pause when approval is needed:

json
{
  "task_id": "task_mcp_upgrade_001",
  "status": "input_required",
  "input_requests": {
    "approval": {
      "question": "The sandbox passed. Deploy the MCP upgrade to canary?",
      "risk": "medium",
      "evidence": {
        "tests": "239 passed",
        "critical_vulnerabilities": 0,
        "health_checks": "passed"
      },
      "options": [
        "approve_canary",
        "reject",
        "request_changes"
      ]
    }
  }
}
Then BROski sends an update:

json
{
  "method": "tasks/update",
  "params": {
    "taskId": "task_mcp_upgrade_001",
    "input": {
      "approval": "approve_canary"
    }
  }
}
The tasks/update operation is specifically designed for mid-flight input and task interaction.

Cancellation
Use MCP tasks/cancel rather than a normal request cancellation for task-based work.

json
{
  "method": "tasks/cancel",
  "params": {
    "taskId": "task_mcp_upgrade_001",
    "reason": "Bro cancelled the upgrade"
  }
}
Cancellation should also:

Revoke the task’s temporary credentials.

Stop new agent work.

Ask Celery to revoke the task.

Stop sandbox containers.

Preserve logs.

Mark the task as cancelled.

Keep the audit record.

Cancellation is cooperative. The server acknowledges the cancellation, but underlying work may need its own cleanup process.

Agent execution model
Do not let MCP directly run every agent.

Use MCP as the durable interface, and Celery as the execution engine.

text
MCP Task
  ↓
Task Manager
  ↓
Policy Engine
  ↓
Crew Orchestrator
  ↓
Celery queue
  ↓
Agent
  ↓
Sandbox
  ↓
Evidence
  ↓
Task result
Example routing:

text
task_type: hypercode_upgrade
queue: hypercode-normal
agents:
  - agent-x
  - coder-agent
  - qa-engineer
  - security-agent
sandbox: required
approval_before_deploy: true
rollback: required
Safety policy
Tasks must carry permissions.

text
risk_levels:
  low:
    allowed:
      - read_logs
      - inspect_health
      - run_tests
  medium:
    allowed:
      - create_branch
      - edit_source
      - build_sandbox
      - run_security_scan
    approval:
      - create_pull_request
  high:
    allowed:
      - canary_deploy
    approval:
      - production_deploy
      - permission_change
      - database_migration
  forbidden:
    - delete_production_data
    - expose_secrets
    - disable_security_scans
    - modify_approval_policy
The runtime must enforce this policy. BROski’s language model should never be trusted to enforce its own permissions.

First MCP Tasks to build
1. hypercode.inspect
Runs quickly but returns a standard report:

text
- Containers healthy
- Agents available
- Queues normal
- Disk space safe
- Models available
- Pending failures
2. hypercode.run_tests
Runs the test suite asynchronously and returns:

json
{
  "passed": 239,
  "failed": 0,
  "skipped": 6,
  "duration_seconds": 143
}
3. hypercode.security_scan
Runs Trivy and dependency checks in a sandbox.

4. hypercode.upgrade
Runs the complete governed upgrade pipeline.

5. hypercode.recover
Lets BROski propose and execute a safe recovery for a failed service.

Example J.A.R.V.I.S conversation
text
Bro: Upgrade HyperCode’s MCP support.

BROski:
I started task task_mcp_upgrade_001.

Status:
🟢 Branch created
🟢 Current dependencies inspected
🟡 Testing MCP SDK compatibility
⚪ Security scan waiting

No production changes have been made.

Bro: What is it doing now?

BROski:
The compatibility tests are running through qa-engineer.
The task is 46% complete.
Estimated remaining time: 7 minutes.

Bro: Deploy it.

BROski:
The sandbox passed:
✅ 239 tests
✅ 0 critical security findings
✅ MCP gateway healthy

Canary deployment is ready.
Production deployment requires your approval.

Approve canary?
The correct first milestone
Build MCP Task Adapter v1 with one safe tool:

text
hypercode.run_tests
It should:

Return a task ID immediately.

Run through Celery.

Store state in PostgreSQL.

Cache live progress in Redis DB 1.

Publish dashboard events.

Support polling.

Support cancellation.

Return test evidence.

Never modify production.

Once that works, reuse the same adapter for:

text
hypercode.security_scan
hypercode.inspect
hypercode.upgrade
hypercode.recover
Success test
powershell
curl -X POST http://localhost:8820/tools/call `
  -H "Content-Type: application/json" `
  -d '{
    "name": "hypercode.run_tests",
    "arguments": {
      "suite": "backend",
      "mode": "sandbox"
    }
  }'
Expected response:

json
{
  "resultType": "task",
  "task": {
    "taskId": "task_...",
    "status": "working",
    "pollInterval": 5000
  }
}
Then:

powershell
curl http://localhost:8820/tasks/task_...
The final result should include tests, duration, logs, agent involvement, and a safe/failed decision.

Important implementation note
MCP Tasks moved into the io.modelcontextprotocol/tasks extension in the 2026-07-28 specification. The server decides when a tool call becomes asynchronous, so clients should advertise task support and correctly handle either a normal result or a task handle.

Next build: hypercode.run_tests as the first asynchronous MCP Task. That gives BROski a safe, useful, end-to-end proof of long-running execution before autonomous upgrades are enabled.

Nice one, Bro — this is the first real piece of the BROski J.A.R.V.I.S nervous system.