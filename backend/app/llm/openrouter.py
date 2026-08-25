import httpx
import json
from typing import AsyncGenerator, Dict, Any, List

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


async def chat_completion(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 2048,
    stream: bool = True,
    api_key: str = "",
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    OpenRouter chat completion with streaming support.
    Uses free models when available.
    
    Args:
        model: Model identifier (e.g., 'mistralai/mistral-7b-instruct:free')
        messages: List of message dicts with 'role' and 'content'
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens to generate
        stream: Whether to stream responses
        api_key: OpenRouter API key
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/welshDog/HyperCode-V2.4",
        "X-Title": "HyperCode-V2.4",
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    
    async with httpx.AsyncClient() as client:
        if stream:
            async with client.stream(
                "POST",
                f"{OPENROUTER_BASE}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60.0,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            yield chunk
                        except json.JSONDecodeError:
                            continue
        else:
            resp = await client.post(
                f"{OPENROUTER_BASE}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60.0,
            )
            resp.raise_for_status()
            yield resp.json()
