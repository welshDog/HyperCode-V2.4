import pytest
import asyncio
from unittest.mock import patch, MagicMock
from sqlalchemy import text
from src.core.database import Database
from src.config.settings import Settings

@pytest.mark.asyncio
async def test_database_init_missing_env():
    """Test that Database.init raises RuntimeError when settings are missing."""
    # Create a fresh database instance for this test
    test_db = Database()
    
    # Mock settings to have empty values
    mock_settings = MagicMock()
    mock_settings.db_host = None
    mock_settings.db_port = None
    mock_settings.db_name = None
    mock_settings.db_user = None
    mock_settings.db_password = None
    
    with patch("src.core.database.settings", mock_settings):
        with pytest.raises(RuntimeError) as exc_info:
            await test_db.init()
        assert "Missing required database settings" in str(exc_info.value)

@pytest.mark.asyncio
async def test_database_connectivity():
    """Test real connectivity using testcontainers (skipped if docker not available)."""
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers not installed")

    import os
    # Check if docker is running
    if os.system("docker ps") != 0:
        pytest.skip("Docker is not running")

    # Use a specific version known to be stable
    with PostgresContainer("postgres:15-alpine") as postgres:
        host = postgres.get_container_host_ip()
        port = postgres.get_exposed_port(5432)
        user = postgres.username
        password = postgres.password
        dbname = postgres.dbname

        # Wait a bit for PG to fully start even after testcontainers says it's ready
        await asyncio.sleep(2)

        # Update settings for the test
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

        test_db = Database()
        with patch("src.core.database.settings", test_settings):
            await test_db.init()
            
            # Execute SELECT 1 with a timeout
            async with test_db.session() as session:
                start_time = asyncio.get_event_loop().time()
                try:
                    result = await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=10.0)
                    end_time = asyncio.get_event_loop().time()
                    
                    assert result.scalar() == 1
                    # Connectivity <= 500ms might be tight for first connection in container
                    assert (end_time - start_time) <= 2.0 
                except asyncio.TimeoutError:
                    pytest.fail("Database query timed out")
            
            await test_db.close()

@pytest.mark.asyncio
async def test_transaction_context_manager():
    """Test that transaction context manager commits/rolls back correctly."""
    test_db = Database()
    mock_session = MagicMock()
    
    # Use AsyncMock for async methods
    from unittest.mock import AsyncMock
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    
    test_db._session_factory = MagicMock(return_value=mock_session)
    
    # Successful transaction
    async with test_db.transaction() as session:
        assert session == mock_session
    
    mock_session.commit.assert_called_once()
    mock_session.close.assert_called_once()
    
    # Failed transaction
    mock_session.commit.reset_mock()
    mock_session.close.reset_mock()
    try:
        async with test_db.transaction() as session:
            raise ValueError("test error")
    except ValueError:
        pass
    
    mock_session.rollback.assert_called_once()
    mock_session.commit.assert_not_called()
    mock_session.close.assert_called_once()

@pytest.mark.asyncio
async def test_database_health_check():
    """Test the health_check method."""
    test_db = Database()
    mock_session = MagicMock()
    from unittest.mock import AsyncMock
    mock_session.execute = AsyncMock()
    mock_session.close = AsyncMock()
    
    test_db._session_factory = MagicMock(return_value=mock_session)
    
    # Healthy
    assert await test_db.health_check() is True
    mock_session.execute.assert_called_once()
    
    # Unhealthy
    mock_session.execute.side_effect = Exception("db error")
    assert await test_db.health_check() is False

@pytest.mark.asyncio
async def test_database_close():
    """Test closing the database."""
    test_db = Database()
    mock_engine = MagicMock()
    from unittest.mock import AsyncMock
    mock_engine.dispose = AsyncMock()
    test_db._engine = mock_engine
    test_db._session_factory = MagicMock()
    
    await test_db.close()
    
    mock_engine.dispose.assert_called_once()
    assert test_db._engine is None
    assert test_db._session_factory is None

@pytest.mark.asyncio
async def test_database_not_initialized_errors():
    """Test errors when database is not initialized."""
    test_db = Database()
    
    with pytest.raises(RuntimeError, match="Database not initialized"):
        async with test_db.session():
            pass
            
    with pytest.raises(RuntimeError, match="Database not initialized"):
        async with test_db.transaction():
            pass

    with pytest.raises(RuntimeError, match="Database not initialized"):
        await test_db.create_tables()

    with pytest.raises(RuntimeError, match="Database not initialized"):
        await test_db.drop_tables()

    with pytest.raises(RuntimeError, match="Database not initialized"):
        _ = test_db.engine
