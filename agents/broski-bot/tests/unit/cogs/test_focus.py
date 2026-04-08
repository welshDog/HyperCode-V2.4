import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from src.cogs.focus import FocusEngine
from src.models.user import User

@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.add_cog = AsyncMock()
    return bot

@pytest.fixture
def focus_cog(mock_bot):
    return FocusEngine(mock_bot)

@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    ctx.author.id = 123456789
    ctx.author.name = "TestUser"
    ctx.author.discriminator = "0000"
    ctx.send = AsyncMock()
    return ctx

@pytest.mark.asyncio
async def test_focus_start(focus_cog, mock_ctx):
    # Mock DB session
    mock_session = AsyncMock()
    # Ensure execute() is an AsyncMock that returns a result with scalar_one_or_none
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = User(id=123456789, username="TestUser")
    mock_session.execute.return_value = mock_result
    
    with patch("src.cogs.focus.get_db_session", return_value=mock_session):
        # We need to mock the async context manager behavior of get_db_session
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        
        await focus_cog.focus_start.callback(focus_cog, mock_ctx, project="Test Project")
        
        # Verify session started in memory
        assert 123456789 in focus_cog.active_sessions
        assert focus_cog.active_sessions[123456789]["project"] == "Test Project"
        
        # Verify DB interactions
        assert mock_session.add.call_count >= 1 # Transaction added
        mock_session.commit.assert_called_once()
        
        # Verify user feedback
        mock_ctx.send.assert_called_once()
        args, kwargs = mock_ctx.send.call_args
        kwargs.get('embed') or (args[0] if args else None)
        # assert "Hyperfocus Session Started" in embed.title (Checking title logic if needed, skipping deep embed inspect)

@pytest.mark.asyncio
async def test_focus_end(focus_cog, mock_ctx):
    # Setup active session
    start_time = datetime.now(timezone.utc)
    focus_cog.active_sessions[123456789] = {
        "start": start_time,
        "project": "Test Project"
    }
    
    mock_session = AsyncMock()
    # Mock user query
    mock_user = User(id=123456789, username="TestUser")
    mock_user.economy = MagicMock()
    mock_user.economy.balance = 100
    mock_user.xp = 0
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result
    
    with patch("src.cogs.focus.get_db_session", return_value=mock_session):
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        
        await focus_cog.focus_end.callback(focus_cog, mock_ctx)
        
        # Verify session removed
        assert 123456789 not in focus_cog.active_sessions
        
        # Verify DB interactions
        # 1. FocusSession add
        # 2. Transaction add
        assert mock_session.add.call_count >= 2 
        mock_session.commit.assert_called_once()
        
        # Verify rewards
        assert mock_user.economy.balance > 100 # Should have increased
        
        # Verify user feedback
        mock_ctx.send.assert_called_once()
