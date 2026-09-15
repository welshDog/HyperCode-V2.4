# Docker Model Runner (DMR) Integration for Agent X

**Status:** ✨ Production-ready proof-of-concept

This integration adds local, resource-aware LLM inference to Agent X using **Docker Model Runner**. Replace the separate Ollama container with an embedded DMR sidecar that:
- **Loads models on-demand** (not always in memory)
- **Auto-unloads after 5 min idle** (saves RAM)
- **Falls back to smaller models** on timeout (resilience)
- **Serves OpenAI-compatible API** (no agent code changes)
- **Streams responses** (better UX for long outputs)
- **Tracks metrics** (latency, token counts, fallback usage)

---

## Quick Start

### 1. Add DMR dependencies to Agent X

```bash
cat agents/agent-x/dmr_requirements.txt >> agents/agent-x/requirements.txt
```

### 2. Update Agent X to use DMR

In `agents/agent-x/agentx/main.py`:

```python
from agentx.dmr_client import DMRClient
from agentx.integration_example import AgentXLLMBridge, AgentXCore

# Initialize Agent X with DMR
async def main():
    agent = AgentXCore(use_dmr=True)  # ✨ Enable DMR
    
    await agent.startup()
    
    # Quick inference
    result = await agent.quick_inference("Write a Docker health check")
    
    # Streaming inference
    async for chunk in agent.llm.infer_stream("Generate a Dockerfile"):
        print(chunk, end="", flush=True)
    
    await agent.shutdown()
```

### 3. Build updated Agent X image

```bash
docker build -t hypercode-v24-agent-x:dmr -f agents/agent-x/Dockerfile .
```

### 4. Start with DMR sidecar

```bash
docker compose -f docker-compose.yml \
               -f docker-compose.dmr.yml \
               up -d agent-x
```

### 5. Verify

```bash
# Check Agent X is healthy with DMR
docker ps | grep agent-x

# Check DMR daemon is running
docker ps | grep dmr-daemon

# Test inference endpoint
curl -X POST http://localhost:12434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ai/smollm2:360m-q4_k_m",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Check Agent X metrics
curl http://localhost:8080/api/v1/metrics | jq .metrics[-5:]
```

---

## Architecture

```
Agent X Container (port 8080)
├── main.py
├── dmr_client.py  ✨ (new)
└── integration_example.py ✨ (new)
     │
     └─> DMR Sidecar (port 12434)
         ├── Model Runner daemon
         ├── Model cache (/var/lib/dmr)
         └── OpenAI-compatible API

Shared localhost → both containers can reach :12434
Shared volumes → models persist across restarts
```

### Data Flow

1. **Agent X needs inference:**
   ```
   agent.infer("prompt") 
   → DMRClient.infer() 
   → HTTP POST /v1/chat/completions
   ```

2. **DMR loads model if needed:**
   ```
   POST received 
   → Model in cache? Yes → use it
   → Model in cache? No → download + quantize → use it
   → Idle timeout (5 min) → unload from memory
   ```

3. **Fallback on timeout:**
   ```
   Primary model slow? 
   → Timeout after 5s 
   → Try fallback (SmolLM2 360M) 
   → Return result + flag `fallback_used=true`
   ```

---

## Files

| File | Purpose |
|------|---------|
| `agentx/dmr_client.py` | Core DMRClient: OpenAI-compatible API, fallback, metrics |
| `agentx/integration_example.py` | Integration patterns: bridge layer, FastAPI endpoints, main loop |
| `dmr_requirements.txt` | Dependencies: aiohttp, tenacity, pydantic |
| `docker-compose.dmr.yml` | Compose override: DMR sidecar, resource limits, volumes |
| `Dockerfile` (existing) | No changes needed—DMR is external sidecar |

---

## Configuration

### Environment Variables (set in docker-compose.dmr.yml)

