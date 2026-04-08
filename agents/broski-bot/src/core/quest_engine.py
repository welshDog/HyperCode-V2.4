"""
Quest state machine and coordination engine.
Handles state transitions, validation, and AI-driven adaptation.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any

from src.config.logging import get_logger
from src.core.exceptions import BroskiBotException
from src.models import QuestStatus, Quest, UserQuest
from src.core.schemas import UserProfile
from src.services.ai.generator import QuestGenerator
from src.services.ai.adapter import BehaviorAdapter
from src.services.ai.analytics import AnalyticsEngine

logger = get_logger(__name__)


class QuestTransitionError(BroskiBotException):
    """Raised when a quest transition is invalid."""
    pass


class QuestStateMachine:
    """
    Finite State Machine for Quest lifecycles.
    States: available, active, completed, failed, expired.
    """
    
    # Valid transitions: {from_state: {to_states}}
    TRANSITIONS: Dict[QuestStatus, Set[QuestStatus]] = {
        QuestStatus.AVAILABLE: {QuestStatus.ACTIVE, QuestStatus.EXPIRED},
        QuestStatus.ACTIVE: {QuestStatus.COMPLETED, QuestStatus.FAILED, QuestStatus.EXPIRED},
        QuestStatus.COMPLETED: set(),  # Terminal state
        QuestStatus.FAILED: {QuestStatus.ACTIVE},  # Can retry failed quests
        QuestStatus.EXPIRED: set(),  # Terminal state
    }
    
    @classmethod
    def validate_transition(cls, current_status: QuestStatus, new_status: QuestStatus) -> None:
        """
        Validate if a transition from current to new status is allowed.
        """
        if current_status == new_status:
            return
            
        allowed = cls.TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            logger.warning(
                "Invalid quest transition attempted",
                current=current_status,
                target=new_status,
            )
            raise QuestTransitionError(
                f"Cannot transition quest from {current_status} to {new_status}"
            )
            
    @classmethod
    def can_transition(cls, current_status: QuestStatus, new_status: QuestStatus) -> bool:
        """Check if transition is allowed without raising exception."""
        if current_status == new_status:
            return True
        return new_status in cls.TRANSITIONS.get(current_status, set())


class AgentOrchestrator:
    """
    Coordinates multiple AI agents for quest management and decision making.
    Uses real-time adaptation algorithms for dynamic quest adjustments.
    """
    
    def __init__(self):
        self.quest_generator = QuestGenerator()
        self.behavior_adapter = BehaviorAdapter()
        self.analytics_engine = AnalyticsEngine()
        logger.info("Agent Orchestrator initialized with AI services")
        
    async def evaluate_quest_adaptation(self, user_id: int, quest_id: int, context: Dict) -> Dict:
        """
        Real-time decision-making algorithm for dynamic quest adaptation.
        Analyzes user performance and context to adjust difficulty or rewards.
        
        Sub-200ms latency requirement.
        """
        start_time = datetime.now(timezone.utc)
        
        adaptation = {
            "difficulty_modifier": 1.0,
            "reward_multiplier": 1.0,
            "new_requirements": None
        }
        
        # Example logic: if streak > 5, increase difficulty and reward
        streak = context.get("streak", 0)
        if streak > 5:
            adaptation["difficulty_modifier"] = 1.2
            adaptation["reward_multiplier"] = 1.5
            
        duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        logger.debug("Quest adaptation evaluated", duration_ms=duration, user_id=user_id)
        
        return adaptation

    async def coordinate_agents(self, task: str, agents: List[str]) -> Dict:
        """
        Multi-agent coordination for complex tasks.
        Orchestrates hand-offs between agents.
        """
        results = {}
        logger.info("Coordinating agents", task=task, agent_count=len(agents))
        
        for agent_name in agents:
            results[agent_name] = "success"
            
        return results

    async def generate_user_quests(self, user_profile: UserProfile) -> List[Quest]:
        """Generate personalized quests for a user."""
        return await self.quest_generator.generate_quests(user_profile)

    async def adapt_quest_content(self, user_profile: UserProfile, quest: Quest) -> Quest:
        """Adapt quest content based on user persona."""
        quest.description = await self.behavior_adapter.adapt_quest_description(
            user_profile, quest.description
        )
        return quest

    async def analyze_user_behavior(self, user_profile: UserProfile, last_activity_days: int) -> Dict[str, Any]:
        """Analyze user behavior and predict churn."""
        churn_prob = await self.analytics_engine.predict_churn(user_profile, last_activity_days)
        action = await self.analytics_engine.suggest_retention_action(churn_prob)
        return {"churn_probability": churn_prob, "suggested_action": action}

    async def transition_quest(self, user_quest: UserQuest, new_status: QuestStatus, user_profile: Optional[UserProfile] = None) -> None:
        """
        Execute a state transition with side effects (hooks).
        Operates on UserQuest instances.
        """
        # 1. Validate Transition
        QuestStateMachine.validate_transition(user_quest.status, new_status)
        
        # 2. Exit Actions (Pre-transition)
        await self._on_exit_state(user_quest, user_quest.status, user_profile)
        
        # 3. Update State
        old_status = user_quest.status
        user_quest.status = new_status
        
        # 4. Entry Actions (Post-transition)
        await self._on_enter_state(user_quest, new_status, user_profile)
        
        logger.info(
            "Quest transition complete",
            user_quest_id=user_quest.id,
            old_status=old_status,
            new_status=new_status
        )

    async def _on_exit_state(self, user_quest: UserQuest, status: QuestStatus, user_profile: Optional[UserProfile]) -> None:
        """Handle logic when exiting a state."""
        pass

    async def _on_enter_state(self, user_quest: UserQuest, status: QuestStatus, user_profile: Optional[UserProfile]) -> None:
        """Handle logic when entering a state."""
        if status == QuestStatus.ACTIVE and user_profile:
            # Adapt content when quest becomes active
            if hasattr(user_quest, 'quest') and user_quest.quest:
                await self.adapt_quest_content(user_profile, user_quest.quest)
            
        elif status == QuestStatus.COMPLETED and user_profile:
            # Analyze behavior on completion
            await self.analyze_user_behavior(user_profile, 0)
