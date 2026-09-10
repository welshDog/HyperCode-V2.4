import asyncio
import pytest
from unittest.mock import AsyncMock, Mock

from src.agents.hyper_agents.retry_helper import retry_with_backoff, RetryError


@pytest.mark.asyncio
async def test_retry_with_backoff_success_first_attempt():
    """Function succeeds on first attempt, no retries."""
    func = Mock(return_value="success")
    result, attempt_index = await retry_with_backoff(func, max_retries=3)
    assert result == "success"
    assert attempt_index == 0
    assert func.call_count == 1


@pytest.mark.asyncio
async def test_retry_with_backoff_success_after_retries():
    """Function fails first two times, succeeds on third."""
    func = Mock()
    func.side_effect = [ValueError("fail"), ValueError("fail"), "success"]
    result, attempt_index = await retry_with_backoff(func, max_retries=3)
    assert result == "success"
    assert attempt_index == 2  # third attempt (0-indexed)
    assert func.call_count == 3


@pytest.mark.asyncio
async def test_retry_with_backoff_all_retries_fail():
    """Function fails all attempts, raises RetryError."""
    func = Mock()
    func.side_effect = ValueError("always fails")
    with pytest.raises(RetryError) as exc_info:
        await retry_with_backoff(func, max_retries=2)
    assert isinstance(exc_info.value.last_exception, ValueError)
    assert str(exc_info.value.last_exception) == "always fails"
    assert exc_info.value.attempt_index == 2  # last attempt index (0,1,2)
    assert func.call_count == 3  # tried 0,1,2


@pytest.mark.asyncio
async def test_retry_with_backoff_on_retry_callback():
    """on_retry callback is called with correct attempt and wait time."""
    func = Mock()
    func.side_effect = [ValueError("fail"), "success"]
    callback = Mock()
    await retry_with_backoff(func, max_retries=3, backoff_base=2.0, on_retry=callback)
    # Should be called once for attempt=1 (wait_time=2.0)
    callback.assert_called_once()
    args, _ = callback.call_args
    assert args[0] == 1  # attempt number
    assert args[1] == 2.0  # wait time


@pytest.mark.asyncio
async def test_retry_with_backoff_async_function():
    """Works with async function."""
    async def async_func():
        return "async success"
    result, attempt_index = await retry_with_backoff(async_func, max_retries=2)
    assert result == "async success"
    assert attempt_index == 0


@pytest.mark.asyncio
async def test_retry_with_backoff_async_function_retry():
    """Async function fails then succeeds."""
    call_count = 0
    async def async_func():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("fail")
        return "async success"
    result, attempt_index = await retry_with_backoff(async_func, max_retries=3)
    assert result == "async success"
    assert attempt_index == 1
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_with_backoff_timeout():
    """A slow attempt times out; with no retries left it raises RetryError."""
    async def slow_func():
        await asyncio.sleep(0.1)
        return "done"

    with pytest.raises(RetryError) as exc_info:
        await retry_with_backoff(slow_func, max_retries=0, timeout=0.01)
    assert isinstance(exc_info.value.last_exception, asyncio.TimeoutError)
    assert exc_info.value.attempt_index == 0


if __name__ == "__main__":
    pytest.main([__file__])