| Variable | Default | Notes |
|----------|---------|-------|
| `DMR_HOST` | `http://127.0.0.1:12434` | DMR API endpoint (localhost because sidecar) |
| `DMR_MODEL` | `ai/qwen2.5-coder:7b-instruct-q4_k_m` | Primary model (7B, good quality) |
| `DMR_FALLBACK` | `ai/smollm2:360m-q4_k_m` | Fallback model (360M, instant, lower quality) |
| `DMR_GPU` | `auto` | GPU support: `auto`, `cuda`, `rocm`, `none` |
| `DMR_BACKEND` | `llama.cpp` | Inference engine: `llama.cpp`, `vllm`, `diffusers` |
| `DMR_INFERENCE_TIMEOUT` | `300s` | Max time for a single inference call |
| `DMR_MODEL_LOAD_TIMEOUT` | `120s` | Max time to load a model from disk |

### Python Client Options

```python
# Create client with custom settings
client = DMRClient(
    host="http://127.0.0.1:12434",
    primary_model="ai/qwen2.5-coder:7b-instruct-q4_k_m",
    fallback_model="ai/smollm2:360m-q4_k_m",
    inference_timeout_ms=300_000,  # 5 min
    max_retries=3,
)

# Quick inference (synchronous-style wrapper)
result = await client.infer(
    "Prompt",
    system_message="You are helpful.",
    temperature=0.7,
    max_tokens=1024,
    use_fallback=True,  # Retry with fallback on timeout
)

# Streaming inference (for long outputs)
async for chunk in client.infer_stream("Prompt"):
    print(chunk, end="")

# Preload models in background
await client.preload_models()

# Get metrics
metrics = client.get_metrics(limit=10)

# Health check
health = await client.health_check()

# Resource cleanup
await client.close()
```

---

## Performance

### Model Load Times (on 8GB host)

| Model | First Load | Cached Load | RAM | Quality |
|-------|-----------|-------------|-----|---------|
| SmolLM2 360M | ~5s | <100ms | 1GB | Good for triage |
| Qwen2.5-Coder 7B | ~20s | <500ms | 7GB | High quality coding |

### Idle Unload

Models stay in memory only while being used. After **5 minutes of idle time**, they're automatically unloaded, freeing RAM for the host.

**Timeline:**
```
t=0:00   Model A loaded (7GB)
t=5:00   No activity → Model A unloaded (free 7GB)
t=5:15   Infer request → Model A reloaded (~20s)
```

---

## Troubleshooting

### DMR container won't start

```bash
docker logs agent-x-dmr
# Check for: "Docker daemon not ready", "Permission denied"
```

**Fix:** Ensure Docker socket is mounted and readable:
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

### Model inference timeout

```python
# Error: InferenceTimeoutError: Inference timeout (>300000ms)
```

**Possible causes:**
1. **Model is loading** (first run): Normal, takes 5-30s depending on model size
2. **System is overloaded**: Check `docker stats`
3. **Network issue**: Verify `curl http://localhost:12434/health`

**Solutions:**
- Increase `inference_timeout_ms` in DMRClient
- Preload models on startup: `await client.preload_models()`
- Switch to smaller model: SmolLM2 360M instead of Qwen2.5 7B
- Increase host memory or reduce other containers

### Out of memory (OOM)

```
ModelNotAvailableError: Model ai/qwen2.5-coder:7b ... unavailable after 3 attempts
# Check daemon logs: docker logs dmr-daemon-agent-x
```

**Fix:**
1. Check available memory: `docker stats agent-x-dmr`
2. Reduce DMR resource limit in docker-compose.dmr.yml:
   ```yaml
   cpus: '2'  # was 3
   memory: 4G  # was 6G
   ```
3. Use smaller model: `DMR_MODEL=ai/smollm2:360m-q4_k_m`

### Fallback model not triggered

```python
# Inference always uses primary model, never falls back
```

**Debug:**
```python
# Check metrics
metrics = client.get_metrics(limit=1)
print(f"Model: {metrics[0]['model']}, Fallback: {metrics[0]['fallback_used']}")
```

If `fallback_used=false` always, the primary model is meeting the timeout threshold. This is expected for most prompts—fallback only triggers on actual timeout or 503 service unavailable.

---

## Best Practices

### 1. Preload models on Agent X startup

