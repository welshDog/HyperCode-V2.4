# 🧠 The Brain (Cognitive Core)

**Doc Tag:** v2.0.0 | **Last Updated:** 2026-03-10

The **Brain** is the routing + prompt engine of HyperCode. It selects an LLM runtime/provider, applies system instructions for predictable output, and (optionally) pulls context from memory systems.

Current default behavior is **local-first** using an Ollama-compatible runtime (commonly the `hypercode-ollama` service). A separate MCP profile can run a Docker Model Runner that also speaks an Ollama-compatible API.

## 1. Architecture

The Brain operates as an asynchronous service within the `hypercode-core` backend.

```mermaid
graph LR
    A[API / Task] --> B[Celery Worker]
    B --> C[Brain.think()]
    C --> D[Ollama-compatible API (/api/tags, /api/generate)]
    C --> E[Perplexity API (optional)]
    D --> C
    E --> C
    C --> B
    B --> E[Result / Database]
```

## 2. Configuration

### Local LLM (recommended)

Set the local LLM host and enable automatic model selection:

```bash
OLLAMA_HOST=http://hypercode-ollama:11434
DEFAULT_LLM_MODEL=auto
```

When `DEFAULT_LLM_MODEL=auto`, the backend selects the best available model from the installed list (TinyLlama-first, size-capped) and caches the selection.

If you are using the MCP Gateway + Model Runner profile, point to the model runner service instead:

```bash
OLLAMA_HOST=http://model-runner:11434
DEFAULT_LLM_MODEL=auto
```

### Cloud LLM (optional)

If you want a cloud fallback, provide a Perplexity API key:

```bash
PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxx
```

If `PERPLEXITY_API_KEY` is set and local Ollama is not configured, the Brain can call the cloud API. For development environments, there is also a session-auth simulation toggle used for local-only workflows.

## 3. Usage

### Programmatic Access
You can invoke the Brain from any backend service or Celery task:

```python
from app.agents.brain import brain

async def solve_problem():
    result = await brain.think(
        role="Backend Specialist",
        task_description="Write a Python script to calculate Fibonacci."
    )
    print(result)
```

### Task API
You can also trigger the Brain via the REST API:

```bash
curl -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Research Task",
    "description": "Find the latest trends in AI agents.",
    "priority": "high"
  }'
```

## 4. Swarm Integration

When a task is submitted, the **Crew Orchestrator** assigns it to a specialized agent (e.g., "Backend Specialist"). The agent then consults the **Brain** to generate a plan or solution.

### Verification
Check the Celery logs to see the Brain in action:

```powershell
docker logs -f celery-worker
```

Look for `[BRAIN] ... is thinking about:` messages.
