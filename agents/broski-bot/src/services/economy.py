"""
Service layer implementing business logic.
Orchestrates repository operations and enforces business rules.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logging import LoggerMixin
from src.config.settings import settings
from src.core.database import db
from src.core.exceptions import (
    DailyLimitExceededException,
    InvalidAmountException,
    SessionActiveException,
    SessionNotFoundException,
)
from src.core.schemas import EconomyProfile, FocusSessionProfile
from src.models import Transaction
from src.repositories import EconomyRepository, FocusSessionRepository, UserRepository, TransactionRepository


class EconomyService(LoggerMixin):
    """Service handling economy and token operations."""
    
    def __init__(self, session: AsyncSession, db_instance=None) -> None:
        """
        Initialize service.
        
        Args:
            session: Database session
            db_instance: Optional Database manager instance (defaults to global db)
        """
        self.session = session
        self.db = db_instance or db
        self.user_repo = UserRepository(session)
        self.economy_repo = EconomyRepository(session)
        self.transaction_repo = TransactionRepository(session)
    
    async def get_balance(self, user_id: int) -> int:
        """Get user's token balance."""
        economy = await self.economy_repo.get_or_create(
            user_id,
            settings.economy_starting_balance,
        )
        return economy.balance

    async def process_transaction(
        self,
        user_id: int,
        amount: int,
        type: str,
        category: str,
        description: str,
        reference_id: Optional[str] = None
    ) -> Transaction:
        """
        Process a financial transaction with idempotency.
        
        Args:
            user_id: User ID
            amount: Amount of tokens
            type: 'credit' or 'debit'
            category: Transaction category
            description: Description
            reference_id: Optional reference ID for idempotency
            
        Returns:
            Created Transaction record
        """
        async with self.db.transaction() as session:
            transaction_repo = TransactionRepository(session)
            economy_repo = EconomyRepository(session)

            # Idempotency check
            if reference_id:
                existing = await transaction_repo.get_by_reference(user_id, category, reference_id)
                if existing:
                    self.logger.info(
                        "Idempotent transaction skipped",
                        user_id=user_id,
                        reference_id=reference_id
                    )
                    return existing

            # Create transaction record
            transaction = await transaction_repo.create_transaction(
                user_id=user_id,
                amount=amount,
                type=type,
                category=category,
                description=description,
                reference_id=reference_id
            )

            # Update balance
            if type == "credit":
                await economy_repo.add_balance(user_id, amount)
            elif type == "debit":
                await economy_repo.subtract_balance(user_id, amount)
                
            return transaction
    
    async def claim_daily_reward(self, user_id: int, username: str, discriminator: str) -> Tuple[int, int, bool]:
        """Claim daily reward with streak bonuses."""
        if self.db and hasattr(self.db, '_session_factory') and self.db._session_factory:
             async with self.db.transaction() as session:
                return await self._claim_daily_reward_logic(session, user_id, username, discriminator)
        else:
            return await self._claim_daily_reward_logic(self.session, user_id, username, discriminator)

    async def _claim_daily_reward_logic(self, session: AsyncSession, user_id: int, username: str, discriminator: str) -> Tuple[int, int, bool]:
        """Internal logic for daily reward."""
        # Re-initialize repos with the transaction session
        user_repo = UserRepository(session)
        economy_repo = EconomyRepository(session)
        transaction_repo = TransactionRepository(session)
        
        # Ensure user exists
        await user_repo.get_or_create(user_id, username, discriminator)
        
        # Get economy data
        economy = await economy_repo.get_or_create(
            user_id,
            settings.economy_starting_balance,
        )
        
        # Check if already claimed today
        now = datetime.utcnow()
        if economy.last_daily_claim:
            time_since_claim = now - economy.last_daily_claim
            if time_since_claim < timedelta(days=1):
                24 - (time_since_claim.seconds / 3600)
                raise DailyLimitExceededException("daily_reward", 1)
        
        # Calculate streak
        is_new_streak = False
        if economy.last_daily_claim:
            days_since_claim = (now - economy.last_daily_claim).days
            if days_since_claim == 1:
                economy.daily_streak += 1
            elif days_since_claim > 1:
                economy.daily_streak = 1
                is_new_streak = True
        else:
            economy.daily_streak = 1
            is_new_streak = True
        
        # Cap streak
        if economy.daily_streak > settings.economy_max_streak_days:
            economy.daily_streak = settings.economy_max_streak_days
        
        # Calculate reward
        base_reward = settings.economy_daily_reward
        streak_bonus = economy.daily_streak * settings.economy_daily_streak_bonus
        total_reward = base_reward + streak_bonus
        
        # Update economy state
        economy.last_daily_claim = now
        if economy.daily_streak > economy.max_daily_streak:
            economy.max_daily_streak = economy.daily_streak
        
        # Process Transaction (Credit)
        await transaction_repo.create_transaction(
            user_id=user_id,
            amount=total_reward,
            type="credit",
            category="daily_reward",
            description=f"Daily reward (Streak: {economy.daily_streak})",
            reference_id=f"daily_{user_id}_{now.date()}"
        )
        
        # Update Balance via Repo
        await economy_repo.add_balance(user_id, total_reward)
        
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
        """Transfer tokens between users."""
        if amount <= 0:
            raise InvalidAmountException(amount, "Amount must be positive")
        
        if from_user_id == to_user_id:
            raise InvalidAmountException(amount, "Cannot transfer to yourself")
        
        if self.db and hasattr(self.db, '_session_factory') and self.db._session_factory:
            async with self.db.transaction() as session:
                return await self._transfer_tokens_logic(session, from_user_id, to_user_id, amount)
        else:
            return await self._transfer_tokens_logic(self.session, from_user_id, to_user_id, amount)

    async def _transfer_tokens_logic(
        self,
        session: AsyncSession,
        from_user_id: int,
        to_user_id: int,
        amount: int,
    ) -> Tuple[int, int]:
        economy_repo = EconomyRepository(session)
        transaction_repo = TransactionRepository(session)
        
        # Deduct from sender
        sender_economy = await economy_repo.subtract_balance(from_user_id, amount)
        await transaction_repo.create_transaction(
            user_id=from_user_id,
            amount=amount,
            type="debit",
            category="transfer_out",
            description=f"Transfer to {to_user_id}",
            reference_id=f"transfer_out_{from_user_id}_{datetime.utcnow().timestamp()}"
        )
        
        # Add to recipient
        recipient_economy = await economy_repo.add_balance(to_user_id, amount)
        await transaction_repo.create_transaction(
            user_id=to_user_id,
            amount=amount,
            type="credit",
            category="transfer_in",
            description=f"Transfer from {from_user_id}",
            reference_id=f"transfer_in_{to_user_id}_{datetime.utcnow().timestamp()}"
        )
        
        self.logger.info(
            "Tokens transferred",
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            amount=amount,
        )
        
        return sender_economy.balance, recipient_economy.balance

    async def get_profile(self, user_id: int) -> EconomyProfile:
        """Get full economy profile for user."""
        economy = await self.economy_repo.get_or_create(user_id)
        return EconomyProfile.model_validate(economy)


