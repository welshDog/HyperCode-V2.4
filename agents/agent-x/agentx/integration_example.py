"""
Integration example: How to use DMRClient in Agent X's main agent loop.

This shows how to replace ollama.Client with DMRClient while maintaining
full backward compatibility with your existing agent code.
"""

import asyncio
import logging
from typing import Optional
from agentx.dmr_client import DMRClient, ModelNotAvailableError, InferenceTimeoutError

logger = logging.getLogger(__name__)


class AgentXLLMBridge:
    """
    Bridge layer to swap between Ollama and Docker Model Runner.

    Maintains a single interface for the rest of Agent X logic — swap
    the underlying implementation without touching agent code.
    """

    def __init__(self, use_dmr: bool = True):
        """
        Initialize the LLM bridge.

        Args:
            use_dmr: If True, use Docker Model Runner; if False, use Ollama.
                     Controlled via USE_DMR env var or startup parameter.
        """
        self.use_dmr = use_dmr
        self.dmr_client: Optional[DMRClient] = None

        if self.use_dmr:
            logger.info("✓ Using Docker Model Runner (DMR)")
        else:
            logger.info("✓ Using Ollama (legacy)")

    async def initialize(self) -> None:
        """Initialize the LLM backend and preload models."""
        if self.use_dmr:
            self.dmr_client = DMRClient()
            await self.dmr_client._ensure_session()

            # Preload models in background
            logger.info("Preloading models in background...")
            await self.dmr_client.preload_models()

            # Health check
            health = await self.dmr_client.health_check()
            logger.info(f"DMR health: {health}")

    async def infer(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        use_fallback: bool = True,
    ) -> str:
        """
        Run inference using the active backend.

        Args:
            prompt: User prompt
            system_message: Optional system role
            temperature: Sampling temperature
            use_fallback: Use fallback model on timeout (DMR only)

        Returns:
            Generated text
        """
        if self.use_dmr:
            return await self.dmr_client.infer(
                prompt=prompt,
                system_message=system_message,
                temperature=temperature,
                use_fallback=use_fallback,
            )
        else:
            # Legacy Ollama path (not shown here)
            raise NotImplementedError("Ollama path deprecated, use DMR only")

    async def infer_stream(self, prompt: str, system_message: Optional[str] = None):
        """
        Run streaming inference.

        Yields:
            Text chunks as they arrive
        """
        if self.use_dmr:
            async for chunk in self.dmr_client.infer_stream(
                prompt=prompt,
                system_message=system_message,
            ):
                yield chunk
        else:
            raise NotImplementedError("Ollama path deprecated, use DMR only")

    async def close(self) -> None:
        """Clean up resources."""
        if self.dmr_client:
            await self.dmr_client.close()

    def get_metrics(self, limit: int = 10):
        """Get recent inference metrics."""
        if self.dmr_client:
            return self.dmr_client.get_metrics(limit=limit)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Example: Agent X's main agent loop (pseudo-code)
# ─────────────────────────────────────────────────────────────────────────────


