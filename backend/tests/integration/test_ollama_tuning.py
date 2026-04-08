import os
import re
from collections import Counter

import httpx
import pytest


def repetition_score(text: str) -> int:
    tokens = re.findall(r"\w+|[^\w\s]", text.lower())
    bigrams = [" ".join(tokens[i : i + 2]) for i in range(len(tokens) - 1)]
    if not bigrams:
        return 0
    counts = Counter(bigrams)
    return max(counts.values())


def generate(host: str, model: str, prompt: str, options: dict) -> str:
    url = f"{host.rstrip('/')}/api/generate"
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            url,
            json={"model": model, "prompt": prompt, "stream": False, "options": options},
        )
        response.raise_for_status()
        return response.json().get("response", "")


@pytest.mark.skipif(os.getenv("RUN_OLLAMA_BENCH") != "1", reason="Set RUN_OLLAMA_BENCH=1 to run")
def test_tuned_hyperparams_reduce_repetition_on_small_model():
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "tinyllama")
    prompt = "Write a short greeting. Avoid repeating yourself. Keep it under 60 words."

    baseline = generate(
        host,
        model,
        prompt,
        {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "repeat_penalty": 1.0,
            "num_ctx": 2048,
            "num_predict": 128,
        },
    )
    tuned = generate(
        host,
        model,
        prompt,
        {
            "temperature": 0.3,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1,
            "num_ctx": 2048,
            "num_predict": 128,
        },
    )

    assert len(tuned) > 0
    assert repetition_score(tuned) <= repetition_score(baseline)

