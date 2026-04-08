import pytest
import asyncio
from unittest.mock import patch
from testcontainers.postgres import PostgresContainer
from alembic.config import Config
from alembic import command
from src.config.settings import Settings
from src.core.database import Database
from src.services.economy import EconomyService
from src.core.exceptions import InsufficientBalanceException

@pytest.mark.asyncio
async def test_economy_service_e2e():
    """End-to-end test for EconomyService with real Postgres and Alembic."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        host = postgres.get_container_host_ip()
        port = postgres.get_exposed_port(5432)
        user = postgres.username
        password = postgres.password
        dbname = postgres.dbname

        # Configure settings for the test
        test_settings = Settings(
            db_host=host,
            db_port=int(port),
            db_user=user,
            db_password=password,
            db_name=dbname,
            discord_token="test",
            secret_key="test",
            redis_url="redis://localhost:6379/0",
            economy_starting_balance=500,
            economy_daily_reward=100,
            economy_daily_streak_bonus=10
        )

        await asyncio.sleep(5)

        # 1. Run Migrations
        alembic_cfg = Config("alembic.ini")
        with patch("src.config.settings.settings", test_settings):
            command.upgrade(alembic_cfg, "head")

        # 2. Test EconomyService
        test_db = Database()
        with patch("src.core.database.settings", test_settings), \
             patch("src.config.settings.settings", test_settings), \
             patch("src.core.database.db", test_db):
            
            await test_db.init()
            
            async with test_db.session() as session:
                service = EconomyService(session, db_instance=test_db)
                
                # Create user and claim daily
                reward, streak, is_new = await service.claim_daily_reward(123, "broski", "0001")
                assert reward == 150 # 100 base + 50 bonus (streak 1)
                assert streak == 1
                assert is_new is True
                
                # Verify balance
                balance = await service.get_balance(123)
                assert balance == 650 # 500 starting + 150 reward
                
                # Create recipient and transfer
                await service.claim_daily_reward(456, "recipient", "0002")
                sender_bal, recv_bal = await service.transfer_tokens(123, 456, 100)
                
                assert sender_bal == 550
                assert recv_bal == 750 # 500 + 150 + 100
                
                # Test Atomicity / Rollback
                # Attempt to transfer more than available
                with pytest.raises(InsufficientBalanceException):
                    await service.transfer_tokens(123, 456, 1000)
                
                # Verify balances didn't change after failed transfer
                assert await service.get_balance(123) == 550
                assert await service.get_balance(456) == 750

            await test_db.close()
