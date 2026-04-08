from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel

class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator"
    CODER = "coder-agent"
    ARCHITECT = "system-architect"
    FRONTEND = "frontend-specialist"
    BACKEND = "backend-specialist"
    QA = "qa-engineer"
    DEVOPS = "devops-engineer"
    SECURITY = "security-engineer"
    STRATEGIST = "project-strategist"

class EvaluationMethod(str, Enum):
    EXACT_MATCH = "exact_match"
    CONTAINS = "contains"
    REGEX = "regex"
    STATUS_CODE = "status_code"
    JSON_SCHEMA = "json_schema"
    LLM_EVAL = "llm_eval"  # Use an LLM to judge the response

class EvaluationCriteria(BaseModel):
    method: EvaluationMethod
    value: Any  # The expected value, regex pattern, or LLM prompt
    weight: float = 1.0
    description: Optional[str] = None

class TestCase(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    agent: AgentType
    endpoint: str = "/execute"  # Default endpoint to hit
    method: str = "POST"
    payload: Dict[str, Any]
    headers: Dict[str, str] = {}
    expected_results: List[EvaluationCriteria]
    timeout: int = 30
    tags: List[str] = []

class TestScenario(BaseModel):
    id: str
    name: str
    description: str
    cases: List[TestCase]
    metadata: Dict[str, Any] = {}

class TestResult(BaseModel):
    case_id: str
    scenario_id: str
    success: bool
    score: float
    duration_ms: float
    response_data: Any
    errors: List[str] = []
    logs: List[str] = []

class ScenarioResult(BaseModel):
    scenario_id: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    total_duration_ms: float
    results: List[TestResult]
    overall_score: float
