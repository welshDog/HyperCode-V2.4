"""Retry utilities with exponential backoff for HyperAgent workers."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Tuple, Type


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, last_exception: BaseException, attempt_index: int):
        super().__init__(str(last_exception))
        self.last_exception = last_exception
        self.attempt_index = attempt_index


async def retry_with_backoff(
    func: Callable[..., Any],
    *args,
    max_retries: int = 3,
    backoff_base: float = 2.0,
    timeout: float | None = None,
    retry_exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    on_retry: Callable[[int, float], None] | None = None,
    **kwargs,
) -> Tuple[Any, int]:
    """Execute a function with exponential backoff retry.

    Args:
        func: The callable to retry (can be sync or async).
        *args: Positional arguments to pass to func.
        max_retries: Maximum number of retry attempts (default 3).
        backoff_base: Base for exponential backoff (default 2.0).
        timeout: Optional timeout for each attempt in seconds.
        retry_exceptions: Exception types to catch and retry on.
        on_retry: Optional callback called on each retry with (attempt_number, wait_time).
        **kwargs: Keyword arguments to pass to func.

    Returns:
        Tuple of (successful_result, attempt_index) where attempt_index is the
        loop attempt number (starting at 0) of the successful attempt.

    Raises:
        RetryError: If all retries are exhausted, contains the last exception
            and the attempt index of the last attempt (which will be max_retries).
    """
    last_exception: BaseException | None = None

    for attempt in range(max_retries + 1):
        if attempt > 0:
            wait_time = backoff_base ** attempt
            if on_retry is not None:
                on_retry(attempt, wait_time)
            await asyncio.sleep(wait_time)

        try:
            if asyncio.iscoroutinefunction(func):
                if timeout is not None:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs), timeout=timeout
                    )
                else:
                    result = await func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                if timeout is not None:
                    result = await asyncio.wait_for(
                        loop.run_in_executor(
                            None, lambda: func(*args, **kwargs)
                        ),
                        timeout=timeout,
                    )
                else:
                    result = await loop.run_in_executor(
                        None, lambda: func(*args, **kwargs)
                    )
            return result, attempt
        except retry_exceptions as exc:
            last_exception = exc
            # Retry logging is left to the caller if desired.
            continue

    # If we got here, all retries failed.
    raise RetryError(last_exception, attempt)  # type: ignore[raise-missing]
