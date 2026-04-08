import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
import sys
import os

# Add parent directory to path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock arq before importing main/task_queue
mock_arq = MagicMock()
sys.modules["arq"] = mock_arq
sys.modules["arq.connections"] = MagicMock()
sys.modules["arq.worker"] = MagicMock()
sys.modules["crewai"] = MagicMock()

from main import app

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.lpush.return_value = True
    mock.ltrim.return_value = True
    mock.publish.return_value = True
    mock.delete.return_value = True
    # Mock pubsub for websocket tests if needed
    mock_pubsub = AsyncMock()
    mock_pubsub.subscribe.return_value = None
    mock_pubsub.listen.return_value = []
    mock.pubsub.return_value = mock_pubsub
    return mock

@pytest.fixture
def mock_httpx_response():
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"status": "success", "data": "mocked result"}
    response.text = '{"status": "success", "data": "mocked result"}'
    return response

@pytest_asyncio.fixture
async def client(mock_redis):
    # Patch the global redis_client in main
    with patch("main.redis_client", mock_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
