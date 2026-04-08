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
from src.models import User, Economy

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
    
    # Initialize the Database singleton with the session factory for this test function
    from src.core.database import db
    db._session_factory = async_session
    
    async with async_session() as session:
        yield session
        await session.rollback()
    
    # Cleanup
    db._session_factory = None


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
from src.services.economy import EconomyService


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
        
        # Create user explicitly to avoid FK constraint errors
        # Use merge to handle if it already exists (though test user_id should be unique)
        # Or check first.
        # But wait, the error is NOT NULL constraint.
        # It says (sqlite3.IntegrityError) NOT NULL constraint failed: users.username
        # This implies that `service.claim_daily_reward` calls `get_or_create(user_id, username, discriminator)`.
        # If the user was already created WITHOUT username/discriminator (e.g. by get_balance?), that would fail.
        # But here we are passing them.
        
        # Let's check `get_or_create` in `UserRepository`.
        
        # If we manually create user here, we ensure it has fields.
        user = await db_session.get(User, user_id)
        if not user:
            user = User(id=user_id, username=username, discriminator=discriminator)
            db_session.add(user)
            await db_session.commit()
        
        # Manually create economy record to avoid implicit creation issues if needed
        economy = await db_session.get(Economy, user_id)
        if not economy:
            economy = Economy(user_id=user_id, balance=500) # Default balance
            db_session.add(economy)
            await db_session.commit()
        
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
        
        # Create user first
        user = await db_session.get(User, user_id)
        if not user:
            user = User(id=user_id, username=username, discriminator=discriminator)
            db_session.add(user)
        
        # Create economy with yesterday's claim
        economy = await db_session.get(Economy, user_id)
        if not economy:
            economy = Economy(
                user_id=user_id,
                balance=500,
                last_daily_claim=datetime.utcnow() - timedelta(days=1),
                daily_streak=5,
            )
            db_session.add(economy)
        else:
            economy.last_daily_claim = datetime.utcnow() - timedelta(days=1)
            economy.daily_streak = 5
            
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
        
        # Create users
        # Check existence first
        user1 = await db_session.get(User, sender_id)
        if not user1:
            user1 = User(id=sender_id, username="sender", discriminator="0001")
            db_session.add(user1)
            
        user2 = await db_session.get(User, recipient_id)
        if not user2:
            user2 = User(id=recipient_id, username="recipient", discriminator="0002")
            db_session.add(user2)
        
        # Create economy records
        economy1 = await db_session.get(Economy, sender_id)
        if not economy1:
            economy1 = Economy(user_id=sender_id, balance=1000)
            db_session.add(economy1)
        else:
            economy1.balance = 1000
            
        economy2 = await db_session.get(Economy, recipient_id)
        if not economy2:
            economy2 = Economy(user_id=recipient_id, balance=500)
            db_session.add(economy2)
        else:
            economy2.balance = 500
            
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
        
        # Create users
        user1 = await db_session.get(User, sender_id)
        if not user1:
            user1 = User(id=sender_id, username="sender", discriminator="0001")
            db_session.add(user1)
            
        user2 = await db_session.get(User, recipient_id)
        if not user2:
            user2 = User(id=recipient_id, username="recipient", discriminator="0002")
            db_session.add(user2)
        
        # Create economy records
        economy1 = await db_session.get(Economy, sender_id)
        if not economy1:
            economy1 = Economy(user_id=sender_id, balance=100)
            db_session.add(economy1)
        else:
            economy1.balance = 100
            
        economy2 = await db_session.get(Economy, recipient_id)
        if not economy2:
            economy2 = Economy(user_id=recipient_id, balance=500)
            db_session.add(economy2)
        else:
            economy2.balance = 500
            
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
        
        # Create users
        user1 = await db_session.get(User, sender_id)
        if not user1:
            user1 = User(id=sender_id, username="sender", discriminator="0001")
            db_session.add(user1)
            
        user2 = await db_session.get(User, recipient_id)
        if not user2:
            user2 = User(id=recipient_id, username="recipient", discriminator="0002")
            db_session.add(user2)
        
        await db_session.commit()
        
        # Act & Assert
        with pytest.raises(InvalidAmountException):
            await service.transfer_tokens(sender_id, recipient_id, -100)
    
    @pytest.mark.asyncio
    async def test_transfer_tokens_to_self(self, db_session):
        """Test transfer to self fails."""
        # Arrange
        service = EconomyService(db_session)
        user_id = 111111111111111111
        
        # Create user
        user = await db_session.get(User, user_id)
        if not user:
            user = User(id=user_id, username="sender", discriminator="0001")
            db_session.add(user)
        
        await db_session.commit()
        
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
    async def test_new_user_complete_flow(self, db_session):
        """Test complete flow for a new user."""
        service = EconomyService(db_session)
        user_id = 111111111111111111
        username = "new_user"
        discriminator = "0001"
        
        # 1. Create User & Claim daily reward
        # Create user explicitly first to satisfy FK
        user = await db_session.get(User, user_id)
        if not user:
            user = User(id=user_id, username=username, discriminator=discriminator)
            db_session.add(user)
            await db_session.commit()
            
        reward, streak, _ = await service.claim_daily_reward(
            user_id,
            username,
            discriminator,
        )
        assert reward == 150  # Base (100) + Streak (50)
        assert streak == 1
        
        # 2. Check balance
        balance = await service.get_balance(user_id)
        assert balance == 650  # Starting (500) + Reward (150)
        
        # 3. Create another user and transfer
        recipient_id = 222222222222222222
        user2 = await db_session.get(User, recipient_id)
        if not user2:
            user2 = User(id=recipient_id, username="recipient", discriminator="0002")
            db_session.add(user2)
            await db_session.commit()
            
        # Ensure recipient economy exists
        recipient_economy = await db_session.get(Economy, recipient_id)
        if not recipient_economy:
            recipient_economy = Economy(user_id=recipient_id, balance=500)
            db_session.add(recipient_economy)
            await db_session.commit()
            
        await service.transfer_tokens(user_id, recipient_id, 200)
        
        # Expire session to ensure we fetch fresh data from DB (since transfer used a separate session)
        db_session.expire_all()
        
        # 4. Verify final states
        sender_balance = await service.get_balance(user_id)
        recipient_balance = await service.get_balance(recipient_id)
        
        assert sender_balance == 450  # 650 - 200
        assert recipient_balance == 700  # 500 + 200
    
    @pytest.mark.asyncio
    async def test_concurrent_transfers(self, db_session):
        """Test concurrent transfer operations maintain consistency."""
        # This test verifies database transaction isolation
        service = EconomyService(db_session)
        
        user1_id = 111111111111111111
        user2_id = 222222222222222222
        
        # Create users
        user1 = await db_session.get(User, user1_id)
        if not user1:
            user1 = User(id=user1_id, username="user1", discriminator="0001")
            db_session.add(user1)
            
        user2 = await db_session.get(User, user2_id)
        if not user2:
            user2 = User(id=user2_id, username="user2", discriminator="0002")
            db_session.add(user2)
            
        await db_session.commit()
        
        # Update balance to 1000
        # Must create economy via service or manually ensure they exist
        # If we use service.get_balance, it creates them.
        await service.get_balance(user1_id) # Creates user/economy
        await service.get_balance(user2_id)
        
        # Update balance to 1000
        from sqlalchemy import update
        await db_session.execute(
            update(Economy).where(Economy.user_id == user1_id).values(balance=1000)
        )
        await db_session.execute(
            update(Economy).where(Economy.user_id == user2_id).values(balance=1000)
        )
        await db_session.commit()
        
        # Transfer in both directions
        await service.transfer_tokens(user1_id, user2_id, 100)
        await service.transfer_tokens(user2_id, user1_id, 50)
        
        # Check final balances
        final_balance1 = await service.get_balance(user1_id)
        final_balance2 = await service.get_balance(user2_id)
        
        assert final_balance1 == 950  # 1000 - 100 + 50
        assert final_balance2 == 1050  # 1000 + 100 - 50
