"""
Quest Repository.
Handles database operations for quests and user progress.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Quest, UserQuest, QuestStatus
from src.repositories.economy import BaseRepository


class QuestRepository(BaseRepository[Quest]):
    """Repository for quest definitions."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Quest)

    async def get_available_quests(self, limit: int = 10) -> List[Quest]:
        """Get active quests that are not expired."""
        stmt = select(Quest).where(
            Quest.is_active,
            (Quest.expires_at is None) | (Quest.expires_at > datetime.utcnow())
        ).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_quest(self, quest: Quest) -> Quest:
        """Create a new quest definition."""
        self.session.add(quest)
        await self.session.flush()
        return quest


class UserQuestRepository(BaseRepository[UserQuest]):
    """Repository for user quest progress."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserQuest)

    async def get_user_quest(self, user_id: int, quest_id: int) -> Optional[UserQuest]:
        """Get a specific user quest record."""
        stmt = select(UserQuest).where(
            UserQuest.user_id == user_id,
            UserQuest.quest_id == quest_id
        ).options(selectinload(UserQuest.quest))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_user_quests(self, user_id: int) -> List[UserQuest]:
        """Get all active quests for a user."""
        stmt = select(UserQuest).where(
            UserQuest.user_id == user_id,
            UserQuest.status == QuestStatus.ACTIVE
        ).options(selectinload(UserQuest.quest))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_user_quest(self, user_id: int, quest_id: int) -> UserQuest:
        """Assign a quest to a user."""
        user_quest = UserQuest(
            user_id=user_id,
            quest_id=quest_id,
            status=QuestStatus.ACTIVE, # Or AVAILABLE depending on logic
            progress=0,
            started_at=datetime.utcnow()
        )
        self.session.add(user_quest)
        await self.session.flush()
        return user_quest

    async def update_progress(self, user_quest_id: int, progress: int) -> UserQuest:
        """Update quest progress."""
        stmt = update(UserQuest).where(
            UserQuest.id == user_quest_id
        ).values(
            progress=progress
        ).returning(UserQuest)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_status(self, user_quest_id: int, status: QuestStatus) -> UserQuest:
        """Update quest status."""
        values = {"status": status}
        if status == QuestStatus.COMPLETED:
            values["completed_at"] = datetime.utcnow()
            
        stmt = update(UserQuest).where(
            UserQuest.id == user_quest_id
        ).values(**values).returning(UserQuest)
        result = await self.session.execute(stmt)
        return result.scalar_one()
