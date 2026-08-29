# agents/mission-executor/models.py
"""
Data models for mission-executor service.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """Status of mission execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ExecutionRequest(BaseModel):
    """Request to execute a mission plan."""
    mission_id: str = Field(..., description="Unique mission identifier")
    goal: str = Field(..., description="Original human goal")
    plan: Dict[str, Any] = Field(..., description="Mission plan to execute")
    requested_at: Optional[str] = Field(None, description="Timestamp when request was made")

    class Config:
        json_schema_extra = {
            "example": {
                "mission_id": "miss_123abc",
                "goal": "Set up a PostgreSQL database for the web application",
                "plan": {
                    "requested_actions": [
                        {
                            "kind": "run_command",
                            "command": "apt-get update && apt-get install -y postgresql",
                            "agent": "devops-engineer"
                        },
                        {
                            "kind": "create_database",
                            "database_name": "webapp_db",
                            "agent": "database-architect"
                        }
                    ]
                },
                "requested_at": "2026-08-28T18:00:00Z"
            }
        }


class ExecutionResult(BaseModel):
    """Result of mission execution."""
    mission_id: str = Field(..., description="Unique mission identifier")
    status: ExecutionStatus = Field(..., description="Execution status")
    started_at: Optional[str] = Field(None, description="Timestamp when execution started")
    completed_at: Optional[str] = Field(None, description="Timestamp when execution completed")
    error_message: Optional[str] = Field(None, description="Error message if execution failed")
    executed_actions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of actions that were executed"
    )
    agent_outputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Outputs from specialist agents"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "mission_id": "miss_123abc",
                "status": "completed",
                "started_at": "2026-08-28T18:00:05Z",
                "completed_at": "2026-08-28T18:02:30Z",
                "error_message": None,
                "executed_actions": [
                    {
                        "action": "install_postgresql",
                        "agent": "devops-engineer",
                        "status": "completed"
                    },
                    {
                        "action": "create_database",
                        "agent": "database-architect",
                        "status": "completed"
                    }
                ],
                "agent_outputs": {
                    "devops-engineer": "PostgreSQL 14 installed successfully",
                    "database-architect": "Database 'webapp_db' created"
                }
            }
        }
    )


class AgentDelegatorConfig(BaseModel):
    """Configuration for agent delegator."""
    # Timeout for individual agent actions (seconds)
    agent_action_timeout: int = Field(30, description="Timeout for individual agent actions")

    # Maximum number of concurrent agent actions
    max_concurrent_actions: int = Field(5, description="Maximum concurrent agent actions")

    # Retry configuration
    max_retries: int = Field(3, description="Maximum retries for failed actions")
    retry_delay: int = Field(2, description="Delay between retries (seconds)")

    # Resource limits
    max_execution_time: int = Field(300, description="Maximum total execution time (seconds)")

    class Config:
        json_schema_extra = {
            "example": {
                "agent_action_timeout": 30,
                "max_concurrent_actions": 5,
                "max_retries": 3,
                "retry_delay": 2,
                "max_execution_time": 300
            }
        }