class AgentXCore:
    """Main Agent X logic (simplified)."""

    def __init__(self, use_dmr: bool = True):
        self.llm = AgentXLLMBridge(use_dmr=use_dmr)

    async def startup(self) -> None:
        """Initialize on startup."""
        await self.llm.initialize()
        logger.info("✓ Agent X initialized")

    async def shutdown(self) -> None:
        """Clean up on shutdown."""
        await self.llm.close()
        logger.info("✓ Agent X shut down")

    async def execute_task(self, task_description: str) -> None:
        """
        Execute a task using streaming inference (recommended for long outputs).

        Example: Code generation, debugging, etc.
        """
        system_message = """You are Agent X, a specialized code execution and debugging agent.
Your role is to:
1. Understand the task
2. Generate or debug code
3. Explain your reasoning
4. Provide actionable results

Always think step-by-step."""

        logger.info(f"Task: {task_description}")
        logger.info("Response:")

        try:
            response_text = ""
            async for chunk in self.llm.infer_stream(
                prompt=task_description,
                system_message=system_message,
            ):
                print(chunk, end="", flush=True)
                response_text += chunk

            logger.info("\n✓ Task complete")
            return response_text

        except ModelNotAvailableError as e:
            logger.error(f"✗ Model unavailable: {e}")
        except InferenceTimeoutError as e:
            logger.error(f"✗ Inference timeout: {e}")
        except Exception as e:
            logger.error(f"✗ Inference failed: {e}")

    async def quick_inference(self, prompt: str) -> str:
        """
        Quick synchronous inference (for short prompts, structured outputs).

        Example: Parsing, classification, decision-making.
        """
        try:
            response = await self.llm.infer(
                prompt=prompt,
                system_message="You are a helpful assistant. Keep responses concise.",
                temperature=0.5,  # Lower temp for more deterministic output
            )
            return response
        except Exception as e:
            logger.error(f"Quick inference failed: {e}")
            raise

    def report_metrics(self) -> None:
        """Print recent inference metrics for monitoring."""
        metrics = self.llm.get_metrics(limit=5)
        if not metrics:
            logger.info("No metrics recorded yet")
            return

        logger.info("Recent inference metrics:")
        for m in metrics:
            fallback_str = " (fallback)" if m.get("fallback_used") else ""
            logger.info(
                f"  {m['timestamp']}: {m['model']}{fallback_str} | "
                f"{m['total_tokens']} tokens | {m['latency_ms']:.0f}ms"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Example: FastAPI integration (if Agent X is an HTTP service)
# ─────────────────────────────────────────────────────────────────────────────


class FastAPIIntegration:
    """Example FastAPI endpoints for Agent X with DMR."""

    def __init__(self, agent: AgentXCore):
        self.agent = agent

    async def task_endpoint(self, request_data: dict) -> dict:
        """
        POST /api/v1/task
        Run a task and stream results.

        Example:
        {
            "task_id": "task-123",
            "description": "Generate a Docker health check for my service",
            "stream": true
        }
        """
        task_id = request_data.get("task_id")
        description = request_data.get("description")
        stream = request_data.get("stream", False)

        logger.info(f"Task {task_id}: {description}")

        if stream:
            # Return SSE stream
            async def generate():
                try:
                    async for chunk in self.agent.llm.infer_stream(
                        prompt=description
                    ):
                        yield f"data: {chunk}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    yield f"data: ERROR: {e}\n\n"

            return generate()
        else:
            # Return full response
            try:
                response = await self.agent.quick_inference(description)
                return {
                    "task_id": task_id,
                    "status": "success",
                    "response": response,
                }
            except Exception as e:
                return {
                    "task_id": task_id,
                    "status": "error",
                    "error": str(e),
                }

    async def metrics_endpoint(self) -> dict:
        """
        GET /api/v1/metrics
        Return recent inference metrics.
        """
        return {
            "metrics": self.agent.llm.get_metrics(limit=20),
        }

    async def health_endpoint(self) -> dict:
        """
        GET /api/v1/health
        Return Agent X and DMR health status.
        """
        dmr_health = await self.agent.llm.dmr_client.health_check()
        return {
            "agent_x": "healthy",
            "dmr": dmr_health,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Example: Main entry point
# ─────────────────────────────────────────────────────────────────────────────


async def main():
    """Example Agent X main loop."""
    # Initialize Agent X with DMR
    agent = AgentXCore(use_dmr=True)

    try:
        await agent.startup()

        # Example 1: Quick inference (synchronous style)
        logger.info("\n=== Example 1: Quick Inference ===")
        result = await agent.quick_inference(
            "Write a one-line Docker health check for a Python service"
        )
        logger.info(f"Result: {result}")

        # Example 2: Streaming inference (for long outputs)
        logger.info("\n=== Example 2: Streaming Inference ===")
        await agent.execute_task(
            "Generate a Dockerfile for a FastAPI service with health checks and multi-stage build"
        )

        # Example 3: Metrics
        logger.info("\n=== Example 3: Inference Metrics ===")
        agent.report_metrics()

    finally:
        await agent.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
