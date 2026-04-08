import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from src.services.quest import QuestService
from src.services.achievement import AchievementService
from src.models import QuestStatus, QuestType, Quest, UserQuest, Achievement
from src.core.quest_engine import AgentOrchestrator

@pytest.mark.asyncio
async def test_quest_service_timed_quest():
    """Test timed quest expiration."""
    # Mock dependencies
    session = AsyncMock()
    service = QuestService(session)
    service.orchestrator = AsyncMock(spec=AgentOrchestrator)
    
    # Setup timed quest that started 2 hours ago with 1 hour limit
    quest = Quest(type=QuestType.TIMED, time_limit_minutes=60, requirement_count=1)
    user_quest = UserQuest(
        id=1, 
        status=QuestStatus.ACTIVE, 
        started_at=datetime.utcnow() - timedelta(minutes=120),
        quest=quest
    )
    
    # Mock transaction context and repositories
    with patch("src.services.quest.db") as mock_db, \
         patch("src.services.quest.UserQuestRepository") as MockUserQuestRepo, \
         patch("src.services.quest.UserRepository"), \
         patch("src.services.quest.QuestRepository"):
        
        tx_context = AsyncMock()
        mock_db.transaction.return_value = tx_context
        tx_context.__aenter__.return_value = session
        
        # Mock Repo Instances
        mock_user_quest_repo = AsyncMock()
        MockUserQuestRepo.return_value = mock_user_quest_repo
        mock_user_quest_repo.get_user_quest.return_value = user_quest
        
        # Call complete_quest
        result = await service.complete_quest(1, 1)
        
        # Verify it expired instead of completing
        mock_user_quest_repo.update_status.assert_called_with(1, QuestStatus.EXPIRED)
        assert result == user_quest

@pytest.mark.asyncio
async def test_quest_service_tiered_quest():
    """Test tiered quest unlocking."""
    # Mock dependencies
    session = AsyncMock()
    service = QuestService(session)
    service.orchestrator = AsyncMock(spec=AgentOrchestrator)
    
    # Setup tiered quest
    quest = Quest(type=QuestType.TIERED, next_quest_id=2, requirement_count=1)
    user_quest = UserQuest(
        id=1, 
        status=QuestStatus.ACTIVE, 
        quest=quest,
        started_at=datetime.utcnow()
    )
    
    next_quest = Quest(id=2, title="Next Quest")
    
    # Mock DB Transaction and Repos
    with patch("src.services.quest.db") as mock_db, \
         patch("src.services.quest.UserQuestRepository") as MockUserQuestRepo, \
         patch("src.services.quest.UserRepository") as MockUserRepo, \
         patch("src.services.quest.QuestRepository") as MockQuestRepo:
        
        tx_context = AsyncMock()
        mock_db.transaction.return_value = tx_context
        tx_context.__aenter__.return_value = session
        
        # Mock Repo Instances
        mock_user_quest_repo = AsyncMock()
        MockUserQuestRepo.return_value = mock_user_quest_repo
        mock_user_quest_repo.get_user_quest.return_value = user_quest
        
        mock_quest_repo = AsyncMock()
        MockQuestRepo.return_value = mock_quest_repo
        mock_quest_repo.get.return_value = next_quest
        
        mock_user_repo = AsyncMock()
        MockUserRepo.return_value = mock_user_repo
        mock_user_repo.get_by_id.return_value = MagicMock(id=1) # Returns user profile
        
        # Call complete_quest
        await service.complete_quest(1, 1)
        
        # Verify status update
        mock_user_quest_repo.update_status.assert_called_with(1, QuestStatus.COMPLETED)
        
        # Verify next quest assignment
        mock_user_quest_repo.create_user_quest.assert_called_with(1, 2)

@pytest.mark.asyncio
async def test_achievement_streak_trigger():
    """Test streak achievement trigger."""
    session = AsyncMock()
    service = AchievementService(session)
    
    # Mock Repos
    achievement_repo = AsyncMock()
    service.achievement_repo = achievement_repo
    
    # Setup achievements
    streak_ach = Achievement(name="Streak Master", trigger_type="streak", trigger_value="5")
    achievement_repo.get_all_achievements.return_value = [streak_ach]
    
    # Mock unlock method
    service.unlock_achievement = AsyncMock()
    
    # Test triggering
    await service.check_triggers(1, "streak", value=5)
    
    service.unlock_achievement.assert_called_with(1, "Streak Master")
    
    # Test not triggering
    service.unlock_achievement.reset_mock()
    await service.check_triggers(1, "streak", value=3)
    service.unlock_achievement.assert_not_called()
