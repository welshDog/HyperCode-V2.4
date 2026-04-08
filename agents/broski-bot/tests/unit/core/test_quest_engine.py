import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from src.core.quest_engine import QuestStateMachine, QuestTransitionError, AgentOrchestrator
from src.models import QuestStatus, Quest, UserQuest
from src.core.schemas import UserProfile


def test_quest_state_machine_valid_transitions():
    """Test all valid transitions defined in the state machine."""
    # Available -> Active
    QuestStateMachine.validate_transition(QuestStatus.AVAILABLE, QuestStatus.ACTIVE)
    # Active -> Completed
    QuestStateMachine.validate_transition(QuestStatus.ACTIVE, QuestStatus.COMPLETED)
    # Active -> Failed
    QuestStateMachine.validate_transition(QuestStatus.ACTIVE, QuestStatus.FAILED)
    # Failed -> Active (Retry)
    QuestStateMachine.validate_transition(QuestStatus.FAILED, QuestStatus.ACTIVE)
    # Available -> Expired
    QuestStateMachine.validate_transition(QuestStatus.AVAILABLE, QuestStatus.EXPIRED)


def test_quest_state_machine_invalid_transitions():
    """Test invalid transitions raise QuestTransitionError."""
    # Completed is terminal
    with pytest.raises(QuestTransitionError):
        QuestStateMachine.validate_transition(QuestStatus.COMPLETED, QuestStatus.ACTIVE)
    
    # Expired is terminal
    with pytest.raises(QuestTransitionError):
        QuestStateMachine.validate_transition(QuestStatus.EXPIRED, QuestStatus.ACTIVE)
    
    # Available cannot go directly to Completed
    with pytest.raises(QuestTransitionError):
        QuestStateMachine.validate_transition(QuestStatus.AVAILABLE, QuestStatus.COMPLETED)


def test_quest_state_machine_self_transition():
    """Test that self-transition (e.g., Active -> Active) is valid."""
    QuestStateMachine.validate_transition(QuestStatus.ACTIVE, QuestStatus.ACTIVE)


def test_quest_state_machine_can_transition():
    """Test the can_transition helper method."""
    assert QuestStateMachine.can_transition(QuestStatus.AVAILABLE, QuestStatus.ACTIVE) is True
    assert QuestStateMachine.can_transition(QuestStatus.COMPLETED, QuestStatus.ACTIVE) is False
    assert QuestStateMachine.can_transition(QuestStatus.ACTIVE, QuestStatus.ACTIVE) is True


@pytest.mark.asyncio
async def test_agent_orchestrator_performance():
    """
    Performance benchmark: evaluate_quest_adaptation should be sub-200ms.
    Demonstrating sub-200ms response times for quest state transitions.
    """
    orchestrator = AgentOrchestrator()
    user_id = 123
    quest_id = 456
    context = {"streak": 7}
    
    start_time = datetime.now(timezone.utc)
    adaptation = await orchestrator.evaluate_quest_adaptation(user_id, quest_id, context)
    end_time = datetime.now(timezone.utc)
    
    duration_ms = (end_time - start_time).total_seconds() * 1000
    
    assert duration_ms < 200
    assert adaptation["reward_multiplier"] == 1.5
    assert adaptation["difficulty_modifier"] == 1.2


@pytest.mark.asyncio
async def test_agent_orchestrator_coordination():
    """Test multi-agent coordination with results dictionary."""
    orchestrator = AgentOrchestrator()
    task = "quest_adaptation"
    agents = ["classifier", "analyzer", "rewarder"]
    
    results = await orchestrator.coordinate_agents(task, agents)
    
    assert len(results) == 3
    assert results["classifier"] == "success"
    assert results["analyzer"] == "success"
    assert results["rewarder"] == "success"

@pytest.mark.asyncio
async def test_agent_orchestrator_services():
    """Test integration with AI services."""
    orchestrator = AgentOrchestrator()
    
    # Mock UserProfile
    user = UserProfile(
        id=1,
        username="test",
        discriminator="0001",
        level=5,
        xp=100,
        total_messages=50,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_seen=datetime.utcnow()
    )
    
    # Test Generate Quests
    quests = await orchestrator.generate_user_quests(user)
    assert len(quests) == 3
    assert quests[0].token_reward > 0
    
    # Test Adapt Content
    quests[0].description = "Original Description"
    updated_quest = await orchestrator.adapt_quest_content(user, quests[0])
    assert "Original Description" in updated_quest.description
    assert updated_quest.description != "Original Description"
    
    # Test Analytics
    analytics = await orchestrator.analyze_user_behavior(user, 5)
    assert "churn_probability" in analytics
    assert 0.0 <= analytics["churn_probability"] <= 1.0

@pytest.mark.asyncio
async def test_transition_quest_with_hooks():
    """Test quest transition with side effects."""
    orchestrator = AgentOrchestrator()
    
    user = UserProfile(
        id=1,
        username="test",
        discriminator="0001",
        level=5,
        xp=100,
        total_messages=50,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_seen=datetime.utcnow()
    )
    
    quest_definition = Quest(
        id=1,
        title="Test Quest",
        description="Test",
        category="test",
        requirement_type="test",
        requirement_count=1
    )
    
    user_quest = UserQuest(
        id=1,
        user_id=1,
        quest_id=1,
        status=QuestStatus.AVAILABLE,
        quest=quest_definition
    )
    
    # Mock services to verify calls
    orchestrator.behavior_adapter.adapt_quest_description = AsyncMock(return_value="Adapted")
    orchestrator.analytics_engine.predict_churn = AsyncMock(return_value=0.1)
    
    # Transition Available -> Active (Triggers adapt_quest_content)
    await orchestrator.transition_quest(user_quest, QuestStatus.ACTIVE, user)
    
    assert user_quest.status == QuestStatus.ACTIVE
    orchestrator.behavior_adapter.adapt_quest_description.assert_called_once()
    
    # Transition Active -> Completed (Triggers analyze_user_behavior)
    await orchestrator.transition_quest(user_quest, QuestStatus.COMPLETED, user)
    
    assert user_quest.status == QuestStatus.COMPLETED
    orchestrator.analytics_engine.predict_churn.assert_called_once()
