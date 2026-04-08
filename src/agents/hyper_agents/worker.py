"""WorkerAgent - The task execution specialist in HyperCode's hyper-agent system.

Designed with neurodivergent-friendly principles:
- Clear task boundaries with explicit start/end signals
- Hyperfocus support: deep single-task execution mode
- Transparent progress reporting at every step
- Sensory-safe error messages (no sudden failures, graceful degradation)
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.agents.hyper_agents.base_agent import (
    AgentArchetype,
    AgentStatus,
    HyperAgent,
    NDErrorResponse,
)


class TaskPriority(Enum):
    """Clear priority levels - no ambiguity, no anxiety."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    HYPERFOCUS = 4  # Maximum focus mode - one task, full power


@dataclass
class Task:
    """A single unit of work with full context.

    Every task knows:
    - What it is (name + description)
    - Why it matters (priority)
    - How long it should take (timeout)
    - Where it came from (task_id for tracing)
    """

    name: str
    handler: Callable[..., Any]
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: float = 30.0
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self) -> None:
        if not self.description:
            self.description = f"Execute: {self.name}"


@dataclass
class TaskResult:
    """The outcome of a task - always structured, never surprising."""

    task_id: str
    task_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    retries_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        """Human-readable one-liner for quick status check."""
        status = "OK" if self.success else "FAILED"
        return f"[{status}] {self.task_name} ({self.duration_ms:.0f}ms)"