class FocusService(LoggerMixin):
    """Service handling focus sessions and productivity tracking."""
    
    def __init__(self, session: AsyncSession, db_instance=None) -> None:
        """
        Initialize service.
        
        Args:
            session: Database session
            db_instance: Optional Database manager instance
        """
        self.session = session
        self.db = db_instance or db
        self.user_repo = UserRepository(session)
        self.economy_repo = EconomyRepository(session)
        self.focus_repo = FocusSessionRepository(session)
        self.transaction_repo = TransactionRepository(session)
    
    async def start_session(
        self,
        user_id: int,
        username: str,
        discriminator: str,
        project_name: str,
    ) -> FocusSessionProfile:
        """Start new focus session."""
        if self.db and hasattr(self.db, '_session_factory') and self.db._session_factory:
             async with self.db.transaction() as session:
                return await self._start_session_logic(session, user_id, username, discriminator, project_name)
        else:
            return await self._start_session_logic(self.session, user_id, username, discriminator, project_name)

    async def _start_session_logic(self, session: AsyncSession, user_id: int, username: str, discriminator: str, project_name: str) -> FocusSessionProfile:
        user_repo = UserRepository(session)
        focus_repo = FocusSessionRepository(session)
        
        # Ensure user exists
        await user_repo.get_or_create(user_id, username, discriminator)
        
        # Check for active session
        active_session = await focus_repo.get_active_session(user_id)
        if active_session:
            raise SessionActiveException("focus")
        
        # Create session
        session_model = await focus_repo.create_session(user_id, project_name)
        
        self.logger.info(
            "Focus session started",
            user_id=user_id,
            project_name=project_name,
        )
        
        return FocusSessionProfile.model_validate(session_model)
    
    async def end_session(self, user_id: int) -> Tuple[FocusSessionProfile, int]:
        """End active focus session and calculate rewards."""
        if self.db and hasattr(self.db, '_session_factory') and self.db._session_factory:
             async with self.db.transaction() as session:
                return await self._end_session_logic(session, user_id)
        else:
            return await self._end_session_logic(self.session, user_id)

    async def _end_session_logic(self, session: AsyncSession, user_id: int) -> Tuple[FocusSessionProfile, int]:
        focus_repo = FocusSessionRepository(session)
        economy_repo = EconomyRepository(session)
        transaction_repo = TransactionRepository(session)
        
        # Get active session
        session_model = await focus_repo.get_active_session(user_id)
        if not session_model:
            raise SessionNotFoundException("focus")
        
        # Calculate duration
        duration_minutes = int((datetime.utcnow() - session_model.start_time).total_seconds() / 60)
        
        # Check for hyperfocus
        is_hyperfocus = duration_minutes >= settings.focus_hyperfocus_threshold
        
        # Calculate rewards
        base_reward = settings.focus_base_reward
        if is_hyperfocus:
            total_reward = int(base_reward * settings.focus_hyperfocus_multiplier)
            session_model.is_hyperfocus = True
        else:
            total_reward = base_reward
        
        # End session
        session_model = await focus_repo.end_session(session_model.id, total_reward)
        
        # Log Transaction
        await transaction_repo.create_transaction(
            user_id=user_id,
            amount=total_reward,
            type="credit",
            category="focus_session",
            description=f"Focus Session: {session_model.project_name} ({duration_minutes}m)",
            reference_id=f"focus_{session_model.id}"
        )
        
        # Add tokens to balance
        await economy_repo.add_balance(user_id, total_reward)
        
        self.logger.info(
            "Focus session ended",
            user_id=user_id,
            duration_minutes=duration_minutes,
            tokens_earned=total_reward,
            is_hyperfocus=is_hyperfocus,
        )
        
        return FocusSessionProfile.model_validate(session_model), total_reward
    
    async def get_active_session(self, user_id: int) -> Optional[FocusSessionProfile]:
        """Get user's active session profile."""
        session = await self.focus_repo.get_active_session(user_id)
        if not session:
            return None
        return FocusSessionProfile.model_validate(session)
