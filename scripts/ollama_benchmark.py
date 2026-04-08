import os
import re
import time
from collections import Counter

import httpx


def repetition_score(text: str) -> int:
    tokens = re.findall(r"\w+|[^\w\s]", text.lower())
    bigrams = [" ".join(tokens[i : i + 2]) for i in range(len(tokens) - 1)]
    if not bigrams:
        return 0
    counts = Counter(bigrams)
    return max(counts.values())


def generate(host: str, model: str, prompt: str, options: dict) -> tuple[str, float]:
    url = f"{host.rstrip('/')}/api/generate"
    started = time.perf_counter()
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            url,
            json={"model": model, "prompt": prompt, "stream": False, "options": options},
        )
        response.raise_for_status()
        text = response.json().get("response", "")
    elapsed = time.perf_counter() - started
    return text, elapsed


def main() -> None:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "tinyllama")
    prompt = os.getenv(
        "OLLAMA_BENCH_PROMPT",
        "Write a short greeting in BROski style. Avoid repeating yourself.",
    )

    baseline_options = {
        "temperature": float(os.getenv("OLLAMA_BASELINE_TEMPERATURE", "0.7")),
        "top_p": float(os.getenv("OLLAMA_BASELINE_TOP_P", "0.95")),
        "top_k": int(os.getenv("OLLAMA_BASELINE_TOP_K", "40")),
        "repeat_penalty": float(os.getenv("OLLAMA_BASELINE_REPEAT_PENALTY", "1.0")),
        "num_ctx": int(os.getenv("OLLAMA_BASELINE_NUM_CTX", "2048")),
        "num_predict": int(os.getenv("OLLAMA_BASELINE_NUM_PREDICT", "256")),
    }

    tuned_options = {
        "temperature": float(os.getenv("OLLAMA_TUNED_TEMPERATURE", "0.3")),
        "top_p": float(os.getenv("OLLAMA_TUNED_TOP_P", "0.9")),
        "top_k": int(os.getenv("OLLAMA_TUNED_TOP_K", "40")),
        "repeat_penalty": float(os.getenv("OLLAMA_TUNED_REPEAT_PENALTY", "1.1")),
        "num_ctx": int(os.getenv("OLLAMA_TUNED_NUM_CTX", "2048")),
        "num_predict": int(os.getenv("OLLAMA_TUNED_NUM_PREDICT", "256")),
    }

    try:
        baseline_text, baseline_s = generate(host, model, prompt, baseline_options)
        tuned_text, tuned_s = generate(host, model, prompt, tuned_options)
    except httpx.HTTPError as exc:
        print(
            {
                "error": "ollama_unreachable",
                "host": host,
                "hint": "Start Ollama and ensure /api/generate is reachable",
                "details": str(exc),
            }
        )
        raise SystemExit(2) from exc

    report = {
        "host": host,
        "model": model,
        "baseline": {
            "seconds": baseline_s,
            "repetition_score": repetition_score(baseline_text),
            "chars": len(baseline_text),
        },
        "tuned": {
            "seconds": tuned_s,
            "repetition_score": repetition_score(tuned_text),
            "chars": len(tuned_text),
        },
    }

    print(report)
    print("\nbaseline_output:\n" + baseline_text.strip())
    print("\ntuned_output:\n" + tuned_text.strip())


if __name__ == "__main__":
    main()
