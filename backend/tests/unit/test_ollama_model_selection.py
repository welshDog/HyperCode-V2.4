import httpx
import pytest

from app.llm.ollama import OllamaModelResolver, select_best_ollama_model


def test_select_best_ollama_model_prefers_tinyllama_when_available():
    payload = {
        "models": [
            {"name": "phi3:latest", "size": 2_200_000_000, "details": {"quantization_level": "Q4_0"}},
            {"name": "tinyllama:latest", "size": 650_000_000, "details": {"quantization_level": "Q4_0"}},
            {"name": "llama3:latest", "size": 4_700_000_000, "details": {"quantization_level": "Q4_0"}},
        ]
    }
    selected = select_best_ollama_model(
        payload,
        preferred_patterns=["tinyllama", "phi3", "llama3"],
        max_size_mb=2500,
    )
    assert selected == "tinyllama:latest"


def test_select_best_ollama_model_filters_by_max_size():
    payload = {
        "models": [
            {"name": "llama3:latest", "size": 4_700_000_000, "details": {"quantization_level": "Q4_0"}},
            {"name": "phi3:latest", "size": 2_200_000_000, "details": {"quantization_level": "Q4_0"}},
        ]
    }
    selected = select_best_ollama_model(
        payload,
        preferred_patterns=["tinyllama", "phi3", "llama3"],
        max_size_mb=2500,
    )
    assert selected == "phi3:latest"


@pytest.mark.asyncio
async def test_ollama_model_resolver_uses_tags_endpoint_and_caches():
    payload = {
        "models": [
            {"name": "tinyllama:latest", "size": 650_000_000, "details": {"quantization_level": "Q4_0"}},
        ]
    }
    hit_count = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            hit_count["count"] += 1
            return httpx.Response(200, json=payload)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, timeout=5.0) as client:
        resolver = OllamaModelResolver(
            ollama_host="http://hypercode-ollama:11434",
            preferred_patterns=["tinyllama"],
            max_size_mb=2500,
            refresh_seconds=3600,
        )
        first = await resolver.resolve(client)
        second = await resolver.resolve(client)

    assert first == "tinyllama:latest"
    assert second == "tinyllama:latest"
    assert hit_count["count"] == 1

