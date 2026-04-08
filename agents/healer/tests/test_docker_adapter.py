import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from agents.healer.adapters.docker_adapter import DockerAdapter

@pytest.fixture
def mock_docker():
    with patch("docker.from_env") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

@pytest.fixture
def mock_redis():
    with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_from_url:
        redis_client = AsyncMock()
        mock_from_url.return_value = redis_client
        
        # Pipeline is synchronous method returning a pipeline object
        pipeline_mock = MagicMock()
        redis_client.pipeline = MagicMock(return_value=pipeline_mock)
        
        # Pipeline methods return self for chaining
        pipeline_mock.incr.return_value = pipeline_mock
        pipeline_mock.expire.return_value = pipeline_mock
        
        # Execute is async
        pipeline_mock.execute = AsyncMock()
        
        yield redis_client

@pytest.mark.asyncio
async def test_get_container_success(mock_docker):
    # Setup mock
    container = MagicMock()
    container.attrs = {
        "State": {
            "Status": "running",
            "Health": {"Status": "healthy"},
            "StartedAt": "2024-01-01T00:00:00Z"
        },
        "RestartCount": 0
    }
    mock_docker.containers.get.return_value = container
    
    adapter = DockerAdapter()
    status = adapter.get_container("test_container")
    
    assert status is not None
    assert status.name == "test_container"
    assert status.status == "running"
    assert status.health == "healthy"

@pytest.mark.asyncio
async def test_restart_container_threshold(mock_docker, mock_redis):
    adapter = DockerAdapter()
    await adapter.get_redis() # Init redis
    
    # Case 1: Under threshold
    mock_redis.get.return_value = "2"
    container = MagicMock()
    mock_docker.containers.get.return_value = container
    
    success = await adapter.restart_container("test_container")
    
    assert success is True
    container.restart.assert_called_once()
    mock_redis.pipeline.return_value.incr.assert_called()

@pytest.mark.asyncio
async def test_restart_container_exceeded(mock_docker, mock_redis):
    adapter = DockerAdapter()
    await adapter.get_redis()
    
    # Case 2: Over threshold
    mock_redis.get.return_value = "3"
    
    success = await adapter.restart_container("test_container")
    
    assert success is False
    mock_docker.containers.get.assert_not_called()

@pytest.mark.asyncio
async def test_restart_container_force(mock_docker, mock_redis):
    adapter = DockerAdapter()
    await adapter.get_redis()
    
    # Case 3: Over threshold but forced
    mock_redis.get.return_value = "3"
    container = MagicMock()
    mock_docker.containers.get.return_value = container
    
    success = await adapter.restart_container("test_container", force=True)
    
    assert success is True
    container.restart.assert_called_once()
