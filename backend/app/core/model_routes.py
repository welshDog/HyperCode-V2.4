"""
Model routing for multiple LLM providers.
"""
from typing import AsyncGenerator, Dict, Any, List
from ..llm.openrouter import chat_completion as openrouter_chat
from ..llm.ollama import chat_completion as ollama_chat


async def route_model_request(
    provider: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 2048,
    stream: bool = True,
    api_key: str = "",
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Route LLM requests to the appropriate provider.
    
    Args:
        provider: Provider name ('openrouter', 'ollama', etc.)
        model: Model identifier
        messages: Chat messages
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        stream: Whether to stream
        api_key: API key for the provider
    """
    if provider == "openrouter":
        async for chunk in openrouter_chat(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            api_key=api_key,
        ):
            yield chunk
    elif provider == "ollama":
        async for chunk in ollama_chat(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
        ):
            yield chunk
    else:
        raise ValueError(f"Unknown provider: {provider}")
