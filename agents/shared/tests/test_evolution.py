import pytest
from unittest.mock import AsyncMock, MagicMock
from agents.shared.core.evolution_logic import EvolutionProtocol
from agents.shared.protocols.evolution import ImprovementRequest, ImprovementType

@pytest.mark.asyncio
async def test_submit_request_success():
    # Setup
    mock_redis = AsyncMock()
    
    # Create a pipeline mock that works as an async context manager
    mock_pipeline = AsyncMock()
    mock_pipeline.__aenter__.return_value = mock_pipeline
    mock_pipeline.__aexit__.return_value = None
    
    # Configure redis.pipeline() to act as an async context manager
    # The trick is that pipeline() itself is called, and then __aenter__ is called on the result.
    # If we make pipeline() return the mock_pipeline, and mock_pipeline has __aenter__, it works.
    
    # However, if pipeline() is mocked as an AsyncMock, calling it returns a coroutine.
    # We need to make sure that calling pipeline() returns a non-awaitable object (our mock_pipeline)
    # OR we need to make sure the await happens correctly if the code awaits it.
    
    # In the code: `async with self.redis.pipeline(...) as pipe:`
    # This expects `self.redis.pipeline(...)` to return an object that has `__aenter__`.
    # If `self.redis.pipeline` is an AsyncMock, calling it returns a coroutine.
    # `async with coroutine` is invalid.
    
    # So we must replace the pipeline method with a MagicMock (synchronous)
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)
    
    # Mock idempotency check (not duplicate)
    mock_redis.exists.return_value = False

    protocol = EvolutionProtocol(mock_redis)
    
    request = ImprovementRequest(
        agent_id="test-agent",
        target_agent="coder-agent",
        improvement_type=ImprovementType.BUG_FIX,
        description="Fixing a critical bug in the matrix",
        payload={"code": "print('hello')"},
        priority=1
    )

    # Execute
    success, req_id = await protocol.submit_request(request)

    # Verify
    assert success is True
    assert req_id == request.id
    
    # Check Pipeline Calls
    # Verify transaction was executed
    assert mock_pipeline.execute.called is True

@pytest.mark.asyncio
async def test_submit_request_duplicate():
    # Setup
    mock_redis = AsyncMock()
    # Mock idempotency check (IS duplicate)
    mock_redis.exists.return_value = True

    protocol = EvolutionProtocol(mock_redis)
    
    request = ImprovementRequest(
        agent_id="test-agent",
        target_agent="coder-agent",
        improvement_type=ImprovementType.BUG_FIX,
        description="Duplicate request",
        payload={"code": "print('hello')"},
        priority=1
    )

    # Execute
    success, msg = await protocol.submit_request(request)

    # Verify
    assert success is False
    assert "Duplicate" in msg
    mock_redis.pipeline.assert_not_called()

@pytest.mark.asyncio
async def test_invalid_request_schema():
    # This tests Pydantic validation indirectly via instantiation
    with pytest.raises(ValueError):
        ImprovementRequest(
            agent_id="test-agent",
            target_agent="coder-agent",
            # Missing improvement_type
            description="Short", # Too short
            payload={},
            priority=10 # Invalid priority
        )
