# agents/mission-executor/agent_delegator.py
"""
Agent delegator for mission-executor service.
Handles delegation of mission plan actions to specialist agents.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any

import httpx
import redis.asyncio as redis
from pydantic import BaseModel

from models import AgentDelegatorConfig, ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)


class AgentDelegator:
    """
    Delegates mission plan actions to specialist agents.

    Responsible for:
    - Parsing mission plans into executable actions
    - Routing actions to appropriate specialist agents
    - Managing execution timing and retries
    - Collecting and aggregating results
    - Ensuring no LLM interpretation occurs during execution
    """

    def __init__(self, config: Optional[AgentDelegatorConfig] = None):
        self.config = config or AgentDelegatorConfig()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._redis_client: Optional[redis.Redis] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for agent communication."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.agent_action_timeout),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
            )
        return self._http_client

    async def _get_redis_client(self) -> redis.Redis:
        """Get or create Redis client for inter-agent communication."""
        if self._redis_client is None:
            redis_url = "redis://redis:6379"  # Could be made configurable
            self._redis_client = redis.from_url(redis_url)
        return self._redis_client

    async def close(self) -> None:
        """Close HTTP and Redis clients."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None

    async def execute_plan(
        self,
        mission_id: str,
        plan_request: Dict[str, Any],
        timeout: int = 300
    ) -> ExecutionResult:
        """
        Execute a mission plan by delegating actions to specialist agents.

        Args:
            mission_id: Unique identifier for the mission
            plan_request: The mission plan to execute (from mission-director)
            timeout: Maximum execution time in seconds

        Returns:
            ExecutionResult with execution status and outputs
        """
        start_time = time.time()
        execution_id = str(uuid.uuid4())

        logger.info(
            f"Starting execution of mission {mission_id} "
            f"(execution_id: {execution_id})"
        )

        # Initialize result tracking
        result = ExecutionResult(
            mission_id=mission_id,
            status=ExecutionStatus.RUNNING,
            started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_time)),
            executed_actions=[],
            agent_outputs={}
        )

        try:
            # Extract actions from plan
            actions = self._extract_actions(plan_request)
            if not actions:
                raise ValueError("No executable actions found in mission plan")

            # Execute actions (could be sequential or parallel based on plan)
            action_results = await self._execute_actions(
                mission_id=mission_id,
                actions=actions,
                execution_id=execution_id
            )

            # Update result with action outcomes
            result.executed_actions = action_results["executed_actions"]
            result.agent_outputs = action_results["agent_outputs"]

            # Determine final status
            if any(action.get("status") == "failed" for action in action_results["executed_actions"]):
                result.status = ExecutionStatus.FAILED
                # Find first failed action for error message
                failed_action = next(
                    (action for action in action_results["executed_actions"]
                     if action.get("status") == "failed"),
                    None
                )
                result.error_message = (
                    failed_action.get("error", "Action failed")
                    if failed_action else "Unknown action failure"
                )
            else:
                result.status = ExecutionStatus.COMPLETED

        except asyncio.TimeoutError:
            logger.error(f"Execution timeout for mission {mission_id}")
            result.status = ExecutionStatus.TIMEOUT
            result.error_message = f"Execution exceeded timeout of {timeout} seconds"
        except Exception as e:
            logger.error(f"Error executing mission {mission_id}: {e}", exc_info=True)
            result.status = ExecutionStatus.FAILED
            result.error_message = f"Execution engine error: {str(e)}"
        finally:
            # Set completion time
            result.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time()))

            # Close clients
            await self.close()

        execution_time = time.time() - start_time
        logger.info(
            f"Completed execution of mission {mission_id} "
            f"in {execution_time:.2f}s with status: {result.status}"
        )

        return result

    def _extract_actions(self, plan_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract executable actions from mission plan.

        Expected plan structure:
        {
            "requested_actions": [
                {
                    "kind": "action_type",
                    "agent": "specialist_agent_name",
                    "parameters": {...}
                },
                ...
            ]
        }
        """
        actions = plan_request.get("requested_actions", [])

        # Validate actions have required fields
        valid_actions = []
        for i, action in enumerate(actions):
            if not isinstance(action, dict):
                logger.warning(f"Skipping invalid action {i}: not a dictionary")
                continue

            required_fields = ["kind", "agent"]
            missing_fields = [field for field in required_fields if field not in action]
            if missing_fields:
                logger.warning(f"Skipping action {i}: missing fields {missing_fields}")
                continue

            valid_actions.append(action)

        if not valid_actions:
            logger.warning("No valid actions found in mission plan")

        return valid_actions

    async def _execute_actions(
        self,
        mission_id: str,
        actions: List[Dict[str, Any]],
        execution_id: str
    ) -> Dict[str, Any]:
        """
        Execute a list of actions, respecting dependencies and concurrency limits.

        For now, we execute actions sequentially. In future versions,
        we could support DAG-based execution based on action dependencies.
        """
        executed_actions = []
        agent_outputs = {}

        # Execute actions sequentially for simplicity and safety
        for action_index, action in enumerate(actions):
            action_start_time = time.time()

            action_record = {
                "action_index": action_index,
                "action_id": f"{execution_id}_action_{action_index}",
                "kind": action.get("kind"),
                "agent": action.get("agent"),
                "parameters": action.get("parameters", {}),
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(action_start_time)),
                "status": "running"
            }

            try:
                logger.info(
                    f"Executing action {action_index}/{len(actions)-1}: "
                    f"{action.get('kind')} via {action.get('agent')}"
                )

                # Execute the action via the appropriate specialist agent
                action_result = await self._execute_single_action(
                    mission_id=mission_id,
                    action=action,
                    execution_id=execution_id
                )

                # Update action record with result
                action_record.update(action_result)
                action_record["completed_at"] = time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time())
                )

                # Store agent output if present
                if "output" in action_result:
                    agent_name = action.get("agent")
                    if agent_name not in agent_outputs:
                        agent_outputs[agent_name] = []
                    agent_outputs[agent_name].append(action_result["output"])

            except Exception as e:
                logger.error(f"Error executing action {action_index}: {e}", exc_info=True)
                action_record.update({
                    "status": "failed",
                    "error": str(e),
                    "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time()))
                })

            executed_actions.append(action_record)

            # Small delay between actions to prevent overwhelming agents
            await asyncio.sleep(0.1)

        return {
            "executed_actions": executed_actions,
            "agent_outputs": agent_outputs
        }

    async def _execute_single_action(
        self,
        mission_id: str,
        action: Dict[str, Any],
        execution_id: str
    ) -> Dict[str, Any]:
        """
        Execute a single action by communicating with the appropriate specialist agent.

        This method ensures that NO LLM interpretation occurs during execution -
        it only performs predefined actions through established agent communication patterns.
        """
        agent_name = action.get("agent")
        action_kind = action.get("kind")
        parameters = action.get("parameters", {})

        logger.debug(
            f"Executing action '{action_kind}' on agent '{agent_name}' "
            f"for mission {mission_id}"
        )

        # Get the agent's HTTP endpoint
        agent_url = await self._get_agent_endpoint(agent_name)
        if not agent_url:
            raise ValueError(f"Could not determine endpoint for agent {agent_name}")

        # Prepare the execution request for the agent
        execution_payload = {
            "mission_id": mission_id,
            "execution_id": execution_id,
            "action_kind": action_kind,
            "parameters": parameters,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time()))
        }

        # Execute the action via HTTP call to specialist agent
        http_client = await self._get_http_client()
        try:
            response = await http_client.post(
                f"{agent_url}/execute",
                json=execution_payload,
                timeout=self.config.agent_action_timeout
            )
            response.raise_for_status()

            result_data = response.json()

            return {
                "status": "completed",
                "output": result_data.get("output", "Action completed successfully"),
                "details": result_data.get("details", {})
            }

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Agent {agent_name} returned HTTP {e.response.status_code}: {e.response.text}"
            )
            return {
                "status": "failed",
                "error": f"Agent returned HTTP {e.response.status_code}",
                "details": e.response.text
            }
        except httpx.RequestError as e:
            logger.error(f"Failed to communicate with agent {agent_name}: {e}")
            return {
                "status": "failed",
                "error": f"Communication failed: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error executing action on {agent_name}: {e}")
            return {
                "status": "failed",
                "error": f"Unexpected error: {str(e)}"
            }

    async def _get_agent_endpoint(self, agent_name: str) -> Optional[str]:
        """
        Get the HTTP endpoint for a specialist agent.

        In a production environment, this might consult a service registry
        or use Docker service discovery. For now, we use known patterns.
        """
        # Map agent names to their known service names in Docker Compose
        agent_service_map = {
            "project-strategist": "project-strategist",
            "devops-engineer": "devops-engineer",
            "database-architect": "database-architect",
            "backend-specialist": "backend-specialist",
            "frontend-specialist": "frontend-specialist",
            "qa-engineer": "qa-engineer",
            "security-engineer": "security-engineer",
            "system-architect": "system-architect",
            "tips-tricks-writer": "tips-tricks-writer",
            "hyper-split-agent": "hyper-split-agent",
            "session-snapshot": "session-snapshot",
            "throttle-agent": "throttle-agent",
            "agent-x": "agent-x",
            "goal-keeper": "goal-keeper",
            "coder": "coder",
            "coderabbit-webhook": "coderabbit-webhook",
            "brain": "brain",
            "broski-bot": "broski-bot",
            "broski-coo": "broski-coo",
            "agent-factory": "agent-factory",
            "hyper-auto-assistant": "hyper-auto-assistant",
            "crew-orchestrator": "crew-orchestrator",
            "safety-shepherd": "safety-shepherd",
            "fleet-controller": "fleet-controller",
            "hypercode-core": "hypercode-core",
            "hypercode-mcp-server": "hypercode-mcp-server"
        }

        service_name = agent_service_map.get(agent_name)
        if not service_name:
            logger.warning(f"Unknown agent name: {agent_name}")
            return None

        # Construct the URL - in Docker Compose, services are reachable by service name
        # Assuming agents listen on port 8080 internally (this should be made configurable)
        return f"http://{service_name}:8080"