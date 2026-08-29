"""
Agent Delegator for the Meta-Research Architect.
Handles task distribution to existing HyperCode specialists.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from enum import Enum

from .models import MetaAgentAction, ResearchFinding, GitHubInsight, OrchestrationSuggestion, ExplanationChunk

logger = logging.getLogger(__name__)

class TaskType(Enum):
    """Types of tasks the meta-agent can delegate."""
    RESEARCH = "research"
    GITHUB_ANALYSIS = "github_analysis"
    ORCHESTRATION_TUNE = "orchestration_tune"
    EXPLANATION = "explanation"
    SELF_EVOLVE = "self_evolve"

class DelegationTarget(Enum):
    """Existing HyperCode specialists that can handle tasks."""
    FOCUS_TRACKER = "focus_tracker"
    ANALYTICS_ENGINE = "analytics_engine"
    GITHUB_WEBHOOK_SERVER = "github_webhook_server"
    MORNING_BRIEFING = "morning_briefing"
    HYPER_BRAIN_CORE = "hyper_brain_core"
    CREW_ORCHESTRATOR = "crew_orchestrator"
    AGENT_TRAINING = "agent_training"

class AgentDelegator:
    """Delegates tasks to appropriate HyperCode specialists."""

    def __init__(self):
        self.task_queue: List[MetaAgentAction] = []
        self.active_tasks: Dict[str, MetaAgentAction] = {}
        self.completed_tasks: List[MetaAgentAction] = []

    async delegate_task(self, action: MetaAgentAction) -> bool:
        """
        Delegate a task to an appropriate specialist.

        Returns:
            bool: True if task was successfully delegated, False otherwise
        """
        try:
            logger.info(f"Delegating task {action.id} of type {action.action_type}")

            # Determine the appropriate target based on action type
            target = self._determine_target(action)

            if target is None:
                logger.warning(f"No suitable target found for action {action.id}")
                action.status = "failed"
                action.error = "No suitable target found"
                return False

            # Update action status
            action.status = "in_progress"
            self.active_tasks[action.id] = action

            # Delegate to the target (this would involve actual MCP/RPC calls)
            success = await self._delegate_to_target(action, target)

            if success:
                action.status = "completed"
                action.completed_at = datetime.now()
                logger.info(f"Task {action.id} successfully delegated to {target.value}")
            else:
                action.status = "failed"
                logger.error(f"Failed to delegate task {action.id} to {target.value}")

            # Move from active to completed
            if action.id in self.active_tasks:
                del self.active_tasks[action.id]
            self.completed_tasks.append(action)

            return success

        except Exception as e:
            logger.error(f"Error delegating task {action.id}: {e}", exc_info=True)
            action.status = "failed"
            action.error = str(e)
            return False

    def _determine_target(self, action: MetaAgentAction) -> Optional[DelegationTarget]:
        """
        Determine which HyperCode specialist should handle the given action.

        Args:
            action: The action to delegate

        Returns:
            DelegationTarget: The appropriate target, or None if no suitable target
        """
        action_type = action.action_type

        # Map action types to appropriate targets
        if action_type == "research":
            # Research findings go to analytics engine for processing
            return DelegationTarget.ANALYTICS_ENGINE
        elif action_type == "github_analysis":
            # GitHub insights can be handled by the webhook server or crew orchestrator
            return DelegationTarget.GITHUB_WEBHOOK_SERVER
        elif action_type == "orchestration_tune":
            # Orchestration suggestions go to crew orchestrator
            return DelegationTarget.CREW_ORCHESTRATOR
        elif action_type == "explanation":
            # Explanations go to morning briefing for distribution
            return DelegationTarget.MORNING_BRIEFING
        elif action_type == "self_evolve":
            # Self-evolution tasks go to hyper brain core
            return DelegationTarget.HYPER_BRAIN_CORE
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return None

    async def _delegate_to_target(self, action: MetaAgentAction, target: DelegationTarget) -> bool:
        """
        Actually delegate the task to a target specialist.

        In a real implementation, this would use MCP or HTTP calls to the target service.
        For now, we'll simulate the delegation.

        Args:
            action: The action to delegate
            target: The target specialist

        Returns:
            bool: True if delegation was successful
        """
        logger.info(f"Delegating {action.action_type} task {action.id} to {target.value}")

        # Simulate delegation delay
        await asyncio.sleep(0.1)

        # In reality, this would:
        # 1. Format the action data appropriately for the target
        # 2. Send it via the appropriate channel (MCP, HTTP, etc.)
        # 3. Wait for acknowledgment or result
        # 4. Handle any errors

        # For now, we'll simulate success
        return True

    def get_task_status(self, action_id: str) -> Optional[str]:
        """
        Get the status of a task by its ID.

        Args:
            action_id: The ID of the action to check

        Returns:
            str: The status of the action, or None if not found
        """
        # Check active tasks
        if action_id in self.active_tasks:
            return self.active_tasks[action_id].status

        # Check completed tasks
        for task in self.completed_tasks:
            if task.id == action_id:
                return task.status

        # Check queued tasks
        for task in self.task_queue:
            if task.id == action_id:
                return task.status

        return None

    def get_pending_tasks(self) -> List[MetaAgentAction]:
        """
        Get all pending tasks.

        Returns:
            List[MetaAgentAction]: List of pending tasks
        """
        return [task for task in self.task_queue if task.status == "pending"]

    def get_active_tasks(self) -> List[MetaAgentAction]:
        """
        Get all currently active tasks.

        Returns:
            List[MetaAgentAction]: List of active tasks
        """
        return list(self.active_tasks.values())

    def get_completed_tasks(self) -> List[MetaAgentAction]:
        """
        Get all completed tasks.

        Returns:
            List[MetaAgentAction]: List of completed tasks
        """
        return self.completed_tasks.copy()