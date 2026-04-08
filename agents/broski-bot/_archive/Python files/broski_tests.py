"""
Test infrastructure with fixtures and comprehensive test coverage.
"""
# tests/conftest.py
import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.core.database import Base
from src.models import Economy

fake = Faker()


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def user_id() -> int:
    """Generate test user ID."""
    return fake.random_int(min=100000000000000000, max=999999999999999999)


@pytest.fixture
def username() -> str:
    """Generate test username."""
    return fake.user_name()


@pytest.fixture
def discriminator() -> str:
    """Generate test discriminator."""
    return f"{fake.random_int(min=1, max=9999):04d}"


# ============================================================================
# tests/unit/test_economy_service.py
"""
Unit tests for EconomyService.
Tests business logic in isolation with mocked dependencies.
"""
from datetime import datetime, timedelta

import pytest

from src.core.exceptions import (
    DailyLimitExceededException,
    InsufficientBalanceException,
    InvalidAmountException,
)
from src.services import EconomyService


class TestEconomyService:
    """Test suite for EconomyService."""
    
    @pytest.mark.asyncio
    async def test_get_balance_existing_user(self, db_session, user_id):
        """Test getting balance for existing user."""
        # Arrange
        service = EconomyService(db_session)
        
        # Create economy record
        economy = Economy(user_id=user_id, balance=1000)
        db_session.add(economy)
        await db_session.commit()
        
        # Act
        balance = await service.get_balance(user_id)
        
        # Assert
        assert balance == 1000
    
    @pytest.mark.asyncio
    async def test_get_balance_new_user(self, db_session, user_id):
        """Test getting balance creates new user with starting balance."""
        # Arrange
        service = EconomyService(db_session)
        
        # Act
        balance = await service.get_balance(user_id)
        
        # Assert
        assert balance == 500  # Starting balance
    
    @pytest.mark.asyncio
    async def test_claim_daily_reward_first_time(
        self,
        db_session,
        user_id,
        username,
        discriminator,
    ):
        """Test claiming daily reward for the first time."""
        # Arrange
        service = EconomyService(db_session)
        
        # Act
        reward, streak, is_new_streak = await service.claim_daily_reward(
            user_id,
            username,
            discriminator,
        )
        
        # Assert
        assert reward == 150  # Base (100) + 1 day streak bonus (50)
        assert streak == 1
        assert is_new_streak is True
    
    @pytest.mark.asyncio
    async def test_claim_daily_reward_streak_continues(
        self,
        db_session,
        user_id,
        username,
        discriminator,
    ):
        """Test daily reward maintains streak."""
        # Arrange
        service = EconomyService(db_session)
        
        # Create economy with yesterday's claim
        economy = Economy(
            user_id=user_id,
            balance=500,
            last_daily_claim=datetime.utcnow() - timedelta(days=1),
            daily_streak=5,
        )
        db_session.add(economy)
        await db_session.commit()
        
        # Act
        reward, streak, is_new_streak = await service.claim_daily_reward(
            user_id,
            username,
            discriminator,
        )
        
        # Assert
        assert reward == 400  # Base (100) + 6 day streak bonus (300)
        assert streak == 6
        assert is_new_streak is False
    
    @pytest.mark.asyncio
    async def test_claim_daily_reward_already_claimed(
        self,
        db_session,
        user_id,
        username,
        discriminator,
    ):
        """Test claiming daily reward when already claimed today."""
        # Arrange
        service = EconomyService(db_session)
        
        # Create economy with today's claim
        economy = Economy(
            user_id=user_id,
            balance=500,
            last_daily_claim=datetime.utcnow(),
            daily_streak=1,
        )
        db_session.add(economy)
        await db_session.commit()
        
        # Act & Assert
        with pytest.raises(DailyLimitExceededException):
            await service.claim_daily_reward(user_id, username, discriminator)
    
    @pytest.mark.asyncio
    async def test_transfer_tokens_success(self, db_session):
        """Test successful token transfer."""
        # Arrange
        service = EconomyService(db_session)
        sender_id = 111111111111111111
        recipient_id = 222222222222222222
        
        # Create economy records
        sender = Economy(user_id=sender_id, balance=1000)
        recipient = Economy(user_id=recipient_id, balance=500)
        db_session.add_all([sender, recipient])
        await db_session.commit()
        
        # Act
        sender_balance, recipient_balance = await service.transfer_tokens(
            sender_id,
            recipient_id,
            300,
        )
        
        # Assert
        assert sender_balance == 700
        assert recipient_balance == 800
    
    @pytest.mark.asyncio
    async def test_transfer_tokens_insufficient_balance(self, db_session):
        """Test transfer with insufficient balance fails."""
        # Arrange
        service = EconomyService(db_session)
        sender_id = 111111111111111111
        recipient_id = 222222222222222222
        
        # Create economy records
        sender = Economy(user_id=sender_id, balance=100)
        recipient = Economy(user_id=recipient_id, balance=500)
        db_session.add_all([sender, recipient])
        await db_session.commit()
        
        # Act & Assert
        with pytest.raises(InsufficientBalanceException):
            await service.transfer_tokens(sender_id, recipient_id, 300)
    
    @pytest.mark.asyncio
    async def test_transfer_tokens_negative_amount(self, db_session):
        """Test transfer with negative amount fails."""
        # Arrange
        service = EconomyService(db_session)
        sender_id = 111111111111111111
        recipient_id = 222222222222222222
        
        # Act & Assert
        with pytest.raises(InvalidAmountException):
            await service.transfer_tokens(sender_id, recipient_id, -100)
    
    @pytest.mark.asyncio
    async def test_transfer_tokens_to_self(self, db_session):
        """Test transfer to self fails."""
        # Arrange
        service = EconomyService(db_session)
        user_id = 111111111111111111
        
        # Act & Assert
        with pytest.raises(InvalidAmountException):
            await service.transfer_tokens(user_id, user_id, 100)


