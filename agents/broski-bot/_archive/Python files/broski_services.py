"""
Service layer implementing business logic.
Orchestrates repository operations and enforces business rules.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logging import LoggerMixin
from src.config.settings import settings
from src.core.exceptions import (
    DailyLimitExceededException,
    InvalidAmountException,
    SessionActiveException,
    SessionNotFoundException,
)
from src.models import FocusSession
from src.repositories import EconomyRepository, FocusSessionRepository, UserRepository


class EconomyService(LoggerMixin):
    """Service handling economy and token operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize service.
        
        Args:
            session: Database session
        """
        self.session = session
        self.user_repo = UserRepository(session)
        self.economy_repo = EconomyRepository(session)
    
    async def get_balance(self, user_id: int) -> int:
        """
        Get user's token balance.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Token balance
        """
        economy = await self.economy_repo.get_or_create(
            user_id,
            settings.economy_starting_balance,
        )
        return economy.balance
    
    async def claim_daily_reward(self, user_id: int, username: str, discriminator: str) -> Tuple[int, int, bool]:
        """
        Claim daily reward with streak bonuses.
        
        Args:
            user_id: Discord user ID
            username: Discord username
            discriminator: Discord discriminator
            
        Returns:
            Tuple of (tokens_earned, current_streak, is_new_streak)
            
        Raises:
            DailyLimitExceededException: If already claimed today
        """
        # Ensure user exists
        await self.user_repo.get_or_create(user_id, username, discriminator)
        
        # Get economy data
        economy = await self.economy_repo.get_or_create(
            user_id,
            settings.economy_starting_balance,
        )
        
        # Check if already claimed today
        now = datetime.utcnow()
        if economy.last_daily_claim:
            time_since_claim = now - economy.last_daily_claim
            if time_since_claim < timedelta(days=1):
                hours_remaining = 24 - (time_since_claim.seconds / 3600)
                self.logger.warning(
                    "Daily reward already claimed",
                    user_id=user_id,
                    hours_remaining=hours_remaining,
                )
                raise DailyLimitExceededException("daily_reward", 1)
        
        # Calculate streak
        is_new_streak = False
        if economy.last_daily_claim:
            days_since_claim = (now - economy.last_daily_claim).days
            if days_since_claim == 1:
                # Streak continues
                economy.daily_streak += 1
            elif days_since_claim > 1:
                # Streak broken
                economy.daily_streak = 1
                is_new_streak = True
        else:
            # First claim
            economy.daily_streak = 1
            is_new_streak = True
        
        # Cap streak
        if economy.daily_streak > settings.economy_max_streak_days:
            economy.daily_streak = settings.economy_max_streak_days
        
        # Calculate reward
        base_reward = settings.economy_daily_reward
        streak_bonus = economy.daily_streak * settings.economy_daily_streak_bonus
        total_reward = base_reward + streak_bonus
        
        # Update economy
        economy.balance += total_reward
        economy.lifetime_earned += total_reward
        economy.last_daily_claim = now
        
        if economy.daily_streak > economy.max_daily_streak:
            economy.max_daily_streak = economy.daily_streak
        
        await self.session.commit()
        
        self.logger.info(
            "Daily reward claimed",
            user_id=user_id,
            reward=total_reward,
            streak=economy.daily_streak,
        )
        
        return total_reward, economy.daily_streak, is_new_streak
    
    async def transfer_tokens(
        self,
        from_user_id: int,
        to_user_id: int,
        amount: int,
    ) -> Tuple[int, int]:
        """
        Transfer tokens between users.
        
        Args:
            from_user_id: Sender user ID
            to_user_id: Recipient user ID
            amount: Amount to transfer
            
        Returns:
            Tuple of (sender_new_balance, recipient_new_balance)
            
        Raises:
            InvalidAmountException: If amount <= 0
            InsufficientBalanceException: If sender has insufficient balance
        """
        if amount <= 0:
            raise InvalidAmountException(amount, "Amount must be positive")
        
        if from_user_id == to_user_id:
            raise InvalidAmountException(amount, "Cannot transfer to yourself")
        
        # Deduct from sender
        sender_economy = await self.economy_repo.subtract_balance(from_user_id, amount)
        
        # Add to recipient
        recipient_economy = await self.economy_repo.add_balance(to_user_id, amount)
        
        await self.session.commit()
        
        self.logger.info(
            "Tokens transferred",
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            amount=amount,
        )
        
        return sender_economy.balance, recipient_economy.balance


class FocusService(LoggerMixin):
    """Service handling focus sessions and productivity tracking."""
    
    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize service.
        
        Args:
            session: Database session
        """
        self.session = session
        self.user_repo = UserRepository(session)
        self.economy_repo = EconomyRepository(session)
        self.focus_repo = FocusSessionRepository(session)
    
    async def start_session(
        self,
        user_id: int,
        username: str,
        discriminator: str,
        project_name: str,
    ) -> FocusSession:
        """
        Start new focus session.
        
        Args:
            user_id: Discord user ID
            username: Discord username
            discriminator: Discord discriminator
            project_name: Name of project
            
        Returns:
            Created focus session
            
        Raises:
            SessionActiveException: If session already active
        """
        # Ensure user exists
        await self.user_repo.get_or_create(user_id, username, discriminator)
        
        # Check for active session
        active_session = await self.focus_repo.get_active_session(user_id)
        if active_session:
            raise SessionActiveException("focus")
        
        # Create session
        session = await self.focus_repo.create_session(user_id, project_name)
        await self.session.commit()
        
        self.logger.info(
            "Focus session started",
            user_id=user_id,
            project_name=project_name,
        )
        
        return session
    
    async def end_session(self, user_id: int) -> Tuple[FocusSession, int]:
        """
        End active focus session and calculate rewards.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (session, tokens_earned)
            
        Raises:
            SessionNotFoundException: If no active session
        """
        # Get active session
        session = await self.focus_repo.get_active_session(user_id)
        if not session:
            raise SessionNotFoundException("focus")
        
        # Calculate duration
        duration_minutes = int((datetime.utcnow() - session.start_time).total_seconds() / 60)
        
        # Check for hyperfocus
        is_hyperfocus = duration_minutes >= settings.focus_hyperfocus_threshold
        
        # Calculate rewards
        base_reward = settings.focus_base_reward
        if is_hyperfocus:
            total_reward = int(base_reward * settings.focus_hyperfocus_multiplier)
            session.is_hyperfocus = True
        else:
            total_reward = base_reward
        
        # End session
        session = await self.focus_repo.end_session(session.id, total_reward)
        
        # Add tokens to balance
        await self.economy_repo.add_balance(user_id, total_reward)
        
        await self.session.commit()
        
        self.logger.info(
            "Focus session ended",
            user_id=user_id,
            duration_minutes=duration_minutes,
            tokens_earned=total_reward,
            is_hyperfocus=is_hyperfocus,
        )
        
        return session, total_reward
    
    async def get_active_session(self, user_id: int) -> Optional[FocusSession]:
        """
        Get user's active session.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Active session or None
        """
        return await self.focus_repo.get_active_session(user_id)
    
    async def get_session_stats(self, user_id: int) -> dict:
        """
        Get user's focus session statistics.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary of statistics
        """
        sessions = await self.focus_repo.get_user_sessions(user_id, limit=100)
        
        if not sessions:
            return {
                "total_sessions": 0,
                "total_minutes": 0,
                "total_tokens_earned": 0,
                "hyperfocus_count": 0,
                "average_duration": 0,
            }
        
        total_minutes = sum(s.duration_minutes or 0 for s in sessions)
        total_tokens = sum(s.tokens_earned for s in sessions)
        hyperfocus_count = sum(1 for s in sessions if s.is_hyperfocus)
        
        return {
            "total_sessions": len(sessions),
            "total_minutes": total_minutes,
            "total_tokens_earned": total_tokens,
            "hyperfocus_count": hyperfocus_count,
            "average_duration": total_minutes // len(sessions) if sessions else 0,
        }