```python
async def startup():
    await agent.llm.initialize()
    await agent.llm.dmr_client.preload_models()
    logger.info("✓ DMR ready")
```

This ensures models are in memory and ready when the first inference request arrives.

### 2. Use streaming for long outputs

```python
# Instead of:
result = await client.infer("Generate a Dockerfile")

# Use:
async for chunk in client.infer_stream("Generate a Dockerfile"):
    print(chunk, end="")
```

Streaming gives better UX for long outputs and lets you print progressively.

### 3. Monitor metrics

```python
# Periodically log metrics
def log_metrics():
    metrics = agent.llm.get_metrics(limit=5)
    for m in metrics:
        print(f"{m['model']} | {m['total_tokens']} tokens | {m['latency_ms']:.0f}ms")
```

Helps identify slow models or fallback patterns.

### 4. Tune resource limits based on your host

If running on 8GB host:
```yaml
dmr-runner:
  deploy:
    resources:
      limits:
        cpus: '2'     # Leave 2 CPUs for agent-x
        memory: 5G    # Leave 3GB for agent-x + OS
```

If running on 16GB+ host:
```yaml
dmr-runner:
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 12G
```

### 5. Use fallback for critical paths

```python
# High-reliability inference (don't fail, use smaller model if needed)
response = await client.infer(
    prompt,
    use_fallback=True,  # Always retry with fallback
)

# Best-effort inference (accept timeout)
try:
    response = await client.infer(
        prompt,
        use_fallback=False,  # No fallback, fail fast
    )
except InferenceTimeoutError:
    response = "Unable to process request"
```

---

## Migration from Ollama to DMR

### Side-by-side testing

1. Keep Ollama running on `:11434`
2. Start DMR on `:12434` via docker-compose.dmr.yml
3. Update Agent X to use DMR (set `DMR_HOST=http://127.0.0.1:12434`)
4. Monitor for issues (see "Troubleshooting" section)
5. Once stable, remove Ollama container

### Rollback if needed

If DMR causes issues, revert to Ollama:
```python
agent = AgentXCore(use_dmr=False)  # Fall back to Ollama
```

---

## Examples

### Example 1: Quick inference (sync-like)

```python
from agentx.dmr_client import quick_infer

# One-liner for scripts/tests
response = await quick_infer("Write a health check for a Docker service")
```

### Example 2: Streaming with metrics

```python
async with DMRClient() as client:
    print("Generating Dockerfile...")
    tokens = 0
    async for chunk in client.infer_stream("Generate a production Dockerfile"):
        print(chunk, end="", flush=True)
        tokens += len(chunk.split())
    
    metrics = client.get_metrics(limit=1)
    print(f"\n\nMetrics: {metrics[0]['latency_ms']:.0f}ms, {tokens} tokens")
```

### Example 3: FastAPI integration

```python
from fastapi import FastAPI
from agentx.integration_example import FastAPIIntegration

app = FastAPI()
agent = AgentXCore(use_dmr=True)
api = FastAPIIntegration(agent)

@app.on_event("startup")
async def startup():
    await agent.startup()

@app.on_event("shutdown")
async def shutdown():
    await agent.shutdown()

@app.post("/api/v1/task")
async def create_task(request_data: dict):
    return await api.task_endpoint(request_data)

@app.get("/api/v1/health")
async def health():
    return await api.health_endpoint()

@app.get("/api/v1/metrics")
async def metrics():
    return await api.metrics_endpoint()
```

---

## Next Steps

1. **Test locally** — spin up `docker-compose.dmr.yml` and verify inference works
2. **Integrate with Agent X** — replace Ollama client with DMRClient
3. **Monitor** — track metrics for 1-2 weeks, tune resource limits
4. **Migrate other agents** — crew-orchestrator, coder-agent, etc. if stable
5. **Retire Ollama** — once all agents use DMR, remove the shared Ollama container

---

## Support

For issues:
1. Check `docker logs agent-x-dmr` for DMR daemon errors
2. Check `docker logs agent-x-01` for Agent X integration errors
3. Verify endpoint: `curl http://localhost:12434/health`
4. Review metrics: `curl http://localhost:8080/api/v1/metrics | jq`
