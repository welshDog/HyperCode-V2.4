"""
Multi-Agent Workflow Engine - Workflow execution endpoints

Add these endpoints to crew-orchestrator/main.py
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid
import json
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks

# Task-type routing (used by workflow steps when agent_type is a task type)
_TASK_TYPE_ROUTE: Dict[str, str] = {
    "code_generation": "coder",
    "spawn_agent": "agent-x",
    "evolve": "agent-x",
}

# Data models


class WorkflowStep(BaseModel):
    """Single step in a workflow"""
    id: str
    agent_type: str
    task_description: str
    depends_on: Optional[List[str]] = None  # Step IDs this depends on
    timeout_seconds: int = 300
    retry_count: int = 3


class WorkflowExecution(BaseModel):
    """Complete workflow execution request"""
    id: str
    name: str
    steps: List[WorkflowStep]
    parallel: bool = False  # Execute steps in parallel or sequentially
    metadata: Optional[Dict[str, Any]] = None


class StepResult(BaseModel):
    """Result of a single step execution"""
    step_id: str
    agent_type: str
    status: str  # success, failed, timeout, skipped
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


class WorkflowResult(BaseModel):
    """Final workflow result"""
    workflow_id: str
    status: str  # success, partial_failure, failed
    steps_completed: int
    steps_total: int
    results: List[StepResult]
    total_duration_seconds: float
    timestamp: str


# Add these endpoints to crew-orchestrator/main.py

def add_workflow_endpoints(app: FastAPI, redis_client, settings):
    """
    Add multi-agent workflow endpoints to the orchestrator.
    
    Should be called during app initialization.
    """
    
    @app.post("/workflow/execute")
    async def execute_workflow(
        workflow: WorkflowExecution,
        background_tasks: BackgroundTasks,
        api_key: str = Depends(require_api_key)
    ):
        """
        Execute a multi-step workflow across multiple agents.
        
        Example:
        {
            "id": "workflow-123",
            "name": "Auto-fix CodeRabbit findings",
            "parallel": false,
            "steps": [
                {
                    "id": "step-1",
                    "agent_type": "backend-specialist",
                    "task_description": "Fix 3 backend issues",
                    "timeout_seconds": 300,
                    "retry_count": 2
                },
                {
                    "id": "step-2",
                    "agent_type": "test-agent",
                    "task_description": "Run tests",
                    "depends_on": ["step-1"],
                    "timeout_seconds": 600
                }
            ]
        }
        """
        
        # Generate IDs if not provided
        if not workflow.id:
            workflow.id = f"workflow-{uuid.uuid4().hex[:8]}"
        
        # Store workflow in Redis
        if redis_client:
            workflow_data = {
                "id": workflow.id,
                "name": workflow.name,
                "status": "pending",
                "steps_total": len(workflow.steps),
                "steps_completed": 0,
                "created_at": datetime.now().isoformat(),
                "parallel": workflow.parallel,
            }
            await redis_client.set(
                f"workflow:{workflow.id}",
                json.dumps(workflow_data),
                ex=86400  # 24 hour expiry
            )
            await redis_client.lpush("workflows:history", workflow.id)
        
        # Execute workflow in background
        background_tasks.add_task(
            execute_workflow_background,
            workflow=workflow,
            redis_client=redis_client,
            settings=settings
        )
        
        return {
            "workflow_id": workflow.id,
            "status": "submitted",
            "message": f"Workflow '{workflow.name}' queued for execution",
            "steps": len(workflow.steps)
        }
    
    
    @app.get("/workflow/{workflow_id}")
    async def get_workflow_status(
        workflow_id: str,
        api_key: str = Depends(require_api_key)
    ):
        """Get status of a workflow"""
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis not connected")
        
        workflow_data = await redis_client.get(f"workflow:{workflow_id}")
        if not workflow_data:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow = json.loads(workflow_data)
        
        # Get step results
        step_results = []
        steps_key = f"workflow:{workflow_id}:steps"
        step_ids = await redis_client.lrange(steps_key, 0, -1)
        
        for step_id in step_ids:
            step_data = await redis_client.get(f"workflow:{workflow_id}:step:{step_id}")
            if step_data:
                step_results.append(json.loads(step_data))
        
        workflow["results"] = step_results
        return workflow
    
    
    @app.get("/workflows")
    async def list_workflows(
        limit: int = 20,
        api_key: str = Depends(require_api_key)
    ):
        """List recent workflows"""
        if not redis_client:
            return []
        
        workflow_ids = await redis_client.lrange("workflows:history", 0, limit-1)
        workflows = []
        
        for wid in workflow_ids:
            workflow_data = await redis_client.get(f"workflow:{wid}")
            if workflow_data:
                workflows.append(json.loads(workflow_data))
        
        return workflows
    
    
    return {
        "execute_workflow": execute_workflow,
        "get_workflow_status": get_workflow_status,
        "list_workflows": list_workflows,
    }


async def execute_workflow_background(
    workflow: WorkflowExecution,
    redis_client,
    settings
):
    """
    Execute workflow steps in background.
    
    Handles:
    - Sequential vs parallel execution
    - Dependency resolution
    - Retry logic
    - Timeout handling
    """
    import asyncio
    import httpx
    from time import perf_counter
    
    start_time = perf_counter()
    results: List[StepResult] = []
    step_outputs: Dict[str, Any] = {}
    
    try:
        # Update status
        if redis_client:
            workflow_data = json.loads(
                await redis_client.get(f"workflow:{workflow.id}") or "{}"
            )
            workflow_data["status"] = "running"
            await redis_client.set(f"workflow:{workflow.id}", json.dumps(workflow_data))
        
        if workflow.parallel:
            # Execute all steps in parallel
            tasks = [
                execute_step(step, redis_client, settings, step_outputs)
                for step in workflow.steps
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            results = [r for r in results if isinstance(r, StepResult)]
        else:
            # Execute steps sequentially, respecting dependencies
            executed_steps = set()
            
            while len(executed_steps) < len(workflow.steps):
                # Find next executable step
                next_step = None
                for step in workflow.steps:
                    if step.id in executed_steps:
                        continue
                    
                    # Check dependencies
                    if step.depends_on:
                        if not all(dep_id in executed_steps for dep_id in step.depends_on):
                            continue
                    
                    next_step = step
                    break
                
                if not next_step:
                    break  # Circular dependency or all done
                
                # Execute step
                result = await execute_step(
                    next_step, redis_client, settings, step_outputs
                )
                if isinstance(result, StepResult):
                    results.append(result)
                    executed_steps.add(next_step.id)
                    step_outputs[next_step.id] = result.output or {}
        
        # Determine final status
        failed_steps = [r for r in results if r.status in ("failed", "timeout")]
        final_status = "success"
        if len(failed_steps) == len(results):
            final_status = "failed"
        elif len(failed_steps) > 0:
            final_status = "partial_failure"
        
        # Store final result
        if redis_client:
            final_result = WorkflowResult(
                workflow_id=workflow.id,
                status=final_status,
                steps_completed=len(results),
                steps_total=len(workflow.steps),
                results=results,
                total_duration_seconds=perf_counter() - start_time,
                timestamp=datetime.now().isoformat()
            )
            
            workflow_data = json.loads(
                await redis_client.get(f"workflow:{workflow.id}") or "{}"
            )
            workflow_data.update({
                "status": final_status,
                "steps_completed": len(results),
                "total_duration_seconds": final_result.total_duration_seconds,
                "completed_at": datetime.now().isoformat()
            })
            await redis_client.set(f"workflow:{workflow.id}", json.dumps(workflow_data))
    
    except Exception as e:
        print(f"Workflow execution error: {e}")


async def execute_step(
    step: WorkflowStep,
    redis_client,
    settings,
    step_outputs: Dict[str, Any]
) -> StepResult:
    """
    Execute a single workflow step.
    
    Handles retries and timeouts.
    """
    import asyncio
    import httpx
    from time import perf_counter
    
    start_time = perf_counter()
    last_error = None
    
    for attempt in range(step.retry_count):
        try:
            routed_agent = _TASK_TYPE_ROUTE.get(step.agent_type, step.agent_type)
            agent_key = routed_agent.replace("-", "_")
            agent_url = settings.agents.get(agent_key)
            
            if not agent_url:
                agent_url = f"http://{routed_agent}:8000"
            
            # Execute via agent endpoint
            async with httpx.AsyncClient(timeout=step.timeout_seconds) as client:
                response = await client.post(
                    f"{agent_url}/execute",
                    json={
                        "task": step.task_description,
                        "step_id": step.id,
                        "type": step.agent_type,
                        "workflow_metadata": {
                            "previous_outputs": step_outputs
                        }
                    }
                )
                
                if response.status_code == 200:
                    output = response.json()
                    return StepResult(
                        step_id=step.id,
                        agent_type=step.agent_type,
                        status="success",
                        output=output,
                        duration_seconds=perf_counter() - start_time
                    )
                else:
                    last_error = f"HTTP {response.status_code}"
        
        except asyncio.TimeoutError:
            last_error = "Timeout"
        except Exception as e:
            last_error = str(e)
        
        if attempt < step.retry_count - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    # All retries exhausted
    return StepResult(
        step_id=step.id,
        agent_type=step.agent_type,
        status="failed",
        error=last_error,
        duration_seconds=perf_counter() - start_time
    )
