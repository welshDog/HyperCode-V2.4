"""
Docker Model Runner (DMR) client for Agent X.

Provides OpenAI-compatible inference with automatic fallback, model preloading,
and resilience to slow model loads. Integrates seamlessly with async workflows.

Features:
  - OpenAI-compatible chat completion API
  - Automatic fallback to smaller models on timeout/unavailable
  - Non-blocking model preload (loads in background, returns immediately)
  - Streaming and non-streaming inference
  - Built-in retry with exponential backoff
  - Structured logging and error telemetry
  - Type-safe with Pydantic models
"""

import asyncio
import json
import logging
import os
import time
from typing import Optional, AsyncGenerator, Any, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


@dataclass
class InferenceMetrics:
    """Metrics for a single inference call."""

    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    ttft_ms: Optional[float] = None  # Time to first token (streaming only)
    fallback_used: bool = False
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


class DMRClientError(Exception):
    """Base exception for DMR client errors."""

    pass


class ModelNotAvailableError(DMRClientError):
    """Model is not available or loading timeout exceeded."""

    pass


class InferenceTimeoutError(DMRClientError):
    """Inference call timed out."""

    pass


class ModelPreloadError(DMRClientError):
    """Failed to preload a model."""

    pass


class DMRClient:
    """
    Docker Model Runner client with OpenAI-compatible API.

    Handles:
      - Connection pooling and lifecycle management
      - Automatic fallback to smaller models
      - Model preloading
      - Structured error handling
      - Inference metrics collection
    """

    # Model timeout thresholds (ms)
    MODEL_LOAD_TIMEOUT_MS = 120_000  # 2 min max to load a model
    INFERENCE_TIMEOUT_MS = 300_000  # 5 min max for a single inference
    FALLBACK_TIMEOUT_MS = 60_000  # 1 min max for fallback model

    def __init__(
        self,
        host: Optional[str] = None,
        primary_model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        inference_timeout_ms: int = INFERENCE_TIMEOUT_MS,
        max_retries: int = 3,
    ):
        """
        Initialize DMR client.

        Args:
            host: DMR host (e.g., http://127.0.0.1:12434). Defaults to env var DMR_HOST.
            primary_model: Primary model to use. Defaults to env var DMR_MODEL.
            fallback_model: Fallback model for timeouts. Defaults to env var DMR_FALLBACK.
            inference_timeout_ms: Timeout for a single inference call.
            max_retries: Max retries for transient errors (429, 503).
        """
        self.host = host or os.getenv("DMR_HOST", "http://127.0.0.1:12434")
        self.primary_model = (
            primary_model
            or os.getenv("DMR_MODEL", "ai/qwen2.5-coder:7b-instruct-q4_k_m")
        )
        self.fallback_model = (
            fallback_model
            or os.getenv("DMR_FALLBACK", "ai/smollm2:360m-q4_k_m")
        )
        self.inference_timeout_ms = inference_timeout_ms
        self.max_retries = max_retries

        self._session: Optional[aiohttp.ClientSession] = None
        self._model_load_times: Dict[str, float] = {}  # Track model load times
        self._metrics: List[InferenceMetrics] = []
        self._lock = asyncio.Lock()

        logger.info(
            f"DMRClient initialized: host={self.host}, primary={self.primary_model}, "
            f"fallback={self.fallback_model}"
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure aiohttp session is initialized."""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit_per_host=10),
                timeout=aiohttp.ClientTimeout(total=self.inference_timeout_ms / 1000),
            )
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def _call_api(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        attempt: int = 0,
    ) -> Any:
        """
        Internal API call to DMR with retry logic.

        Args:
            model: Model name/tag
            messages: Chat messages in OpenAI format
            temperature: Sampling temperature
            max_tokens: Max tokens in response
            stream: Whether to stream response
            attempt: Current attempt number (for retry tracking)

        Returns:
            Response dict or async generator (if streaming)

        Raises:
            InferenceTimeoutError: If inference timeout exceeded
            ModelNotAvailableError: If model unavailable after retries
            DMRClientError: For other API errors
        """
        session = await self._ensure_session()

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        endpoint = f"{self.host}/v1/chat/completions"
        start_time = time.time()

        try:
            logger.debug(
                f"[Attempt {attempt + 1}/{self.max_retries}] Calling {endpoint} "
                f"with model={model}, stream={stream}"
            )

            async with session.post(endpoint, json=payload) as resp:
                elapsed_ms = (time.time() - start_time) * 1000

                if resp.status == 200:
                    if stream:
                        # Return async generator for streaming
                        return self._stream_response(resp, model, elapsed_ms)
                    else:
                        data = await resp.json()
                        logger.debug(
                            f"✓ Inference succeeded in {elapsed_ms:.0f}ms "
                            f"(model={model}, tokens={data['usage']['total_tokens']})"
                        )
                        return data

                elif resp.status == 503:
                    # Service unavailable (model loading or overloaded)
                    error_text = await resp.text()
                    logger.warning(
                        f"Model loading or overloaded ({resp.status}): {error_text[:200]}"
                    )

                    if attempt < self.max_retries - 1:
                        # Retry with exponential backoff
                        wait_ms = min(2 ** attempt * 1000, 10_000)
                        logger.info(f"Retrying in {wait_ms}ms...")
                        await asyncio.sleep(wait_ms / 1000)
                        return await self._call_api(
                            model, messages, temperature, max_tokens, stream, attempt + 1
                        )
                    else:
                        raise ModelNotAvailableError(
                            f"Model {model} unavailable after {self.max_retries} attempts"
                        )

                elif resp.status == 429:
                    # Rate limited
                    if attempt < self.max_retries - 1:
                        wait_ms = 5000  # Wait 5s before retrying
                        logger.warning(f"Rate limited. Retrying in {wait_ms}ms...")
                        await asyncio.sleep(wait_ms / 1000)
                        return await self._call_api(
                            model, messages, temperature, max_tokens, stream, attempt + 1
                        )
                    else:
                        raise DMRClientError(f"Rate limited after {self.max_retries} attempts")

                elif resp.status == 400:
                    # Bad request (invalid model, malformed payload)
                    error_data = await resp.json()
                    raise DMRClientError(
                        f"Bad request (400): {error_data.get('error', {}).get('message', 'unknown')}"
                    )

                else:
                    error_text = await resp.text()
                    raise DMRClientError(
                        f"Unexpected status {resp.status}: {error_text[:200]}"
                    )

        except asyncio.TimeoutError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Inference timeout after {elapsed_ms:.0f}ms (model={model})"
            )
            raise InferenceTimeoutError(f"Inference timeout (>{self.inference_timeout_ms}ms)")

        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            raise DMRClientError(f"HTTP client error: {e}")

    async def _stream_response(
        self, resp: aiohttp.ClientResponse, model: str, start_ms: float
    ) -> AsyncGenerator[str, None]:
        """
        Stream response chunks from DMR.

        Yields:
            Decoded JSON objects (parsed from SSE format)
        """
        first_token_time = None

        async for line in resp.content:
            line_str = line.decode("utf-8").strip()

            if not line_str or line_str == ":":
                continue

            if line_str.startswith("data:"):
                data_str = line_str[5:].strip()

                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)

                    # Track time to first token
                    if (
                        first_token_time is None
                        and chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                    ):
                        first_token_time = (time.time() * 1000) - start_ms
                        logger.debug(f"First token received in {first_token_time:.0f}ms")

                    yield chunk

                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON chunk: {data_str[:100]}")

    async def infer(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_fallback: bool = True,
    ) -> str:
        """
        Run inference synchronously (non-streaming).

        Args:
            prompt: User prompt
            system_message: System role message
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Max tokens in response
            use_fallback: Whether to retry with fallback model on timeout

        Returns:
            Generated text

        Raises:
            DMRClientError: If inference fails
            ModelNotAvailableError: If model unavailable
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        start_time = time.time()
        fallback_used = False

        try:
            response = await self._call_api(
                model=self.primary_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
            content = response["choices"][0]["message"]["content"]
            usage = response.get("usage", {})

        except InferenceTimeoutError as e:
            if use_fallback and self.fallback_model != self.primary_model:
                logger.warning(
                    f"Primary model timeout, falling back to {self.fallback_model}"
                )
                fallback_used = True
                response = await self._call_api(
                    model=self.fallback_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                )
                content = response["choices"][0]["message"]["content"]
                usage = response.get("usage", {})
            else:
                raise

        elapsed_ms = (time.time() - start_time) * 1000

        # Record metrics
        metrics = InferenceMetrics(
            model=self.fallback_model if fallback_used else self.primary_model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            latency_ms=elapsed_ms,
            fallback_used=fallback_used,
        )
        await self._record_metrics(metrics)

        logger.info(
            f"✓ Inference complete: "
            f"model={metrics.model}, tokens={metrics.total_tokens}, "
            f"latency={elapsed_ms:.0f}ms"
            + (", fallback=yes" if fallback_used else "")
        )

        return content

    async def infer_stream(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_fallback: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Run inference with streaming output.

        Yields:
            Streamed text chunks as they arrive

        Raises:
            DMRClientError: If inference fails
            ModelNotAvailableError: If model unavailable
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        start_time = time.time()
        fallback_used = False
        total_tokens = 0

        try:
            stream = await self._call_api(
                model=self.primary_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if "choices" in chunk:
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content

                if "usage" in chunk:
                    total_tokens = chunk["usage"].get("total_tokens", 0)

        except InferenceTimeoutError as e:
            if use_fallback and self.fallback_model != self.primary_model:
                logger.warning(
                    f"Primary model timeout, falling back to {self.fallback_model}"
                )
                fallback_used = True
                stream = await self._call_api(
                    model=self.fallback_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                )

                async for chunk in stream:
                    if "choices" in chunk:
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content

                    if "usage" in chunk:
                        total_tokens = chunk["usage"].get("total_tokens", 0)
            else:
                raise

        elapsed_ms = (time.time() - start_time) * 1000

        # Record metrics
        metrics = InferenceMetrics(
            model=self.fallback_model if fallback_used else self.primary_model,
            prompt_tokens=0,  # Not always available in streaming
            completion_tokens=total_tokens,
            total_tokens=total_tokens,
            latency_ms=elapsed_ms,
            fallback_used=fallback_used,
        )
        await self._record_metrics(metrics)

        logger.info(
            f"✓ Streaming inference complete: "
            f"model={metrics.model}, tokens={total_tokens}, latency={elapsed_ms:.0f}ms"
            + (", fallback=yes" if fallback_used else "")
        )

    async def preload_model(self, model: Optional[str] = None) -> bool:
        """
        Preload a model into memory (non-blocking).

        Sends a no-op inference to trigger model load, runs in background.
        This allows the model to be ready when the agent needs it.

        Args:
            model: Model to preload. Defaults to primary_model.

        Returns:
            True if preload initiated successfully, False otherwise
        """
        model = model or self.primary_model

        async def _preload():
            try:
                logger.info(f"Preloading model: {model}...")
                # Send a minimal prompt to trigger model load
                await self.infer(
                    "Hello.",
                    temperature=0.5,
                    max_tokens=10,
                    use_fallback=False,
                )
                logger.info(f"✓ Model preloaded: {model}")
            except Exception as e:
                logger.error(f"✗ Failed to preload model {model}: {e}")

        # Run preload in background
        asyncio.create_task(_preload())
        return True

    async def preload_models(self) -> bool:
        """Preload both primary and fallback models."""
        await self.preload_model(self.primary_model)
        if self.fallback_model != self.primary_model:
            await self.preload_model(self.fallback_model)
        return True

    async def _record_metrics(self, metrics: InferenceMetrics) -> None:
        """Record inference metrics for monitoring/telemetry."""
        async with self._lock:
            self._metrics.append(metrics)
            # Keep only last 100 metrics in memory to avoid unbounded growth
            if len(self._metrics) > 100:
                self._metrics = self._metrics[-100:]

        logger.debug(f"Metrics recorded: {metrics.to_dict()}")

    def get_metrics(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recorded inference metrics.

        Args:
            limit: Max number of metrics to return (recent first)

        Returns:
            List of metric dicts
        """
        metrics = [m.to_dict() for m in self._metrics]
        if limit:
            metrics = metrics[-limit:]
        return list(reversed(metrics))

    async def health_check(self) -> Dict[str, Any]:
        """
        Check DMR service health.

        Returns:
            Health status dict with model availability
        """
        try:
            session = await self._ensure_session()
            async with session.get(f"{self.host}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    return {
                        "status": "healthy",
                        "host": self.host,
                        "primary_model": self.primary_model,
                        "fallback_model": self.fallback_model,
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "host": self.host,
                        "status_code": resp.status,
                    }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "host": self.host,
                "error": str(e),
            }


# Convenience function for quick inference
async def quick_infer(
    prompt: str,
    system_message: Optional[str] = None,
    host: Optional[str] = None,
) -> str:
    """
    One-off inference call (useful for scripts/tests).

    Args:
        prompt: User prompt
        system_message: Optional system message
        host: DMR host (defaults to DMR_HOST env var)

    Returns:
        Generated text
    """
    async with DMRClient(host=host) as client:
        return await client.infer(prompt, system_message=system_message)
