"""
Achievement Repository.
Handles database operations for achievements and user progress.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Achievement, UserAchievement
from src.repositories.economy import BaseRepository


class AchievementRepository(BaseRepository[Achievement]):
    """Repository for achievement definitions."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Achievement, session)

    async def get_by_name(self, name: str) -> Optional[Achievement]:
        """Get achievement by name."""
        stmt = select(Achievement).where(Achievement.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_achievements(self) -> List[Achievement]:
        """Get all achievements."""
        stmt = select(Achievement)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class UserAchievementRepository(BaseRepository[UserAchievement]):
    """Repository for user achievement unlocks."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(UserAchievement, session)

    async def get_user_achievements(self, user_id: int) -> List[UserAchievement]:
        """Get all unlocked achievements for a user."""
        stmt = (
            select(UserAchievement)
            .where(UserAchievement.user_id == user_id)
            .options(selectinload(UserAchievement.achievement))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def unlock_achievement(self, user_id: int, achievement_id: int) -> UserAchievement:
        """Unlock an achievement for a user."""
        # Check if already unlocked
        stmt = select(UserAchievement).where(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement_id
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            return existing
            
        # Unlock
        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id,
            unlocked_at=datetime.utcnow()
        )
        self.session.add(user_achievement)
        await self.session.flush()
        return user_achievement
