# AI Integration Notes (Local-first Ollama)

**Doc Tag:** v2.0.0 | **Last Updated:** 2026-03-10

This note describes the *current* AI integration for HyperCode V2.0.

## Source of Truth

- Backend LLM routing + tuning: [backend/app/agents/brain.py](../../backend/app/agents/brain.py)
- Ollama model auto-selection: [backend/app/llm/ollama.py](../../backend/app/llm/ollama.py)
- Default env surface: [.env.example](../../.env.example)
- TinyLlama guide: [TINYLLAMA_CONFIGURATION.md](../configuration/TINYLLAMA_CONFIGURATION.md)

## Current Architecture (What Runs Where)

- **Ollama** runs as a Docker service (`hypercode-ollama`) in [docker-compose.yml](../../docker-compose.yml).
- **HyperCode Core API** calls Ollama via `OLLAMA_HOST=http://hypercode-ollama:11434`.
- **Model selection** uses `DEFAULT_LLM_MODEL=auto` and chooses the best small/quantized installed model.

## Quick Start (Local Dev)

```bash
docker compose up -d hypercode-ollama
docker compose up -d hypercode-core
```

Verify:

```bash
docker compose ps
docker exec hypercode-ollama ollama list
curl http://localhost:8000/health
```

## Recommended Environment Defaults

These are the defaults used across docs and the backend config surface:

```text
OLLAMA_HOST=http://hypercode-ollama:11434
DEFAULT_LLM_MODEL=auto
OLLAMA_MODEL_PREFERRED=tinyllama:latest,tinyllama,phi3:latest,phi3
OLLAMA_MAX_MODEL_SIZE_MB=2500
OLLAMA_MODEL_REFRESH_SECONDS=300

OLLAMA_TEMPERATURE=0.3
OLLAMA_TOP_P=0.9
OLLAMA_TOP_K=40
OLLAMA_REPEAT_PENALTY=1.1
OLLAMA_NUM_CTX=2048
OLLAMA_NUM_PREDICT=256
```

## Notes on Production Deployments

- The frontend can be hosted separately from the backend.
- Ollama runs wherever the backend runs (Docker/Kubernetes/VPS), not in static hosting platforms.