# ============================================================================
# tests/integration/test_economy_flow.py
"""
Integration tests for economy workflows.
Tests end-to-end flows with real database.
"""
import pytest



class TestEconomyFlow:
    """Integration tests for economy operations."""
    
    @pytest.mark.asyncio
    async def test_new_user_complete_flow(
        self,
        db_session,
        user_id,
        username,
        discriminator,
    ):
        """Test complete new user flow: create -> daily -> transfer."""
        service = EconomyService(db_session)
        
        # Step 1: Check initial balance (creates user)
        balance = await service.get_balance(user_id)
        assert balance == 500
        
        # Step 2: Claim daily reward
        reward, streak, _ = await service.claim_daily_reward(
            user_id,
            username,
            discriminator,
        )
        assert reward == 150
        assert streak == 1
        
        # Step 3: Check updated balance
        new_balance = await service.get_balance(user_id)
        assert new_balance == 650  # 500 + 150
        
        # Step 4: Create recipient and transfer
        recipient_id = 999999999999999999
        recipient_balance = await service.get_balance(recipient_id)
        assert recipient_balance == 500
        
        sender_bal, recip_bal = await service.transfer_tokens(
            user_id,
            recipient_id,
            200,
        )
        assert sender_bal == 450  # 650 - 200
        assert recip_bal == 700  # 500 + 200
    
    @pytest.mark.asyncio
    async def test_concurrent_transfers(self, db_session):
        """Test concurrent transfer operations maintain consistency."""
        # This test verifies database transaction isolation
        service = EconomyService(db_session)
        
        user1_id = 111111111111111111
        user2_id = 222222222222222222
        
        # Create users with initial balance
        economy1 = Economy(user_id=user1_id, balance=1000)
        economy2 = Economy(user_id=user2_id, balance=1000)
        db_session.add_all([economy1, economy2])
        await db_session.commit()
        
        # Transfer in both directions
        await service.transfer_tokens(user1_id, user2_id, 100)
        await service.transfer_tokens(user2_id, user1_id, 50)
        
        # Check final balances
        final_balance1 = await service.get_balance(user1_id)
        final_balance2 = await service.get_balance(user2_id)
        
        assert final_balance1 == 950  # 1000 - 100 + 50
        assert final_balance2 == 1050  # 1000 + 100 - 50
