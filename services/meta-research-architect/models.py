"""
Data models for the Meta-Research Architect Agent.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

@dataclass
class ResearchFinding:
    """Represents a research finding from arXiv, blogs, etc."""
    id: str
    title: str
    authors: List[str]
    abstract: str
    source: str  # e.g., "arXiv", "blog", "awesome-repo"
    url: str
    published_at: datetime
    relevance_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    summary: Optional[str] = None

@dataclass
class GitHubInsight:
    """Represents an insight from GitHub repository scanning."""
    id: str
    repo: str
    finding_type: str  # e.g., "flaky_test", "security_issue", "performance"
    description: str
    severity: str  # e.g., "low", "medium", "high", "critical"
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggestion: Optional[str] = None
    confidence: float = 0.0

@dataclass
class OrchestrationSuggestion:
    """Represents a suggestion for tuning agent workflows."""
    id: str
    metric_type: str  # e.g., "error_rate", "latency", "oom"
    current_value: float
    threshold: float
    suggestion: str
    confidence: float = 0.0
    proposed_changes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExplanationChunk:
    """Represents a chunk of explanation for neurodivergent users."""
    id: str
    topic: str
    content: str
    complexity_level: str  # e.g., "beginner", "intermediate", "advanced"
    focus_tools: List[str] = field(default_factory=list)
    pet_feedback: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class MetaAgentAction:
    """Represents an action the meta-agent can take."""
    id: str
    action_type: str  # e.g., "research", "github_analysis", "orchestration_tune", "explanation"
    priority: str  # e.g., "low", "medium", "high"
    status: str  # e.g., "pending", "in_progress", "completed", "failed"
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None