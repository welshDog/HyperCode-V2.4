"""
Agent X + Docker Model Runner Integration Examples

Shows how to integrate DMRClient into Agent X:
- AgentXLLMBridge: LLM interface adapter
- FastAPI integration
- Main loop example
- Streaming example
"""

import asyncio
import logging
from typing import AsyncIterator, Optional
from dataclasses import dataclass

from agentx.dmr_client import DMRClient, InferenceTimeoutError, ModelNotAvailableError

logger = logging.getLogger(__name__)


# ============================================================================
# Bridge Layer: AgentXLLMBridge
# ============================================================================

@dataclass
class LLMConfig:
    """Configuration for LLM."""
    host: str = "http://127.0.0.1:12434"
    primary_model: str = "ai/qwen2.5-coder:7b-instruct-q4_k_m"
    fallback_model: str = "ai/smollm2:360m-q4_k_m"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    use_fallback: bool = True


class AgentXLLMBridge:
    """
    Bridge between Agent X and Docker Model Runner.
    
    Replaces Ollama client. Drop-in replacement for existing LLM calls.
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client: Optional[DMRClient] = None
    
    async def startup(self) -> None:
        """Initialize DMR client on Agent X startup."""
        self.client = DMRClient(
            host=self.config.host,
            primary_model=self.config.primary_model,
            fallback_model=self.config.fallback_model,
        )
        await self.client._ensure_session()
        
        # Preload models in background
        success = await self.client.preload_models()
        logger.info(f"DMR models preload: {success}")
    
    async def shutdown(self) -> None:
        """Cleanup DMR client on Agent X shutdown."""
        if self.client and self.client._session:
            await self.client._session.close()
    
    async def infer(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Non-streaming inference.
        
        Usage:
            response = await llm_bridge.infer("Write a Dockerfile for a Python app")
        """
        if not self.client:
            raise RuntimeError("LLM bridge not initialized. Call startup() first.")
        
        try:
            return await self.client.infer(
                prompt=prompt,
                system_message=system_message,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                use_fallback=self.config.use_fallback,
            )
        except InferenceTimeoutError as e:
            logger.error(f"Inference timeout: {e}")
            raise
        except ModelNotAvailableError as e:
            logger.error(f"Model not available: {e}")
            raise
    
    async def infer_stream(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Streaming inference.
        
        Usage:
            async for chunk in llm_bridge.infer_stream("Generate a Dockerfile"):
                print(chunk, end="", flush=True)
        """
        if not self.client:
            raise RuntimeError("LLM bridge not initialized. Call startup() first.")
        
        async for chunk in self.client.infer_stream(
            prompt=prompt,
            system_message=system_message,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            use_fallback=self.config.use_fallback,
        ):
            yield chunk
    
    def get_metrics(self, limit: int = 10) -> list:
        """Get recent inference metrics."""
        if not self.client:
            return []
        return self.client.get_metrics(limit=limit)


# ============================================================================
# FastAPI Integration
# ============================================================================

async def setup_fastapi_routes(app, llm_bridge: AgentXLLMBridge):
    """
    Attach DMR-backed inference routes to FastAPI app.
    
    Usage:
        from fastapi import FastAPI
        app = FastAPI()
        llm_bridge = AgentXLLMBridge(LLMConfig())
        
        @app.on_event("startup")
        async def startup():
            await llm_bridge.startup()
        
        @app.on_event("shutdown")
        async def shutdown():
            await llm_bridge.shutdown()
        
        await setup_fastapi_routes(app, llm_bridge)
    """
    from fastapi import Request
    from fastapi.responses import StreamingResponse
    import json
    
    @app.post("/api/v1/infer")
    async def infer_endpoint(request: Request):
        """Non-streaming inference endpoint."""
        body = await request.json()
        prompt = body.get("prompt")
        system = body.get("system_message")
        
        try:
            response = await llm_bridge.infer(
                prompt=prompt,
                system_message=system,
            )
            return {
                "status": "success",
                "response": response,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }
    
    @app.post("/api/v1/infer/stream")
    async def infer_stream_endpoint(request: Request):
        """Streaming inference endpoint."""
        body = await request.json()
        prompt = body.get("prompt")
        system = body.get("system_message")
        
        async def stream_generator():
            try:
                async for chunk in llm_bridge.infer_stream(
                    prompt=prompt,
                    system_message=system,
                ):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
        )
    
    @app.get("/api/v1/metrics")
    async def metrics_endpoint():
        """Get recent inference metrics."""
        metrics = llm_bridge.get_metrics(limit=20)
        return {
            "status": "success",
            "metrics": metrics,
        }


# ============================================================================
# Main Loop Example
# ============================================================================

class AgentXCore:
    """Example Agent X core with DMR integration."""
    
    def __init__(self, use_dmr: bool = True):
        self.use_dmr = use_dmr
        self.llm_bridge: Optional[AgentXLLMBridge] = None
    
    async def startup(self):
        """Initialize Agent X."""
        if self.use_dmr:
            self.llm_bridge = AgentXLLMBridge(LLMConfig())
            await self.llm_bridge.startup()
            logger.info("Agent X started with DMR")
        else:
            logger.info("Agent X started (without DMR)")
    
    async def shutdown(self):
        """Cleanup Agent X."""
        if self.llm_bridge:
            await self.llm_bridge.shutdown()
            logger.info("Agent X shutdown complete")
    
    async def process_task(self, task: str) -> str:
        """Process a task using LLM."""
        if not self.llm_bridge:
            raise RuntimeError("LLM bridge not initialized")
        
        system_msg = (
            "You are Agent X, a Docker expert AI assistant. "
            "Respond concisely and accurately."
        )
        
        try:
            response = await self.llm_bridge.infer(
                prompt=task,
                system_message=system_msg,
            )
            return response
        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            raise
    
    async def process_task_streaming(self, task: str) -> AsyncIterator[str]:
        """Process a task with streaming output."""
        if not self.llm_bridge:
            raise RuntimeError("LLM bridge not initialized")
        
        system_msg = (
            "You are Agent X, a Docker expert AI assistant. "
            "Respond concisely and accurately."
        )
        
        async for chunk in self.llm_bridge.infer_stream(
            prompt=task,
            system_message=system_msg,
        ):
            yield chunk


# ============================================================================
# Usage Examples
# ============================================================================

async def example_basic_usage():
    """Example: Basic non-streaming inference."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Non-Streaming Inference")
    print("="*60)
    
    bridge = AgentXLLMBridge(LLMConfig())
    await bridge.startup()
    
    try:
        response = await bridge.infer(
            "Write a 3-line Dockerfile for a Python app"
        )
        print(f"Response:\n{response}")
    finally:
        await bridge.shutdown()


