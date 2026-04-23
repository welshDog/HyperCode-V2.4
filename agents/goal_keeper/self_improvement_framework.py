"""
🦅 SELF-IMPROVING AGENT SYSTEM FRAMEWORK
Autonomous capability evolution, performance optimization, and emergent learning

Author: Gordon (Docker AI)
Date: 2026-04-22
Version: 1.0

Architecture:
- GoalKeeper: Strategic improvement orchestration
- Metrics Engine: Real-time performance tracking
- Learning Loop: Feedback → improvement → validation
- Skill Registry: Capability discovery & evolution
- System Optimization: Cross-agent improvement
- A/B Testing: Decision validation
- Failure Pattern Learning: Automatic debugging
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
import structlog
from collections import defaultdict, deque
import random

logger = structlog.get_logger()

def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return str(value)


def _safe_json_dumps(payload: Any) -> str:
    return json.dumps(payload, default=_json_default, ensure_ascii=False)


def _parse_datetime(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw)
        except Exception:
            return datetime.now()
    return datetime.now()


# ============================================================================
# CORE DATA MODELS
# ============================================================================

class AgentRole(str, Enum):
    """Agent role types"""
    ORCHESTRATOR = "orchestrator"
    SPECIALIST = "specialist"
    VALIDATOR = "validator"
    HEALER = "healer"
    GOAL_KEEPER = "goal_keeper"


class ImprovementType(str, Enum):
    """Types of improvements agents can make"""
    PERFORMANCE = "performance"  # Speed/efficiency
    QUALITY = "quality"  # Accuracy/correctness
    COST = "cost"  # Resource efficiency
    CAPABILITY = "capability"  # New features
    RELIABILITY = "reliability"  # Stability/recovery
    SCALABILITY = "scalability"  # Handle more load


class MetricLevel(str, Enum):
    """Metric hierarchy"""
    SYSTEM = "system"  # All agents
    TEAM = "team"  # Agent team
    INDIVIDUAL = "individual"  # Single agent
    TASK = "task"  # Single task


@dataclass
class AgentMetrics:
    """Metrics for a single agent"""
    agent_name: str
    role: str
    
    # Performance
    avg_task_duration_ms: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    success_rate: float = 1.0
    
    # Quality
    avg_quality_score: float = 0.0  # 0-100
    user_satisfaction: float = 0.0
    errors_per_task: float = 0.0
    
    # Resource
    avg_memory_mb: float = 0.0
    avg_cpu_percent: float = 0.0
    peak_memory_mb: float = 0.0
    
    # Cost (LLM API)
    total_cost_usd: float = 0.0
    cost_per_task_usd: float = 0.0
    
    # Time window
    window_start: datetime = field(default_factory=datetime.now)
    window_end: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=1))
    
    # Improvement tracking
    improvements_made: int = 0
    improvements_pending: List[str] = field(default_factory=list)


@dataclass
class SystemMetrics:
    """Metrics across all agents"""
    timestamp: datetime
    
    # Throughput
    total_tasks: int
    total_completed: int
    total_failed: int
    tasks_per_minute: float
    
    # Quality
    overall_success_rate: float
    avg_quality_score: float
    
    # Resource
    total_memory_mb: float
    total_cpu_percent: float
    
    # Cost
    total_cost_usd: float
    
    # Team health
    healthy_agents: int
    degraded_agents: int
    failed_agents: int
    
    # Improvement velocity
    improvements_completed_this_hour: int
    improvements_pending: int


@dataclass
class ImprovementProposal:
    """Proposed improvement to an agent"""
    proposal_id: str
    agent_name: str
    improvement_type: ImprovementType
    description: str
    expected_impact: Dict[str, float]  # metric_name -> expected_change_percent
    
    implementation_plan: List[str]
    estimated_effort_hours: float
    risk_level: str  # low, medium, high
    
    created_at: datetime
    proposed_by: str  # Agent that proposed improvement
    status: str  # pending, approved, in_progress, completed, failed
    
    # A/B testing
    control_group_size: int = 0
    test_group_size: int = 0
    control_agents: List[str] = field(default_factory=list)
    test_agents: List[str] = field(default_factory=list)
    baseline_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    current_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    statistical_significance: Optional[float] = None  # p-value


@dataclass
class FailurePattern:
    """Detected pattern of failures"""
    pattern_id: str
    agent_name: str
    task_type: str
    
    frequency: int  # How many times seen
    last_seen: datetime
    
    symptoms: List[str]  # What the failures look like
    root_causes: List[str]  # Identified causes
    
    # Recovery
    recovery_successful: bool
    recovery_strategy: Optional[str]
    recovery_success_rate: float = 0.0
    
    # Prevention
    prevention_strategy: Optional[str] = None
    automated_prevention_enabled: bool = False


@dataclass
class SkillDefinition:
    """Definition of an agent skill/capability"""
    skill_id: str
    name: str
    agent_name: str
    category: str  # technical, communication, reasoning, etc.
    
    description: str
    examples: List[str]
    
    # Proficiency
    proficiency_level: str  # beginner, intermediate, advanced, expert
    confidence: float  # 0-1
    
    # Learning
    times_used: int = 0
    success_rate: float = 1.0
    last_improved: Optional[datetime] = None
    improvement_suggestions: List[str] = field(default_factory=list)


# ============================================================================
# METRICS ENGINE
# ============================================================================

class MetricsEngine:
    """
    Real-time performance tracking for all agents.
    Emits alerts when metrics deviate from baseline.
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.system_metrics_history: deque[Dict[str, Any]] = deque(maxlen=1000)
        self.baseline_metrics: Dict[str, Dict[str, float]] = {}
        self._last_system_total_tasks: int = 0
        self._last_system_timestamp: datetime | None = None
        self.metric_thresholds = {
            "success_rate": {"min": 0.95, "max": 1.0},
            "quality_score": {"min": 80.0},
            "error_rate": {"max": 0.05},
            "cost_per_task": {"max": 0.5},
        }
    
    async def record_task_completion(
        self,
        agent_name: str,
        task_duration_ms: float,
        quality_score: float = 100.0,
        cost_usd: float = 0.0,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Record a completed task"""
        if agent_name not in self.agent_metrics:
            self.agent_metrics[agent_name] = AgentMetrics(
                agent_name=agent_name,
                role="unknown"
            )
        
        metrics = self.agent_metrics[agent_name]
        
        # Update counts
        metrics.tasks_completed += (1 if success else 0)
        metrics.tasks_failed += (0 if success else 1)
        
        # Update averages
        total = metrics.tasks_completed + metrics.tasks_failed
        metrics.success_rate = metrics.tasks_completed / total if total > 0 else 0
        
        # Running average for duration
        metrics.avg_task_duration_ms = (
            (metrics.avg_task_duration_ms * (total - 1) + task_duration_ms) / total
        )
        
        # Running average for quality
        metrics.avg_quality_score = (
            (metrics.avg_quality_score * (total - 1) + quality_score) / total
        )
        
        # Cost tracking
        metrics.total_cost_usd += cost_usd
        metrics.cost_per_task_usd = metrics.total_cost_usd / metrics.tasks_completed if metrics.tasks_completed > 0 else 0
        
        # Store in Redis
        await self.redis.set(f"metrics:{agent_name}", _safe_json_dumps(asdict(metrics)))
        
        # Check for threshold breaches
        await self._check_metric_thresholds(agent_name, metrics)
    
    async def record_resource_usage(
        self,
        agent_name: str,
        memory_mb: float,
        cpu_percent: float
    ):
        """Record resource usage"""
        if agent_name not in self.agent_metrics:
            return
        
        metrics = self.agent_metrics[agent_name]
        metrics.avg_memory_mb = (metrics.avg_memory_mb + memory_mb) / 2
        metrics.avg_cpu_percent = (metrics.avg_cpu_percent + cpu_percent) / 2
        
        if memory_mb > metrics.peak_memory_mb:
            metrics.peak_memory_mb = memory_mb
        await self.redis.set(f"metrics:{agent_name}", _safe_json_dumps(asdict(metrics)))
    
    async def _check_metric_thresholds(self, agent_name: str, metrics: AgentMetrics):
        """Check if metrics breach thresholds"""
        breaches = []
        
        if metrics.success_rate < self.metric_thresholds["success_rate"]["min"]:
            breaches.append({
                "metric": "success_rate",
                "value": metrics.success_rate,
                "threshold": self.metric_thresholds["success_rate"]["min"],
                "severity": "high"
            })
        
        if metrics.avg_quality_score < self.metric_thresholds["quality_score"]["min"]:
            breaches.append({
                "metric": "quality_score",
                "value": metrics.avg_quality_score,
                "threshold": self.metric_thresholds["quality_score"]["min"],
                "severity": "medium"
            })
        
        if breaches:
            logger.info(
                "metric_threshold_breached",
                agent=agent_name,
                breaches=breaches
            )
            await self.redis.xadd(
                "goal_keeper:events",
                {
                    "data": _safe_json_dumps(
                        {
                            "event": "metric_threshold_breached",
                            "agent": agent_name,
                            "timestamp": datetime.now().isoformat(),
                            "breaches": breaches,
                        }
                    )
                },
                maxlen=1000,
                approximate=True,
            )
            
            # Trigger improvement proposal
            for breach in breaches:
                await self.redis.lpush(
                    "improvement_triggers",
                    json.dumps({
                        "agent": agent_name,
                        "trigger_type": "metric_breach",
                        "breach": breach,
                        "timestamp": datetime.now().isoformat()
                    })
                )
    
    async def get_agent_metrics(self, agent_name: str) -> Optional[AgentMetrics]:
        """Get current metrics for an agent"""
        if agent_name in self.agent_metrics:
            return self.agent_metrics[agent_name]
        raw = await self.redis.get(f"metrics:{agent_name}")
        if not raw:
            return None
        try:
            payload = json.loads(raw)
            payload["window_start"] = _parse_datetime(payload.get("window_start"))
            payload["window_end"] = _parse_datetime(payload.get("window_end"))
            metrics = AgentMetrics(**payload)
            self.agent_metrics[agent_name] = metrics
            return metrics
        except Exception:
            return None
    
    async def get_system_metrics(self) -> SystemMetrics:
        """Calculate system-wide metrics"""
        total_tasks = sum(m.tasks_completed + m.tasks_failed for m in self.agent_metrics.values())
        total_completed = sum(m.tasks_completed for m in self.agent_metrics.values())
        total_failed = sum(m.tasks_failed for m in self.agent_metrics.values())
        now = datetime.now()
        tasks_per_minute = 0.0
        if self._last_system_timestamp is not None:
            delta_tasks = total_tasks - self._last_system_total_tasks
            delta_seconds = max(1.0, (now - self._last_system_timestamp).total_seconds())
            tasks_per_minute = (delta_tasks / delta_seconds) * 60.0
        self._last_system_total_tasks = total_tasks
        self._last_system_timestamp = now
        
        overall_success = total_completed / total_tasks if total_tasks > 0 else 1.0
        avg_quality = sum(m.avg_quality_score for m in self.agent_metrics.values()) / max(1, len(self.agent_metrics))
        
        # Count healthy/degraded agents
        healthy = sum(1 for m in self.agent_metrics.values() if m.success_rate > 0.95)
        degraded = sum(1 for m in self.agent_metrics.values() if 0.85 <= m.success_rate <= 0.95)
        failed = sum(1 for m in self.agent_metrics.values() if m.success_rate < 0.85)
        
        metrics = SystemMetrics(
            timestamp=datetime.now(),
            total_tasks=total_tasks,
            total_completed=total_completed,
            total_failed=total_failed,
            tasks_per_minute=tasks_per_minute,
            overall_success_rate=overall_success,
            avg_quality_score=avg_quality,
            total_memory_mb=sum(m.avg_memory_mb for m in self.agent_metrics.values()),
            total_cpu_percent=sum(m.avg_cpu_percent for m in self.agent_metrics.values()),
            total_cost_usd=sum(m.total_cost_usd for m in self.agent_metrics.values()),
            healthy_agents=healthy,
            degraded_agents=degraded,
            failed_agents=failed,
            improvements_completed_this_hour=0,  # Computed elsewhere
            improvements_pending=0  # Computed elsewhere
        )
        
        self.system_metrics_history.append(asdict(metrics))
        return metrics


# ============================================================================
# SKILL REGISTRY
# ============================================================================

class SkillRegistry:
    """
    Discover, track, and evolve agent skills.
    Agents can learn new skills or improve existing ones.
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.skills: Dict[str, Dict[str, SkillDefinition]] = defaultdict(dict)
    
    async def register_skill(self, skill: SkillDefinition):
        """Register a skill for an agent"""
        if skill.agent_name not in self.skills:
            self.skills[skill.agent_name] = {}
        
        self.skills[skill.agent_name][skill.skill_id] = skill
        
        await self.redis.hset(
            f"skills:{skill.agent_name}",
            skill.skill_id,
            json.dumps(asdict(skill), default=str)
        )
        
        logger.info("skill_registered", skill=skill.skill_id, agent=skill.agent_name)
    
    async def record_skill_usage(self, agent_name: str, skill_id: str, success: bool):
        """Record usage of a skill"""
        if agent_name not in self.skills or skill_id not in self.skills[agent_name]:
            return
        
        skill = self.skills[agent_name][skill_id]
        skill.times_used += 1
        
        # Update success rate
        total = skill.times_used
        skill.success_rate = (skill.success_rate * (total - 1) + (1 if success else 0)) / total
        
        await self.redis.hset(
            f"skills:{agent_name}",
            skill_id,
            json.dumps(asdict(skill), default=str)
        )
    
    async def discover_emergent_skills(self, agent_name: str) -> List[SkillDefinition]:
        """
        Analyze agent's recent work to detect new emergent skills.
        This is how agents evolve beyond their initial capabilities.
        """
        # Get recent task history
        recent_tasks = await self.redis.lrange(f"tasks:{agent_name}", 0, 100)
        
        emergent = []
        
        # Analyze patterns in task execution
        task_categories = defaultdict(int)
        for task_json in recent_tasks:
            task = json.loads(task_json)
            category = task.get("category", "unknown")
            task_categories[category] += 1
        
        # If agent frequently tackles new categories, register as emergent skills
        for category, count in task_categories.items():
            if count > 5:  # Threshold: used >5 times
                skill_id = f"emergent_{category}_{int(time.time())}"
                skill = SkillDefinition(
                    skill_id=skill_id,
                    name=f"Emergent: {category}",
                    agent_name=agent_name,
                    category=category,
                    description=f"Skill automatically detected from task patterns",
                    examples=[],
                    proficiency_level="beginner",
                    confidence=0.7,
                    times_used=count,
                    success_rate=0.8  # Estimated
                )
                emergent.append(skill)
                await self.register_skill(skill)
        
        return emergent
    
    async def get_agent_skills(self, agent_name: str) -> List[SkillDefinition]:
        """Get all skills for an agent"""
        return list(self.skills.get(agent_name, {}).values())


# ============================================================================
# FAILURE PATTERN LEARNING
# ============================================================================

class FailurePatternDetector:
    """
    Detect recurring failure patterns and automatically suggest fixes.
    Learns from failures across all agents to prevent future issues.
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.failure_patterns: Dict[str, FailurePattern] = {}
        self.failure_history: deque[Dict[str, Any]]  = deque(maxlen=10000)
    
    async def record_failure(
        self,
        agent_name: str,
        task_type: str,
        error_message: str,
        context: Dict[str, Any]
    ):
        """Record a failure"""
        self.failure_history.append({
            "agent": agent_name,
            "task_type": task_type,
            "error": error_message,
            "context": context,
            "timestamp": datetime.now()
        })
        
        # Check for pattern
        pattern = await self._detect_pattern(agent_name, task_type, error_message)
        
        if pattern:
            logger.info(
                "failure_pattern_detected",
                pattern_id=pattern.pattern_id,
                frequency=pattern.frequency
            )
    
    async def _detect_pattern(
        self,
        agent_name: str,
        task_type: str,
        error_message: str
    ) -> Optional[FailurePattern]:
        """Detect if this failure is part of a pattern"""
        pattern_key = f"{agent_name}:{task_type}"
        
        # Count recent similar failures
        recent_failures = [
            f for f in self.failure_history
            if f["agent"] == agent_name and f["task_type"] == task_type
        ]
        
        if len(recent_failures) >= 3:  # Pattern threshold: 3+ failures
            if pattern_key not in self.failure_patterns:
                self.failure_patterns[pattern_key] = FailurePattern(
                    pattern_id=hashlib.md5(f"{agent_name}{task_type}".encode()).hexdigest(),
                    agent_name=agent_name,
                    task_type=task_type,
                    frequency=len(recent_failures),
                    last_seen=datetime.now(),
                    symptoms=list(set(f["error"] for f in recent_failures)),
                    root_causes=[],
                    recovery_successful=False,
                    recovery_strategy=None
                )
            
            pattern = self.failure_patterns[pattern_key]
            pattern.frequency = len(recent_failures)
            pattern.last_seen = datetime.now()
            
            return pattern
        
        return None
    
    async def get_failure_pattern(self, agent_name: str, task_type: str) -> Optional[FailurePattern]:
        """Get pattern info for debugging"""
        key = f"{agent_name}:{task_type}"
        return self.failure_patterns.get(key)
    
    async def suggest_prevention_strategy(
        self,
        pattern: FailurePattern
    ) -> str:
        """Suggest how to prevent this pattern"""
        # In production, this would use LLM reasoning
        strategies = {
            "timeout": "Increase timeout limit, add early detection",
            "memory": "Optimize memory usage, add garbage collection",
            "network": "Add retry logic with exponential backoff",
            "validation": "Add input validation earlier in pipeline",
            "dependency": "Add dependency health checks",
        }
        
        for symptom in pattern.symptoms:
            for keyword, strategy in strategies.items():
                if keyword in symptom.lower():
                    return strategy
        
        return "Enable detailed logging and retry with monitoring"


# ============================================================================
# A/B TESTING FRAMEWORK
# ============================================================================

class ABTestingFramework:
    """
    Test proposed improvements on subset of agents before rollout.
    Uses statistical testing to validate improvements.
    """
    
    def __init__(self, redis_client, metrics_engine: MetricsEngine):
        self.redis = redis_client
        self.metrics = metrics_engine
        self.active_tests: Dict[str, ImprovementProposal] = {}
    
    async def start_ab_test(
        self,
        proposal: ImprovementProposal,
        control_agents: List[str],
        test_agents: List[str]
    ) -> str:
        """Start A/B test of improvement"""
        proposal.control_group_size = len(control_agents)
        proposal.test_group_size = len(test_agents)
        proposal.control_agents = list(control_agents)
        proposal.test_agents = list(test_agents)
        proposal.status = "in_progress"
        
        # Capture baseline metrics
        for agent in control_agents + test_agents:
            metrics = await self.metrics.get_agent_metrics(agent)
            if metrics:
                proposal.baseline_metrics[agent] = {
                    "quality": metrics.avg_quality_score,
                    "duration": metrics.avg_task_duration_ms,
                    "cost": metrics.cost_per_task_usd
                }
        
        self.active_tests[proposal.proposal_id] = proposal
        
        await self.redis.hset(
            "ab_tests",
            proposal.proposal_id,
            _safe_json_dumps(asdict(proposal))
        )
        
        logger.info(
            "ab_test_started",
            proposal_id=proposal.proposal_id,
            control_size=len(control_agents),
            test_size=len(test_agents)
        )
        
        return proposal.proposal_id
    
    async def record_ab_test_result(
        self,
        proposal_id: str,
        agent_name: str,
        metrics: Dict[str, float]
    ):
        """Record test result for an agent"""
        if proposal_id not in self.active_tests:
            return
        
        proposal = self.active_tests[proposal_id]
        proposal.current_metrics[agent_name] = metrics
    
    async def evaluate_ab_test(self, proposal_id: str, p_value_threshold: float = 0.05) -> Tuple[bool, float]:
        """
        Evaluate if test shows statistically significant improvement.
        Returns (success: bool, p_value: float)
        """
        if proposal_id not in self.active_tests:
            return False, 1.0
        
        proposal = self.active_tests[proposal_id]
        
        metric_name = "quality"
        if proposal.expected_impact:
            metric_name = next(iter(proposal.expected_impact.keys()))

        direction = 1.0
        if metric_name in {"duration", "cost"}:
            direction = -1.0

        async def _current_snapshot(agent: str) -> Optional[Dict[str, float]]:
            metrics = await self.metrics.get_agent_metrics(agent)
            if not metrics:
                return None
            return {
                "quality": metrics.avg_quality_score,
                "duration": metrics.avg_task_duration_ms,
                "cost": metrics.cost_per_task_usd,
            }

        control_values: list[float] = []
        test_values: list[float] = []
        for agent in proposal.control_agents:
            baseline = proposal.baseline_metrics.get(agent)
            current = await _current_snapshot(agent)
            if not baseline or not current:
                continue
            proposal.current_metrics[agent] = current
            denom = baseline.get(metric_name, 0.0) or 1.0
            delta = (current.get(metric_name, denom) - denom) / denom
            control_values.append(delta * direction)

        for agent in proposal.test_agents:
            baseline = proposal.baseline_metrics.get(agent)
            current = await _current_snapshot(agent)
            if not baseline or not current:
                continue
            proposal.current_metrics[agent] = current
            denom = baseline.get(metric_name, 0.0) or 1.0
            delta = (current.get(metric_name, denom) - denom) / denom
            test_values.append(delta * direction)

        if not control_values or not test_values:
            return False, 1.0

        observed = (sum(test_values) / len(test_values)) - (sum(control_values) / len(control_values))
        if observed <= 0:
            return False, 1.0

        combined = control_values + test_values
        control_n = len(control_values)
        test_n = len(test_values)
        seed = int(hashlib.md5(proposal_id.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        permutations = 2000 if len(combined) <= 20 else 1000
        count = 0
        for _ in range(permutations):
            rng.shuffle(combined)
            c = combined[:control_n]
            t = combined[control_n : control_n + test_n]
            diff = (sum(t) / len(t)) - (sum(c) / len(c))
            if diff >= observed:
                count += 1
        p_value = (count + 1) / (permutations + 1)
        return p_value < p_value_threshold, p_value


# ============================================================================
# IMPROVEMENT PROPOSAL ENGINE
# ============================================================================

class ImprovementProposalEngine:
    """
    Generate and manage improvement proposals.
    Agents can propose improvements to themselves or peers.
    """
    
    def __init__(self, redis_client, metrics_engine: MetricsEngine):
        self.redis = redis_client
        self.metrics = metrics_engine
        self.proposals: Dict[str, ImprovementProposal] = {}
    
    async def propose_improvement(
        self,
        agent_name: str,
        improvement_type: ImprovementType,
        description: str,
        expected_impact: Dict[str, float],
        implementation_plan: List[str],
        estimated_effort_hours: float = 1.0,
        risk_level: str = "low"
    ) -> str:
        """Propose an improvement"""
        proposal_id = hashlib.md5(
            f"{agent_name}{improvement_type}{time.time()}".encode()
        ).hexdigest()
        
        proposal = ImprovementProposal(
            proposal_id=proposal_id,
            agent_name=agent_name,
            improvement_type=improvement_type,
            description=description,
            expected_impact=expected_impact,
            implementation_plan=implementation_plan,
            estimated_effort_hours=estimated_effort_hours,
            risk_level=risk_level,
            created_at=datetime.now(),
            proposed_by="system",
            status="pending"
        )
        
        self.proposals[proposal_id] = proposal
        
        await self.redis.lpush(
            "improvement_proposals",
            _safe_json_dumps(asdict(proposal))
        )
        await self.redis.xadd(
            "goal_keeper:events",
            {
                "data": _safe_json_dumps(
                    {
                        "event": "improvement_proposed",
                        "agent": agent_name,
                        "proposal_id": proposal_id,
                        "improvement_type": improvement_type.value,
                        "risk_level": risk_level,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            },
            maxlen=1000,
            approximate=True,
        )
        
        logger.info(
            "improvement_proposed",
            proposal_id=proposal_id,
            agent=agent_name,
            type=improvement_type
        )
        
        return proposal_id
    
    async def auto_approve_low_risk(self, proposal: ImprovementProposal) -> bool:
        """Auto-approve low-risk improvements without user input"""
        impact_score = sum(abs(v) for v in proposal.expected_impact.values())
        if (
            proposal.risk_level == "low" and
            proposal.estimated_effort_hours < 0.5 and
            impact_score > 0
        ):
            proposal.status = "approved"
            return True
        
        return False


# ============================================================================
# GOAL KEEPER AGENT (THE ORCHESTRATOR)
# ============================================================================

class GoalKeeper:
    """
    Master orchestrator for agent self-improvement.
    
    Responsibilities:
    - Monitor all agent metrics
    - Detect improvement opportunities
    - Prioritize improvements
    - Orchestrate A/B tests
    - Learn from failures
    - Trigger system optimizations
    - Track evolution of agent capabilities
    """
    
    def __init__(
        self,
        redis_client,
        agent_registry: Dict[str, Any]
    ):
        self.redis = redis_client
        self.agents = agent_registry
        
        self.metrics_engine = MetricsEngine(redis_client)
        self.skill_registry = SkillRegistry(redis_client)
        self.failure_detector = FailurePatternDetector(redis_client)
        self.ab_testing = ABTestingFramework(redis_client, self.metrics_engine)
        self.proposal_engine = ImprovementProposalEngine(redis_client, self.metrics_engine)
        
        self.improvement_queue: List[ImprovementProposal] = []
        self._failure_cursor: int = 0
        self._tasks: list[asyncio.Task[None]] = []
        self.running = False
    
    async def start(self):
        """Start the GoalKeeper monitoring loop"""
        self.running = True
        
        logger.info("goal_keeper_started")
        await self.redis.xadd(
            "goal_keeper:events",
            {"data": _safe_json_dumps({"event": "goal_keeper_started", "timestamp": datetime.now().isoformat()})},
            maxlen=1000,
            approximate=True,
        )
        self._tasks = [
            asyncio.create_task(self._monitor_metrics_loop()),
            asyncio.create_task(self._detect_improvements_loop()),
            asyncio.create_task(self._execute_improvements_loop()),
            asyncio.create_task(self._learn_from_failures_loop()),
            asyncio.create_task(self._discover_emergent_skills_loop()),
        ]
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            raise
        finally:
            for task in self._tasks:
                task.cancel()
            for task in self._tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    
    async def _monitor_metrics_loop(self):
        """Continuously monitor agent metrics"""
        while self.running:
            try:
                system_metrics = await self.metrics_engine.get_system_metrics()
                
                logger.info(
                    "system_metrics_update",
                    success_rate=system_metrics.overall_success_rate,
                    healthy_agents=system_metrics.healthy_agents,
                    total_cost=system_metrics.total_cost_usd
                )
                
                # Check system health
                if system_metrics.overall_success_rate < 0.9:
                    logger.info("system_health_degraded", severity="high")
                    await self._trigger_emergency_optimization()
                
                await asyncio.sleep(60)  # Check every minute
            
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error("metrics_loop_error", error=str(e))
    
    async def _detect_improvements_loop(self):
        """Detect opportunities for improvement"""
        while self.running:
            try:
                for agent_name, agent_metrics in self.metrics_engine.agent_metrics.items():
                    improvements = await self._analyze_agent_for_improvements(agent_name, agent_metrics)
                    
                    for improvement in improvements:
                        proposal_id = await self.proposal_engine.propose_improvement(
                            agent_name=agent_name,
                            improvement_type=improvement["type"],
                            description=improvement["description"],
                            expected_impact=improvement["expected_impact"],
                            implementation_plan=improvement["plan"],
                            estimated_effort_hours=improvement["effort"],
                            risk_level=improvement["risk"]
                        )
                        
                        self.improvement_queue.append(
                            self.proposal_engine.proposals[proposal_id]
                        )
                
                await asyncio.sleep(300)  # Check every 5 minutes
            
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error("improvement_detection_error", error=str(e))
    
    async def _analyze_agent_for_improvements(
        self,
        agent_name: str,
        metrics: AgentMetrics
    ) -> List[Dict[str, Any]]:
        """Analyze metrics to find improvement opportunities"""
        improvements = []
        
        # Slow execution
        if metrics.avg_task_duration_ms > 5000:  # >5 seconds
            improvements.append({
                "type": ImprovementType.PERFORMANCE,
                "description": f"Optimize {agent_name} execution speed (currently {metrics.avg_task_duration_ms:.0f}ms)",
                "expected_impact": {"duration": -0.2},  # 20% faster
                "plan": [
                    "Profile current execution",
                    "Identify bottlenecks",
                    "Implement caching",
                    "Optimize API calls"
                ],
                "effort": 2.0,
                "risk": "low"
            })
        
        # Low quality
        if metrics.avg_quality_score < 85:
            improvements.append({
                "type": ImprovementType.QUALITY,
                "description": f"Improve {agent_name} output quality (currently {metrics.avg_quality_score:.1f}%)",
                "expected_impact": {"quality": 0.15},  # 15% improvement
                "plan": [
                    "Review recent failures",
                    "Add validation",
                    "Improve prompt engineering",
                    "Add post-processing"
                ],
                "effort": 3.0,
                "risk": "medium"
            })
        
        # High cost
        if metrics.cost_per_task_usd > 0.1:
            improvements.append({
                "type": ImprovementType.COST,
                "description": f"Reduce {agent_name} API costs (currently ${metrics.cost_per_task_usd:.3f}/task)",
                "expected_impact": {"cost": -0.3},  # 30% cheaper
                "plan": [
                    "Use cheaper models",
                    "Reduce token usage",
                    "Add response caching",
                    "Batch requests"
                ],
                "effort": 1.5,
                "risk": "low"
            })
        
        return improvements
    
    async def _execute_improvements_loop(self):
        """Execute approved improvements"""
        while self.running:
            try:
                if self.improvement_queue:
                    # Sort by impact/effort ratio
                    self.improvement_queue.sort(
                        key=lambda p: sum(abs(v) for v in p.expected_impact.values()) / max(p.estimated_effort_hours, 0.1),
                        reverse=True
                    )
                    
                    proposal = self.improvement_queue[0]
                    
                    # Auto-approve low-risk
                    if await self.proposal_engine.auto_approve_low_risk(proposal):
                        await self._execute_improvement(proposal)
                        self.improvement_queue.pop(0)
                
                await asyncio.sleep(10)
            
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error("improvement_execution_error", error=str(e))
    
    async def _execute_improvement(self, proposal: ImprovementProposal):
        """Execute a specific improvement"""
        logger.info(
            "executing_improvement",
            proposal_id=proposal.proposal_id,
            agent=proposal.agent_name,
            description=proposal.description
        )
        await self.redis.xadd(
            "goal_keeper:events",
            {
                "data": _safe_json_dumps(
                    {
                        "event": "improvement_execution_started",
                        "proposal_id": proposal.proposal_id,
                        "agent": proposal.agent_name,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            },
            maxlen=1000,
            approximate=True,
        )
        
        try:
            # Run A/B test
            test_agents = [proposal.agent_name]  # Simplified
            control_agents = [
                name for name in self.agents.keys()
                if name.startswith(proposal.agent_name.split("-")[0])
                and name != proposal.agent_name
            ][:2]  # Use 2 control agents
            
            test_id = await self.ab_testing.start_ab_test(
                proposal,
                control_agents,
                test_agents
            )
            
            # Wait for test results
            await asyncio.sleep(60)
            
            success, p_value = await self.ab_testing.evaluate_ab_test(test_id)
            
            if success:
                proposal.status = "completed"
                proposal.statistical_significance = p_value
                
                logger.info(
                    "improvement_successful",
                    proposal_id=proposal.proposal_id,
                    p_value=p_value
                )
                await self.redis.xadd(
                    "goal_keeper:events",
                    {
                        "data": _safe_json_dumps(
                            {
                                "event": "improvement_completed",
                                "proposal_id": proposal.proposal_id,
                                "agent": proposal.agent_name,
                                "p_value": p_value,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    },
                    maxlen=1000,
                    approximate=True,
                )
            else:
                proposal.status = "failed"
                
                logger.info(
                    "improvement_failed",
                    proposal_id=proposal.proposal_id,
                    reason="A/B test inconclusive"
                )
                await self.redis.xadd(
                    "goal_keeper:events",
                    {
                        "data": _safe_json_dumps(
                            {
                                "event": "improvement_failed",
                                "proposal_id": proposal.proposal_id,
                                "agent": proposal.agent_name,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    },
                    maxlen=1000,
                    approximate=True,
                )
        
        except asyncio.CancelledError:
            proposal.status = "failed"
            raise
        except Exception as e:
            proposal.status = "failed"
            logger.error("improvement_execution_failed", error=str(e))
    
    async def _learn_from_failures_loop(self):
        """Learn from failures and prevent recurrence"""
        while self.running:
            try:
                failures = list(self.failure_detector.failure_history)
                new_failures = failures[self._failure_cursor :]
                self._failure_cursor = len(failures)
                for failure in new_failures:
                    pattern = await self.failure_detector._detect_pattern(
                        failure["agent"],
                        failure["task_type"],
                        failure["error"]
                    )
                    
                    if pattern:
                        strategy = await self.failure_detector.suggest_prevention_strategy(pattern)
                        
                        # Propose fix
                        proposal_id = await self.proposal_engine.propose_improvement(
                            agent_name=pattern.agent_name,
                            improvement_type=ImprovementType.RELIABILITY,
                            description=f"Fix recurring failure pattern ({pattern.frequency}x): {pattern.symptoms[0]}",
                            expected_impact={"reliability": 0.2},
                            implementation_plan=[strategy],
                            estimated_effort_hours=2.0,
                            risk_level="medium"
                        )
                
                await asyncio.sleep(120)  # Check every 2 minutes
            
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error("failure_learning_error", error=str(e))
    
    async def _discover_emergent_skills_loop(self):
        """Discover new skills emerging in agents"""
        while self.running:
            try:
                for agent_name in self.agents.keys():
                    emergent = await self.skill_registry.discover_emergent_skills(agent_name)
                    
                    if emergent:
                        logger.info(
                            "emergent_skills_detected",
                            agent=agent_name,
                            skills=[s.name for s in emergent]
                        )
                
                await asyncio.sleep(600)  # Check every 10 minutes
            
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error("skill_discovery_error", error=str(e))
    
    async def _trigger_emergency_optimization(self):
        """Emergency system optimization when health degrades"""
        logger.info("emergency_optimization_triggered")
        
        # Disable expensive features
        # Scale down non-critical agents
        # Switch to faster/cheaper models
        # Implement aggressive caching
        
        await self.proposal_engine.propose_improvement(
            agent_name="system",
            improvement_type=ImprovementType.RELIABILITY,
            description="Emergency optimization: System health <90%",
            expected_impact={"reliability": 0.3},
            implementation_plan=[
                "Disable expensive features",
                "Scale down non-critical agents",
                "Switch to faster models",
                "Implement aggressive caching"
            ],
            estimated_effort_hours=0.5,
            risk_level="low"
        )
    
    async def get_improvement_status(self) -> Dict[str, Any]:
        """Get current status of improvements"""
        return {
            "total_proposals": len(self.proposal_engine.proposals),
            "pending": sum(1 for p in self.proposal_engine.proposals.values() if p.status == "pending"),
            "in_progress": sum(1 for p in self.proposal_engine.proposals.values() if p.status == "in_progress"),
            "completed": sum(1 for p in self.proposal_engine.proposals.values() if p.status == "completed"),
            "failed": sum(1 for p in self.proposal_engine.proposals.values() if p.status == "failed"),
            "queue_length": len(self.improvement_queue)
        }
    
    async def stop(self):
        """Stop the GoalKeeper"""
        self.running = False
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self.redis.xadd(
            "goal_keeper:events",
            {"data": _safe_json_dumps({"event": "goal_keeper_stopped", "timestamp": datetime.now().isoformat()})},
            maxlen=1000,
            approximate=True,
        )
        logger.info("goal_keeper_stopped")
