"""
Docker Model Runner (DMR) Client for Agent X

Provides OpenAI-compatible interface to Docker Model Runner with:
- Automatic fallback to smaller models on timeout
- Streaming and non-streaming inference
- Built-in retry logic with exponential backoff
- Metrics collection (latency, tokens, fallback usage)
- Async-first design

Usage:
    from agentx.dmr_client import DMRClient
    
    async with DMRClient() as client:
        response = await client.infer("What is Docker?")
        async for chunk in client.infer_stream("Generate a Dockerfile"):
            print(chunk, end="")
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import AsyncIterator, Dict, Optional, Any
from collections import deque

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class InferenceMetric(BaseModel):
    """Single inference metric."""
    model: str
    latency_ms: float
    total_tokens: int
    fallback_used: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DMRHealthResponse(BaseModel):
    """Health check response from DMR."""
    status: str
    version: Optional[str] = None


# ============================================================================
# Exceptions
# ============================================================================

class DMRClientError(Exception):
    """Base error for DMR client."""
    pass


class InferenceTimeoutError(DMRClientError):
    """Inference exceeded timeout."""
    pass


class ModelNotAvailableError(DMRClientError):
    """Model not available or failed to load."""
    pass


# ============================================================================
# DMR Client
# ============================================================================

class DMRClient:
    """
    OpenAI-compatible Docker Model Runner client.
    
    Features:
    - Async-first (asyncio)
    - Automatic fallback to smaller models on timeout
    - Streaming and non-streaming inference
    - Retry logic with exponential backoff
    - Built-in metrics collection
    
    Args:
        host: DMR API endpoint (default: http://127.0.0.1:12434)
        primary_model: Primary model name (default: ai/qwen2.5-coder:7b-instruct-q4_k_m)
        fallback_model: Fallback model on timeout (default: ai/smollm2:360m-q4_k_m)
        inference_timeout_ms: Max inference time in ms (default: 300000 = 5 min)
        model_load_timeout_ms: Max model load time in ms (default: 300000 = 5 min)
        max_retries: Max retries on transient errors (default: 3)
        metrics_limit: Keep last N metrics (default: 100)
    """
    
    def __init__(
        self,
        host: str = "http://127.0.0.1:12434",
        primary_model: str = "ai/qwen2.5-coder:7b-instruct-q4_k_m",
        fallback_model: str = "ai/smollm2:360m-q4_k_m",
        inference_timeout_ms: int = 300_000,
        model_load_timeout_ms: int = 300_000,
        max_retries: int = 3,
        metrics_limit: int = 100,
    ):
        self.host = host.rstrip("/")
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.inference_timeout_ms = inference_timeout_ms
        self.model_load_timeout_ms = model_load_timeout_ms
        self.max_retries = max_retries
        self.metrics = deque(maxlen=metrics_limit)
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.debug(
            f"DMRClient initialized: host={host}, "
            f"primary={primary_model}, fallback={fallback_model}"
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
    
    async def _ensure_session(self) -> None:
        """Ensure aiohttp session is created."""
        if not self._session:
            self._session = aiohttp.ClientSession()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check DMR service health."""
        try:
            url = f"{self.host}/health"
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    return {"status": "healthy"}
                else:
                    return {"status": f"unhealthy (HTTP {resp.status})"}
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": f"error: {str(e)}"}
    
    async def preload_models(self) -> bool:
        """Preload models in background (returns immediately)."""
        try:
            await self._ensure_session()
            url = f"{self.host}/v1/models/preload"
            async with self._session.post(
                url,
                json={"models": [self.primary_model, self.fallback_model]},
                timeout=aiohttp.ClientTimeout(total=2),
            ) as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning(f"Model preload failed: {e}")
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def _call_api(
        self,
        model: str,
        messages: list,
        stream: bool = False,
        **kwargs,
    ) -> Any:
        """Call DMR API with retry logic."""
        await self._ensure_session()
        
        url = f"{self.host}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs,
        }
        
        start_time = time.time()
        
        try:
            timeout_sec = self.inference_timeout_ms / 1000.0
            async with self._session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout_sec),
            ) as resp:
                elapsed = (time.time() - start_time) * 1000
                
                if resp.status == 200:
                    if stream:
                        return resp
                    else:
                        data = await resp.json()
                        return data, elapsed
                elif resp.status == 503:
                    raise ModelNotAvailableError(f"Model {model} loading (HTTP 503)")
                elif resp.status == 429:
                    raise Exception(f"Rate limited (HTTP 429), retrying...")
                else:
                    text = await resp.text()
                    raise DMRClientError(f"HTTP {resp.status}: {text[:200]}")
        
        except asyncio.TimeoutError:
            raise InferenceTimeoutError(
                f"Inference timeout after {self.inference_timeout_ms}ms for model {model}"
            )
    
    async def infer(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_fallback: bool = True,
    ) -> str:
        """
        Non-streaming inference.
        
        Args:
            prompt: User prompt
            system_message: System message (optional)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Max tokens to generate (optional)
            use_fallback: Auto-fallback to smaller model on timeout
        
        Returns:
            Generated text
        
        Raises:
            InferenceTimeoutError: On timeout (unless fallback enabled)
            ModelNotAvailableError: Model not available
            DMRClientError: Other errors
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        kwargs = {"temperature": temperature}
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        # Try primary model
        try:
            data, elapsed = await self._call_api(
                self.primary_model,
                messages,
                stream=False,
                **kwargs,
            )
            response_text = data["choices"][0]["message"]["content"]
            total_tokens = data.get("usage", {}).get("total_tokens", 0)
            
            self.metrics.append(InferenceMetric(
                model=self.primary_model,
                latency_ms=elapsed,
                total_tokens=total_tokens,
                fallback_used=False,
            ))
            
            logger.info(
                f"Inference successful: model={self.primary_model}, "
                f"latency={elapsed:.0f}ms, tokens={total_tokens}"
            )
            return response_text
        
        except (InferenceTimeoutError, ModelNotAvailableError) as e:
            if not use_fallback:
                raise
            
            logger.warning(f"Primary model failed ({str(e)}), trying fallback...")
            
            # Try fallback model
            try:
                data, elapsed = await self._call_api(
                    self.fallback_model,
                    messages,
                    stream=False,
                    **kwargs,
                )
                response_text = data["choices"][0]["message"]["content"]
                total_tokens = data.get("usage", {}).get("total_tokens", 0)
                
                self.metrics.append(InferenceMetric(
                    model=self.fallback_model,
                    latency_ms=elapsed,
                    total_tokens=total_tokens,
                    fallback_used=True,
                ))
                
                logger.info(
                    f"Fallback inference successful: model={self.fallback_model}, "
                    f"latency={elapsed:.0f}ms, tokens={total_tokens}"
                )
                return response_text
            
            except Exception as fallback_error:
                logger.error(f"Fallback model also failed: {fallback_error}")
                raise DMRClientError(
                    f"Both primary and fallback models failed. "
                    f"Primary: {str(e)}, Fallback: {str(fallback_error)}"
                )
    
    async def infer_stream(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_fallback: bool = True,
    ) -> AsyncIterator[str]:
        """
        Streaming inference (yields tokens).
        
        Args:
            prompt: User prompt
            system_message: System message (optional)
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            use_fallback: Auto-fallback on timeout
        
        Yields:
            Token chunks
        
        Raises:
            InferenceTimeoutError: On timeout
            ModelNotAvailableError: Model not available
            DMRClientError: Other errors
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        kwargs = {"temperature": temperature}
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        start_time = time.time()
        total_tokens = 0
        fallback_used = False
        model_used = self.primary_model
        
        # Try primary model
        try:
            resp = await self._call_api(
                self.primary_model,
                messages,
                stream=True,
                **kwargs,
            )
            
            async for line in resp.content:
                if line:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            import json
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                total_tokens += 1
                                yield content
                        except json.JSONDecodeError:
                            pass
        
        except (InferenceTimeoutError, ModelNotAvailableError) as e:
            if not use_fallback:
                raise
            
            logger.warning(f"Primary stream failed ({str(e)}), trying fallback...")
            fallback_used = True
            model_used = self.fallback_model
            
            try:
                resp = await self._call_api(
                    self.fallback_model,
                    messages,
                    stream=True,
                    **kwargs,
                )
                
                async for line in resp.content:
                    if line:
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                import json
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    total_tokens += 1
                                    yield content
                            except json.JSONDecodeError:
                                pass
            
            except Exception as fallback_error:
                raise DMRClientError(
                    f"Both primary and fallback streams failed. "
                    f"Primary: {str(e)}, Fallback: {str(fallback_error)}"
                )
        
        finally:
            elapsed = (time.time() - start_time) * 1000
            self.metrics.append(InferenceMetric(
                model=model_used,
                latency_ms=elapsed,
                total_tokens=total_tokens,
                fallback_used=fallback_used,
            ))
            
            logger.info(
                f"Stream complete: model={model_used}, "
                f"latency={elapsed:.0f}ms, tokens={total_tokens}, "
                f"fallback={fallback_used}"
            )
    
    def get_metrics(self, limit: Optional[int] = None) -> list[Dict[str, Any]]:
        """
        Get recent metrics.
        
        Args:
            limit: Return last N metrics (default: all)
        
        Returns:
            List of metric dicts
        """
        metrics_list = list(self.metrics)
        if limit:
            metrics_list = metrics_list[-limit:]
        
        return [
            {
                "model": m.model,
                "latency_ms": m.latency_ms,
                "total_tokens": m.total_tokens,
                "fallback_used": m.fallback_used,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in metrics_list
        ]


# ============================================================================
# Convenience functions
# ============================================================================

async def quick_infer(
    prompt: str,
    host: str = "http://127.0.0.1:12434",
    **kwargs,
) -> str:
    """Quick inference (creates client, closes on done)."""
    async with DMRClient(host=host) as client:
        return await client.infer(prompt, **kwargs)