async def example_streaming():
    """Example: Streaming inference."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Streaming Inference")
    print("="*60)
    
    bridge = AgentXLLMBridge(LLMConfig())
    await bridge.startup()
    
    try:
        print("Generating...")
        async for chunk in bridge.infer_stream(
            "List 3 Docker best practices"
        ):
            print(chunk, end="", flush=True)
        print()
    finally:
        await bridge.shutdown()


async def example_metrics():
    """Example: Collecting metrics."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Metrics Collection")
    print("="*60)
    
    bridge = AgentXLLMBridge(LLMConfig())
    await bridge.startup()
    
    try:
        # Run a few inferences
        for i in range(2):
            await bridge.infer(f"Short prompt {i}")
        
        # Get metrics
        metrics = bridge.get_metrics(limit=2)
        print(f"Last 2 inference metrics:")
        for m in metrics:
            print(f"  - Model: {m['model']}, Latency: {m['latency_ms']:.0f}ms, "
                  f"Tokens: {m['total_tokens']}, Fallback: {m['fallback_used']}")
    finally:
        await bridge.shutdown()


async def example_main_loop():
    """Example: Agent X main loop."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Agent X Main Loop")
    print("="*60)
    
    agent = AgentXCore(use_dmr=True)
    await agent.startup()
    
    try:
        # Process a task
        result = await agent.process_task(
            "What is the difference between CMD and ENTRYPOINT in Dockerfile?"
        )
        print(f"Task result:\n{result}")
        
        # Stream a task
        print("\nStreaming task:")
        async for chunk in agent.process_task_streaming(
            "Name 3 Docker networking drivers"
        ):
            print(chunk, end="", flush=True)
        print()
    finally:
        await agent.shutdown()


# ============================================================================
# Run Examples
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        # Uncomment examples to run
        # await example_basic_usage()
        # await example_streaming()
        # await example_metrics()
        # await example_main_loop()
        print("Integration examples ready. Uncomment in __main__ to run.")
    
    asyncio.run(main())
