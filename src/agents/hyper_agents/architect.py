"""ArchitectAgent - The planning and coordination lead for HyperCode.

Designed with neurodivergent-friendly principles:
- Big picture first: define clear milestones before starting
- Decomposition: break complex goals into small, sensory-safe tasks
- Resource management: ensure agents aren't overwhelmed
- Conflict resolution: clear decision-making logic
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from src.agents.hyper_agents.base_agent import (
    AgentArchetype,
    AgentStatus,
    HyperAgent,
    NDErrorResponse,
)


class GoalStatus(Enum):
    """The lifecycle of a goal - always transparent."""

    DEFINED = "defined"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PlanStep:
    """A single executable step in a larger plan."""

    step_id: str
    description: str
    assigned_to: Optional[str] = None  # agent_id
    depends_on: Set[str] = field(default_factory=set)  # step_ids
    status: GoalStatus = GoalStatus.DEFINED
    result: Any = None
    error: Optional[str] = None

    def is_ready(self, completed_steps: Set[str]) -> bool:
        """Check if all dependencies are met."""
        return self.depends_on.issubset(completed_steps)


@dataclass
class Goal:
    """A high-level objective broken down into steps."""

    goal_id: str
    title: str
    description: str
    steps: List[PlanStep] = field(default_factory=list)
    status: GoalStatus = GoalStatus.DEFINED
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        """Calculate completion percentage."""
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status == GoalStatus.COMPLETED)
        return completed / len(self.steps)


class ArchitectAgent(HyperAgent):
    """ArchitectAgent - High-level planning and multi-agent coordination.

    The Architect is the "thinking" lead. It takes broad user requests and
    converts them into structured plans that other agents can execute.

    Core Capabilities:
    - Goal decomposition: breaking "Build X" into [Step 1, Step 2, ...]
    - Dependency management: ensuring tasks happen in the right order
    - Agent registry: keeping track of available Workers and Observers
    - Status aggregation: providing a single "Big Picture" view
    - Dynamic re-planning: adjusting when steps fail or environment changes

    ND-Friendly Features:
    - Always provides a plan BEFORE starting execution
    - Breaks tasks into "bite-sized" chunks (avoids overwhelm)
    - Explicitly marks what is blocked and why
    - Provides clear milestones for dopamine hits upon completion

    Example usage::

        architect = ArchitectAgent(name="lead-architect-01")
        goal_id = architect.create_goal("Deploy Microservice")
        step_a = architect.add_step(goal_id, "Build Docker image")
        step_b = architect.add_step(goal_id, "Run unit tests", depends_on=[step_a])
        print(f"Goal progress: {architect.goal_progress(goal_id):.1%}")
    """

    ARCHETYPE = AgentArchetype.ARCHITECT

    def __init__(
        self,
        name: str,
        archetype: AgentArchetype = AgentArchetype.ARCHITECT,
        planning_timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, archetype=archetype, **kwargs)
        self.planning_timeout = planning_timeout
        self._goals: Dict[str, Goal] = {}
        self._agent_registry: Dict[str, str] = {}  # name -> role/archetype
        self._active_goal_id: Optional[str] = None
        self._total_goals_completed: int = 0

    async def initialize(self) -> None:
        """Prepare the architect for planning."""
        self._log("ArchitectAgent initializing...")
        self.status = AgentStatus.STARTING
        await asyncio.sleep(0)
        self.status = AgentStatus.READY
        self._log(f"ArchitectAgent '{self.name}' ready for planning.")

    def create_goal(self, description: str) -> str:
        """Create a new top-level goal.

        Args:
            description: Full context/requirements (also used as title).

        Returns:
            goal_id for tracking.
        """
        goal_id = str(uuid.uuid4())[:8]
        goal = Goal(goal_id=goal_id, title=description, description=description)
        self._goals[goal_id] = goal
        self._log(f"New goal created [{goal_id}]: {description}")
        return goal_id

    def add_step(
        self,
        goal_id: str,
        description: str,
        depends_on: Optional[List[str]] = None,
        assigned_to: Optional[str] = None,
    ) -> str:
        """Add an execution step to a goal.

        Args:
            goal_id: Parent goal.
            description: What needs to be done.
            depends_on: List of step_ids that must complete first.
            assigned_to: ID of the agent to perform the step.

        Returns:
            step_id for tracking.
        """
        if goal_id not in self._goals:
            raise ValueError(f"Goal {goal_id} not found")

        step_id = str(uuid.uuid4())[:8]
        step = PlanStep(
            step_id=step_id,
            description=description,
            assigned_to=assigned_to,
            depends_on=set(depends_on or []),
        )
        self._goals[goal_id].steps.append(step)
        self._log(f"Step added to [{goal_id}]: {step_id} - {description}")
        return step_id

    def complete_step(self, goal_id: str, step_id: str) -> None:
        """Mark a step as completed."""
        self.update_step_status(goal_id, step_id, GoalStatus.COMPLETED)

    def fail_step(self, goal_id: str, step_id: str, error: Optional[str] = None) -> None:
        """Mark a step as failed."""
        self.update_step_status(goal_id, step_id, GoalStatus.FAILED, error=error)

    def register_sub_agent(self, name: str, role: str) -> None:
        """Register a sub-agent by name and role string."""
        self._agent_registry[name] = role
        self._log(f"Sub-agent registered: {name} ({role})")

    def register_agent(self, agent_id: str, archetype: AgentArchetype) -> None:
        """Register an agent by id and archetype enum."""
        self._agent_registry[agent_id] = archetype.value
        self._log(f"Agent registered: {agent_id} ({archetype.value})")

    @property
    def registered_agents(self) -> Dict[str, str]:
        """Public view of the agent registry."""
        return self._agent_registry

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Retrieve full goal details."""
        return self._goals.get(goal_id)

    def goal_progress(self, goal_id: str) -> float:
        """Return completion fraction (0.0–1.0) for a goal."""
        goal = self._goals.get(goal_id)
        return goal.progress if goal else 0.0

    def get_ready_steps(self, goal_id: str) -> List[PlanStep]:
        """Find steps that are ready for execution (deps met, not started)."""
        goal = self._goals.get(goal_id)
        if not goal:
            return []

        completed = {s.step_id for s in goal.steps if s.status == GoalStatus.COMPLETED}
        return [
            s for s in goal.steps
            if s.status == GoalStatus.DEFINED and s.is_ready(completed)
        ]

    def update_step_status(
        self,
        goal_id: str,
        step_id: str,
        status: GoalStatus,
        result: Any = None,
        error: Optional[str] = None,
    ) -> None:
        """Update a step's progress and check for goal completion."""
        goal = self._goals.get(goal_id)
        if not goal:
            return

        for step in goal.steps:
            if step.step_id == step_id:
                step.status = status
                step.result = result
                step.error = error
                self._log(f"Step [{goal_id}:{step_id}] status -> {status.value}")
                break

        # Check if goal is now complete or failed
        if all(s.status == GoalStatus.COMPLETED for s in goal.steps):
            goal.status = GoalStatus.COMPLETED
            self._total_goals_completed += 1
            self._log(f"GOAL COMPLETED [{goal_id}]: {goal.title}")
        elif any(s.status == GoalStatus.FAILED for s in goal.steps):
            goal.status = GoalStatus.FAILED
            self._log(f"GOAL FAILED [{goal_id}]: One or more steps failed")

    @property
    def stats(self) -> Dict[str, Any]:
        """Current architect statistics."""
        return {
            "name": self.name,
            "status": self.status.value,
            "total_goals": len(self._goals),
            "completed_goals": self._total_goals_completed,
            "registered_agents": len(self._agent_registry),
            "active_goal": self._active_goal_id,
        }

    def _log(self, message: str) -> None:
        print(f"[ArchitectAgent:{self.name}] {message}")

    def shutdown(self) -> None:
        """Graceful shutdown - archive goals, notify agents."""
        self._log("Initiating graceful shutdown...")
        super().shutdown()
        self._log(f"Shutdown complete. Final stats: {self.stats}")