class WorkerAgent(HyperAgent):
    """WorkerAgent - Focused task execution with neurodivergent-friendly design.

    The WorkerAgent specializes in:
    - Single-task hyperfocus execution
    - Transparent progress tracking
    - Graceful error recovery with clear messaging
    - Priority-based task queuing

    ND-Friendly Features:
    - Every step is logged (no black boxes)
    - Errors explain WHAT went wrong AND what to do next
    - Hyperfocus mode locks onto one task until completion
    - Time estimates provided upfront

    Example usage::

        worker = WorkerAgent(agent_id="data-processor-01")
        await worker.initialize()

        task = Task(
            name="process_dataset",
            handler=my_processing_function,
            args=(dataset,),
            priority=TaskPriority.HYPERFOCUS,
            timeout=60.0,
            description="Processing 10k rows from user upload"
        )

        result = await worker.execute_task(task)
        print(result.summary)
    """

    ARCHETYPE = AgentArchetype.WORKER

    def __init__(
        self,
        name: str,
        archetype: AgentArchetype = AgentArchetype.WORKER,
        max_concurrent_tasks: int = 1,
        hyperfocus_mode: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, archetype=archetype, **kwargs)
        self.max_concurrent_tasks = max_concurrent_tasks
        self.hyperfocus_mode = hyperfocus_mode
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._enqueue_seq: int = 0  # tie-breaker: prevents Task comparison on equal priority
        self._active_tasks: Dict[str, Task] = {}
        self._completed_tasks: List[TaskResult] = []
        self._task_history: List[TaskResult] = []
        self._total_tasks_executed: int = 0
        self._successful_tasks: int = 0

    async def initialize(self) -> None:
        """Spin up the worker - clear signals at each stage."""
        self._log("WorkerAgent initializing...")
        self.status = AgentStatus.STARTING
        await asyncio.sleep(0)  # yield to event loop
        self.status = AgentStatus.READY
        self._log(
            f"WorkerAgent '{self.name}' ready. "
            f"Hyperfocus mode: {'ON' if self.hyperfocus_mode else 'OFF'}"
        )

    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a single task with full tracking and error safety.

        Args:
            task: The Task to execute.

        Returns:
            TaskResult with outcome, duration, and any error details.
        """
        if self.hyperfocus_mode and self._active_tasks:
            return TaskResult(
                task_id=task.task_id,
                task_name=task.name,
                success=False,
                error=(
                    "Hyperfocus mode is active - completing current task first. "
                    "Queue this task for after current work completes."
                ),
            )

        self.status = AgentStatus.BUSY
        self._active_tasks[task.task_id] = task
        self._log(f"Starting task [{task.task_id}]: {task.description}")

        start_time = time.monotonic()
        result = await self._execute_with_retry(task)
        duration_ms = (time.monotonic() - start_time) * 1000
        result.duration_ms = duration_ms

        del self._active_tasks[task.task_id]
        self._completed_tasks.append(result)
        self._task_history.append(result)
        self._total_tasks_executed += 1
        if result.success:
            self._successful_tasks += 1

        self.status = AgentStatus.READY
        self._log(result.summary)
        return result

    async def _execute_with_retry(self, task: Task) -> TaskResult:
        """Attempt task execution with exponential backoff retry."""
        last_error: Optional[str] = None

        for attempt in range(task.max_retries + 1):
            if attempt > 0:
                wait_time = 2 ** attempt
                self._log(
                    f"Retry {attempt}/{task.max_retries} for [{task.task_id}] "
                    f"- waiting {wait_time}s before retry"
                )
                await asyncio.sleep(wait_time)

            try:
                if asyncio.iscoroutinefunction(task.handler):
                    raw_result = await asyncio.wait_for(
                        task.handler(*task.args, **task.kwargs),
                        timeout=task.timeout,
                    )
                else:
                    raw_result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: task.handler(*task.args, **task.kwargs),
                    )

                return TaskResult(
                    task_id=task.task_id,
                    task_name=task.name,
                    success=True,
                    result=raw_result,
                    retries_used=attempt,
                )

            except asyncio.TimeoutError:
                last_error = (
                    f"Task timed out after {task.timeout}s. "
                    "Consider increasing timeout or breaking into smaller tasks."
                )
                self._log(f"Timeout on attempt {attempt + 1}: {task.task_id}")

            except Exception as exc:  # noqa: BLE001
                nd_err = self.format_nd_error(
                    title="Task Execution Error",
                    what_happened=str(exc),
                    why_it_matters="The task could not complete successfully.",
                    options=[
                        "Check the task handler for issues.",
                        "If this persists, reduce task complexity.",
                    ],
                    error_code="TASK_EXECUTION_ERROR",
                )
                last_error = f"[{nd_err.error_code}] {nd_err.what_happened}"
                self._log(f"Error on attempt {attempt + 1}: {exc}")

        return TaskResult(
            task_id=task.task_id,
            task_name=task.name,
            success=False,
            error=last_error,
            retries_used=task.max_retries,
        )

    async def run_queue(self) -> List[TaskResult]:
        """Process all queued tasks in priority order.

        Returns list of results when queue is empty.
        """
        results: List[TaskResult] = []
        while not self._task_queue.empty():
            _, _seq, task = await self._task_queue.get()
            result = await self.execute_task(task)
            results.append(result)
            self._task_queue.task_done()
        return results

    def enqueue(self, task: Task) -> str:
        """Add a task to the priority queue.

        Args:
            task: Task to queue.

        Returns:
            task_id for tracking.
        """
        # Lower number = higher priority in PriorityQueue.
        # Sequence counter breaks ties so Task objects are never compared directly.
        priority_value = 5 - task.priority.value
        self._task_queue.put_nowait((priority_value, self._enqueue_seq, task))
        self._enqueue_seq += 1
        self._log(
            f"Queued task [{task.task_id}]: {task.name} "
            f"(priority: {task.priority.name})"
        )
        return task.task_id

    @property
    def stats(self) -> Dict[str, Any]:
        """Current worker statistics - always visible, never hidden."""
        success_rate = (
            self._successful_tasks / self._total_tasks_executed
            if self._total_tasks_executed > 0
            else 0.0
        )
        return {
            "name": self.name,
            "status": self.status.value,
            "hyperfocus_mode": self.hyperfocus_mode,
            "total_executed": self._total_tasks_executed,
            "successful": self._successful_tasks,
            "success_rate": f"{success_rate:.1%}",
            "active_tasks": len(self._active_tasks),
            "queued_tasks": self._task_queue.qsize(),
        }

    def _log(self, message: str) -> None:
        """Structured logging - every action is visible."""
        print(f"[WorkerAgent:{self.name}] {message}")

    def shutdown(self) -> None:
        """Graceful shutdown with clear status reporting."""
        self._log("Initiating graceful shutdown...")
        if self._active_tasks:
            self._log(
                f"Warning: {len(self._active_tasks)} active task(s) will be abandoned."
            )
        super().shutdown()
        self._log(f"Shutdown complete. Final stats: {self.stats}")
