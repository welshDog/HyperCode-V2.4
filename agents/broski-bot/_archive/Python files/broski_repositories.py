"""
Repository pattern implementation for data access.
Separates business logic from database operations.
"""
from datetime import datetime
from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.database import Base
from src.core.exceptions import RecordNotFoundException
from src.models import Economy, FocusSession, User

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository providing common CRUD operations.
    
    All repositories should inherit from this class.
    """
    
    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        """
        Initialize repository.
        
        Args:
            model: SQLAlchemy model class
            session: Database session
        """
        self.model = model
        self.session = session
    
    async def get(self, id: int) -> Optional[ModelType]:
        """
        Get record by primary key.
        
        Args:
            id: Primary key value
            
        Returns:
            Model instance or None if not found
        """
        return await self.session.get(self.model, id)
    
    async def get_or_fail(self, id: int) -> ModelType:
        """
        Get record by primary key or raise exception.
        
        Args:
            id: Primary key value
            
        Returns:
            Model instance
            
        Raises:
            RecordNotFoundException: If record not found
        """
        record = await self.get(id)
        if not record:
            raise RecordNotFoundException(self.model.__name__, id)
        return record
    
    async def create(self, **kwargs) -> ModelType:
        """
        Create new record.
        
        Args:
            **kwargs: Model attributes
            
        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
    
    async def update(self, id: int, **kwargs) -> ModelType:
        """
        Update record by primary key.
        
        Args:
            id: Primary key value
            **kwargs: Attributes to update
            
        Returns:
            Updated model instance
            
        Raises:
            RecordNotFoundException: If record not found
        """
        record = await self.get_or_fail(id)
        for key, value in kwargs.items():
            setattr(record, key, value)
        await self.session.flush()
        await self.session.refresh(record)
        return record
    
    async def delete(self, id: int) -> bool:
        """
        Delete record by primary key.
        
        Args:
            id: Primary key value
            
        Returns:
            True if deleted, False if not found
        """
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0


class UserRepository(BaseRepository[User]):
    """Repository for user operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)
    
    async def get_with_economy(self, user_id: int) -> Optional[User]:
        """
        Get user with economy data loaded.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            User with economy relationship loaded
        """
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.economy))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_or_create(self, user_id: int, username: str, discriminator: str) -> User:
        """
        Get existing user or create new one.
        
        Args:
            user_id: Discord user ID
            username: Discord username
            discriminator: Discord discriminator
            
        Returns:
            User instance
        """
        user = await self.get(user_id)
        if not user:
            user = await self.create(
                id=user_id,
                username=username,
                discriminator=discriminator,
            )
        return user
    
    async def update_last_seen(self, user_id: int) -> None:
        """
        Update user's last seen timestamp.
        
        Args:
            user_id: Discord user ID
        """
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_seen=datetime.utcnow())
        )
        await self.session.execute(stmt)


class EconomyRepository(BaseRepository[Economy]):
    """Repository for economy operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Economy, session)
    
    async def get_by_user(self, user_id: int) -> Optional[Economy]:
        """
        Get economy data for user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Economy instance or None
        """
        return await self.session.get(Economy, user_id)
    
    async def get_or_create(self, user_id: int, starting_balance: int = 500) -> Economy:
        """
        Get or create economy record for user.
        
        Args:
            user_id: Discord user ID
            starting_balance: Initial balance for new users
            
        Returns:
            Economy instance
        """
        economy = await self.get_by_user(user_id)
        if not economy:
            economy = await self.create(
                user_id=user_id,
                balance=starting_balance,
            )
        return economy
    
    async def add_balance(self, user_id: int, amount: int) -> Economy:
        """
        Add tokens to user balance.
        
        Args:
            user_id: Discord user ID
            amount: Amount to add
            
        Returns:
            Updated economy instance
        """
        economy = await self.get_or_create(user_id)
        economy.balance += amount
        economy.lifetime_earned += amount
        await self.session.flush()
        await self.session.refresh(economy)
        return economy
    
    async def subtract_balance(self, user_id: int, amount: int) -> Economy:
        """
        Subtract tokens from user balance.
        
        Args:
            user_id: Discord user ID
            amount: Amount to subtract
            
        Returns:
            Updated economy instance
            
        Raises:
            InsufficientBalanceException: If balance too low
        """
        from src.core.exceptions import InsufficientBalanceException
        
        economy = await self.get_or_create(user_id)
        if economy.balance < amount:
            raise InsufficientBalanceException(amount, economy.balance)
        
        economy.balance -= amount
        economy.lifetime_spent += amount
        await self.session.flush()
        await self.session.refresh(economy)
        return economy
    
    async def get_leaderboard(self, limit: int = 10) -> List[Economy]:
        """
        Get top users by balance.
        
        Args:
            limit: Number of results
            
        Returns:
            List of economy records ordered by balance
        """
        stmt = (
            select(Economy)
            .order_by(Economy.balance.desc())
            .limit(limit)
            .options(selectinload(Economy.user))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class FocusSessionRepository(BaseRepository[FocusSession]):
    """Repository for focus session operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FocusSession, session)
    
    async def get_active_session(self, user_id: int) -> Optional[FocusSession]:
        """
        Get user's active focus session.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Active session or None
        """
        stmt = (
            select(FocusSession)
            .where(FocusSession.user_id == user_id)
            .where(FocusSession.is_active)
            .order_by(FocusSession.start_time.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_session(self, user_id: int, project_name: str) -> FocusSession:
        """
        Create new focus session.
        
        Args:
            user_id: Discord user ID
            project_name: Project name
            
        Returns:
            Created session
        """
        return await self.create(
            user_id=user_id,
            project_name=project_name,
            is_active=True,
        )
    
    async def end_session(self, session_id: int, tokens_earned: int) -> FocusSession:
        """
        End focus session and calculate rewards.
        
        Args:
            session_id: Session ID
            tokens_earned: Tokens earned
            
        Returns:
            Updated session
        """
        session = await self.get_or_fail(session_id)
        
        # Calculate duration
        end_time = datetime.utcnow()
        duration = (end_time - session.start_time).total_seconds() / 60
        
        # Update session
        session.end_time = end_time
        session.duration_minutes = int(duration)
        session.tokens_earned = tokens_earned
        session.is_active = False
        
        await self.session.flush()
        await self.session.refresh(session)
        return session
    
    async def get_user_sessions(
        self,
        user_id: int,
        limit: int = 10,
    ) -> List[FocusSession]:
        """
        Get user's recent focus sessions.
        
        Args:
            user_id: Discord user ID
            limit: Number of results
            
        Returns:
            List of sessions
        """
        stmt = (
            select(FocusSession)
            .where(FocusSession.user_id == user_id)
            .order_by(FocusSession.start_time.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
