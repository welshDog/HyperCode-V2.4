import pytest
import asyncio
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer
from alembic.config import Config
from alembic import command

from src.config.settings import Settings
from src.core.database import Database
from src.api.main import app

@pytest.mark.asyncio
async def test_economy_api_e2e():
    """End-to-end test for Economy API and Services."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        host = postgres.get_container_host_ip()
        port = postgres.get_exposed_port(5432)
        user = postgres.username
        password = postgres.password
        dbname = postgres.dbname

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
        )

        await asyncio.sleep(5)

        # 1. Run Migrations
        alembic_cfg = Config("alembic.ini")
        # Need to patch settings inside alembic env if possible, or use env vars
        # Here we just run upgrade head, assuming env.py handles connection string via settings
        with patch("src.config.settings.settings", test_settings):
            command.upgrade(alembic_cfg, "head")

        # 2. Initialize DB
        test_db = Database()
        
        # Patch everything
        with patch("src.core.database.settings", test_settings), \
             patch("src.config.settings.settings", test_settings), \
             patch("src.core.database.db", test_db), \
             patch("src.api.routes.economy.db", test_db), \
             patch("src.services.economy.db", test_db), \
             patch("src.api.main.db", test_db):
        
            await test_db.init()
            
            # Helper to create user
            async with test_db.session() as session:
                await session.execute(text("INSERT INTO users (id, username, discriminator) VALUES (1, 'test', '0001')"))
                await session.execute(text("INSERT INTO economy (user_id, balance) VALUES (1, 1000)"))
                await session.commit()

            # Create Async Client
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Test GET /economy/balance/{user_id}
                response = await client.get("/economy/balance/1")
                assert response.status_code == 200
                assert response.json() == {"user_id": 1, "balance": 1000}
                
                # Test POST /economy/redeem
                redeem_data = {"user_id": 1, "amount": 100, "description": "Test Redeem"}
                response = await client.post("/economy/redeem", json=redeem_data)
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert data["new_balance"] == 900
                
                # Verify Transaction Record
                async with test_db.session() as session:
                    result = await session.execute(text("SELECT count(*) FROM transactions WHERE user_id = 1 AND type = 'debit'"))
                    assert result.scalar() == 1
                
                # Test Idempotency (Same request)
                # Note: reference_id logic in API is dynamic if not passed.
                # In the API route: reference_id=f"redeem_{request.user_id}_{request.amount}_{request.description}"
                # So repeating the same request (same amount/desc) produces SAME reference_id.
                response = await client.post("/economy/redeem", json=redeem_data)
                assert response.status_code == 200
                data = response.json()
                assert data["new_balance"] == 900 # Balance shouldn't change
                
                # Verify Transaction Count is still 1
                async with test_db.session() as session:
                    result = await session.execute(text("SELECT count(*) FROM transactions WHERE user_id = 1 AND type = 'debit'"))
                    assert result.scalar() == 1
            
            await test_db.close()
