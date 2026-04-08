from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import hashlib
import uuid

class EvolutionStatus(str, Enum):
    PROPOSED = "proposed"
    CODED = "coded"
    TESTED = "tested"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class ImprovementType(str, Enum):
    BUG_FIX = "bug_fix"
    PERFORMANCE = "performance"
    FEATURE = "feature"
    REFACTOR = "refactor"
    SECURITY = "security"

class ImprovementRequest(BaseModel):
    """
    Standard format for agents to request self-improvements.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for this evolution cycle")
    agent_id: str = Field(..., description="The ID of the agent making the request")
    target_agent: str = Field(..., description="The agent to be improved (e.g., 'coder-agent')")
    improvement_type: ImprovementType = Field(..., description="Type of improvement")
    description: str = Field(..., min_length=10, description="Detailed description of what is being improved and why")
    payload: Dict[str, Any] = Field(..., description="The actual improvement data (code, config, etc.)")
    priority: int = Field(default=1, ge=1, le=5, description="Priority level (1=Low, 5=Critical)")
    files_changed: List[str] = Field(default=[], description="List of files modified")
    test_results: Optional[Dict[str, Any]] = Field(None, description="Output from QA validation")
    status: EvolutionStatus = EvolutionStatus.PROPOSED
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="ISO 8601 timestamp")

    @field_validator('timestamp')
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Invalid ISO 8601 timestamp format")

    def generate_hash(self) -> str:
        """Generates a deterministic hash for deduplication"""
        content = f"{self.agent_id}:{self.target_agent}:{self.description}:{str(self.payload)}"
        return hashlib.sha256(content.encode()).hexdigest()

class DeploymentResult(BaseModel):
    request_id: str
    success: bool
    logs: str
    new_image_id: Optional[str] = None
