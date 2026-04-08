"""
Achievement Service.
Manages achievement unlocks, rewards, and migration logic.
"""
from typing import List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logging import LoggerMixin
from src.core.database import db
from src.models import UserAchievement
from src.repositories.achievement import AchievementRepository, UserAchievementRepository
from src.repositories.economy import UserRepository, EconomyRepository
from src.services.economy import EconomyService


class AchievementService(LoggerMixin):
    """
    Service layer for Achievement system.
    """
    
    def __init__(self, session: AsyncSession, db_instance=None):
        self.session = session
        self.db = db_instance or db
        self.achievement_repo = AchievementRepository(session)
        self.user_achievement_repo = UserAchievementRepository(session)
        self.user_repo = UserRepository(session)
        self.economy_repo = EconomyRepository(session)
        self.economy_service = EconomyService(session, db_instance)

    async def get_user_achievements(self, user_id: int) -> List[UserAchievement]:
        """Get all achievements unlocked by user."""
        return await self.user_achievement_repo.get_user_achievements(user_id)

    async def check_triggers(self, user_id: int, trigger_type: str, value: int = 0):
        """
        Check for achievements triggered by an event (e.g., streak update).
        """
        all_achievements = await self.achievement_repo.get_all_achievements()
        
        # Filter potential achievements
        candidates = [
            a for a in all_achievements 
            if a.trigger_type == trigger_type
        ]
        
        for ach in candidates:
            should_unlock = False
            
            if trigger_type == "streak":
                # Check if current streak meets requirement
                # Assuming value passed is current streak
                if value >= int(ach.trigger_value or 0):
                    should_unlock = True
            
            elif trigger_type == "seasonal":
                # Check if current date is within season
                # trigger_value format: "start_month-end_month" e.g. "12-02" for Winter
                # This is simplified logic
                datetime.utcnow().month
                # ... parsing logic ...
                pass

            if should_unlock:
                await self.unlock_achievement(user_id, ach.name)

    async def unlock_achievement(self, user_id: int, achievement_name: str) -> Optional[UserAchievement]:
        """
        Unlock an achievement by name and award tokens.
        Idempotent: If already unlocked, returns existing record without re-awarding.
        """
        async with self.db.transaction() as session:
            achievement_repo = AchievementRepository(session)
            user_achievement_repo = UserAchievementRepository(session)
            economy_service = EconomyService(session, self.db)
            
            achievement = await achievement_repo.get_by_name(achievement_name)
            if not achievement:
                self.logger.warning(f"Achievement not found: {achievement_name}")
                return None
            
            # Check if already unlocked
            user_achievements = await user_achievement_repo.get_user_achievements(user_id)
            is_unlocked = any(ua.achievement_id == achievement.id for ua in user_achievements)
            
            if is_unlocked:
                return next(ua for ua in user_achievements if ua.achievement_id == achievement.id)
            
            # Unlock
            user_achievement = await user_achievement_repo.unlock_achievement(user_id, achievement.id)
            
            # Award Tokens
            if achievement.reward > 0:
                await economy_service.process_transaction(
                    user_id=user_id,
                    amount=achievement.reward,
                    type="credit",
                    category="achievement_reward",
                    description=f"Unlocked: {achievement.name}",
                    reference_id=f"ach_{user_id}_{achievement.id}"
                )
                
            self.logger.info(
                "Achievement unlocked",
                user_id=user_id,
                achievement=achievement.name,
                reward=achievement.reward
            )
            
            return user_achievement
