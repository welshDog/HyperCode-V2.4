# 🐳 Docker Model Runner — HyperCode-V2.4

> **Since:** 2026-09-07 (replaced the standalone `ollama/ollama` container)
> **Spike / decision record:** `docs/health-reports/dmr-spike-2026-09-07.md`
> **Plan:** `~/.claude/plans/…-hypercode-v2-4-parallel-lighthouse.md`

---

## What this is

Local LLM inference is served by **Docker Model Runner (DMR)** — the
`docker model` engine built into Docker Desktop — not a container we run.
It loads a model on first request and unloads it after **5 minutes idle**, so
there is no always-on multi-GB Ollama container on this 4 GB box any more.

DMR v1.2.8+ serves **both** APIs:

| API | Base (host) | Base (in-container) |
|---|---|---|
| Ollama-native (`/api/tags`, `/api/generate`, `/api/chat`) | `http://localhost:12434` | `http://model-runner.docker.internal` |
| OpenAI-compatible (`/engines/v1/...`) | `http://localhost:12434/engines/v1` | `http://model-runner.docker.internal/engines/v1` |

## How HyperCode reaches it

The compose service still called **`hypercode-ollama`** is now a ~1 MB
`alpine/socat` shim (in `docker-compose.core.yml`) that forwards
`:11434 → model-runner.docker.internal:80`. Every consumer keeps its existing
`OLLAMA_HOST=http://hypercode-ollama:11434` and every `depends_on: hypercode-ollama`
still works — the shim has a health check.

`backend/app/llm/ollama.py` (`OllamaModelResolver`) and `backend/app/agents/brain.py`
are unchanged: DMR's `/api/tags` and `/api/generate` responses match the Ollama
shapes they already parse. `DEFAULT_LLM_MODEL=auto` resolves via
`OLLAMA_MODEL_PREFERRED` (now DMR names — `smollm2,qwen2.5-coder,qwen2.5`).

## First-time setup

```bash
docker desktop enable model-runner --tcp=12434     # once; no restart needed
docker model pull ai/smollm2                        # the default fallback model
docker model list
```

## Models

| HyperCode use | Env var(s) | Model |
|---|---|---|
| brain / `auto` / general | `OLLAMA_MODEL`, `OLLAMA_MODEL_PREFERRED`, `BRAIN_OLLAMA_MODEL` | `ai/smollm2` |
| coder agents | `CODER_OLLAMA_MODEL`, agent-x `OLLAMA_MODEL` | `ai/smollm2` (upgrade to `ai/qwen2.5-coder` once the catalog name/auth is sorted — `insufficient_scope` on pull as of 2026-09-07) |
| pets | `PETS_OLLAMA_MODEL` | `ai/smollm2` |

Pull a model the catalog doesn't carry straight from Hugging Face:
```bash
docker model pull hf.co/<user>/<repo>-GGUF:Q4_K_M
```

## Notes / gotchas

- **CPU only** on this box (`llama.cpp b9879-cpu`) — inference speed is the same
  as Ollama was. The win is RAM lifecycle, not latency.
- **Cold start:** first request after 5 min idle reloads the model from disk
  before the first token. Bursty agent traffic will occasionally see a slow
  first response.
- DMR `/api/tags` reports `"size":0`; the resolver's `OLLAMA_MAX_MODEL_SIZE_MB`
  filter treats 0 as "unknown" and skips it — harmless no-op.
- Model names from `/api/tags` come back fully qualified
  (`docker.io/ai/smollm2:latest`); DMR accepts that form in `/api/generate`.
- **Rollback:** `docker compose … -f docker-compose.hosted-llm.yml up -d` routes
  agents to Anthropic and takes the shim out of the path.

## Commands

```bash
docker model list                 # pulled models
docker model ps                   # loaded now + idle-unload countdown
docker model pull  <ref>
docker model rm    <ref>
docker model status               # engine + backend
```
