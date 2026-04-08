import pytest
import asyncio
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer
from alembic.config import Config
from alembic import command
from src.config.settings import Settings
from src.core.database import Database

@pytest.mark.asyncio
async def test_migrations_roundtrip():
    """Test upgrade head -> downgrade base -> upgrade head cycle."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        host = postgres.get_container_host_ip()
        port = postgres.get_exposed_port(5432)
        user = postgres.username
        password = postgres.password
        dbname = postgres.dbname

        # Construct connection string for Alembic (Alembic env.py uses settings.database_url)
        # So we need to patch settings.database_url or use environment variables
        
        # Configure settings for the test
        test_settings = Settings(
            db_host=host,
            db_port=int(port),
            db_user=user,
            db_password=password,
            db_name=dbname,
            discord_token="test",
            secret_key="test",
            redis_url="redis://localhost:6379/0"
        )

        # Wait for Postgres to be ready
        await asyncio.sleep(5)

        # Patch settings and run Alembic
        from unittest.mock import patch
        with patch("src.config.settings.settings", test_settings):
            # Alembic config
            alembic_cfg = Config("alembic.ini")
            # The env.py will now use test_settings.database_url
            
            # 1. Upgrade to head
            command.upgrade(alembic_cfg, "head")

            # 2. Insert fixture data to verify tables exist
            test_db = Database()
            with patch("src.core.database.settings", test_settings):
                await test_db.init()
                async with test_db.session() as session:
                    await session.execute(text(
                        "INSERT INTO users (id, username, discriminator) VALUES (1, 'test', '0001')"
                    ))
                    await session.execute(text(
                        "INSERT INTO economy (user_id, balance) VALUES (1, 1000)"
                    ))
                    await session.commit()
                    
                    result = await session.execute(text("SELECT balance FROM economy WHERE user_id = 1"))
                    assert result.scalar() == 1000
                await test_db.close()

            # 3. Downgrade to base
            command.downgrade(alembic_cfg, "base")
            
            # Verify tables are gone
            with patch("src.core.database.settings", test_settings):
                await test_db.init()
                async with test_db.session() as session:
                    with pytest.raises(Exception):
                        await session.execute(text("SELECT * FROM users"))
                await test_db.close()

            # 4. Upgrade to head again
            command.upgrade(alembic_cfg, "head")
            
            # Verify tables are back
            with patch("src.core.database.settings", test_settings):
                await test_db.init()
                async with test_db.session() as session:
                    result = await session.execute(text("SELECT count(*) FROM users"))
                    assert result.scalar() == 0
                await test_db.close()
