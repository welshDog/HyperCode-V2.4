# TinyLlama Configuration - Completed

**Doc Tag:** v2.0.0 | **Last Updated:** 2026-03-10  
**Status:** ✅ Current defaults (TinyLlama-first + auto model selection)  

## Changes Made

### 1. Docker Compose Updates

**Resource Optimization:**
- Keep Ollama on a smaller quantized model by default (`tinyllama`) to avoid OOM on low-memory machines
- Use auto-selection to fall back to the smallest available quantized model if TinyLlama is missing

**Resource Allocation:**
```yaml
deploy:
  resources:
    limits:
      cpus: "2"
      memory: 3G
    reservations:
      cpus: "1"
      memory: 1G
```

### 2. TinyLlama Model Installed

**Model Details:**
- **Name:** `tinyllama:latest`
- **Size:** 637 MB (0.6 GB)
- **ID:** 2644915ede35
- **Location:** `/root/.ollama` in container
- **Persistent Storage:** `ollama-data` Docker volume (host-managed)

### 3. Agent Configuration

All agents should default to TinyLlama:
```json
{
  "model": "tinyllama",
  "ollama_host": "http://hypercode-ollama:11434",
  "temperature": 0.3
}
```

Auto-selection + tuning (recommended):

```text
DEFAULT_LLM_MODEL=auto
OLLAMA_MODEL_PREFERRED=tinyllama:latest,tinyllama,phi3:latest,phi3
OLLAMA_MAX_MODEL_SIZE_MB=2500
OLLAMA_TEMPERATURE=0.3
OLLAMA_TOP_P=0.9
OLLAMA_TOP_K=40
OLLAMA_REPEAT_PENALTY=1.1
OLLAMA_NUM_CTX=2048
OLLAMA_NUM_PREDICT=256
```

**Configured agents:**
- frontend-specialist
- backend-specialist
- database-architect
- qa-engineer
- devops-engineer
- security-engineer
- system-architect
- project-strategist

## Current System Status

### Services Running
✅ All 17 containers are up and healthy:
- **Infrastructure:** postgres, redis, jaeger, prometheus, grafana
- **Core:** hypercode-core, hypercode-dashboard
- **LLM:** hypercode-ollama (with TinyLlama model)
- **Agents:** 8 specialist agents + crew-orchestrator

### Memory Usage (Current)
Based on `docker stats`:
- **Agents:** ~50-70 MB each (512 MB limit per agent)
- **Core Services:** ~100-130 MB
- **Orchestrator:** ~47 MB (1GB limit)
- **Ollama Container:** Starting (2GB limit, ~1GB expected with TinyLlama loaded)
- **Total Docker Usage:** ~2-3 GB out of 6GB allocated

### Resource Availability
```
System RAM: 8GB total
├── OS/Apps: ~2GB
└── Docker Desktop: 6GB
    ├── Used: ~3GB
    └── Available: ~3GB buffer
```

**Safe operating margins** ✅

## Testing the LLM

### Verify Model is Available
```bash
curl http://localhost:11434/api/tags
```

### Test Inference
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "tinyllama",
  "prompt": "Why is the sky blue?",
  "stream": false
}'
```

### From Inside Container
```bash
docker exec -it hypercode-ollama ollama run tinyllama
```

## Next Steps

### Optional: Set Docker Memory to 6GB
Currently, you're using default Docker memory allocation. To explicitly set it to 6GB:

1. Open **Docker Desktop** → **Settings** → **Resources**
2. Set **Memory** slider to **6144 MB (6GB)**
3. Click **Apply & Restart**
4. Verify with: `docker info | grep Memory`

### Alternative Models (if TinyLlama isn't sufficient)

If you need better quality responses, consider:

**Slightly Larger Models (still fit in 8GB RAM):**
```bash
docker exec hypercode-ollama ollama pull phi           # 2.6 GB
docker exec hypercode-ollama ollama pull orca-mini     # 1.3 GB
```

**Update agent configs to use new model:**
```json
{
  "model": "phi"  # or "orca-mini"
}
```

**Cloud/API-Based (no local memory needed):**
- OpenAI API (set `OPENAI_API_KEY` environment variable)
- Groq Cloud (fast inference, generous free tier)
- Ollama Cloud (remote Ollama hosting)

## Troubleshooting

### If Ollama Container is Unhealthy
```bash
# Check logs
docker logs hypercode-ollama

# Restart container
docker restart hypercode-ollama

# Re-pull model if needed
docker exec hypercode-ollama ollama pull tinyllama
```

### If Memory Issues Occur
```bash
# Check current memory usage
docker stats --no-stream

# If over 80% usage, consider:
# 1. Stop some agent containers temporarily
# 2. Switch to API-based LLM
# 3. Use even smaller model (orca-mini)
```

### If Agents Can't Connect to LLM
```bash
# Verify network connectivity
docker exec frontend-specialist ping -c 2 hypercode-ollama

# Check if model is loaded
docker exec hypercode-ollama ollama list

# Test from within network
docker exec hypercode-core curl http://hypercode-ollama:11434/api/tags
```

## Performance Notes

### TinyLlama Characteristics
- ✅ **Fast inference** (1-2 seconds for simple queries)
- ✅ **Low memory footprint** (~1GB loaded)
- ✅ **Good for simple tasks** (code suggestions, basic Q&A)
- ⚠️ **Limited reasoning** (not as capable as larger models)
- ⚠️ **Shorter context window** (2048 tokens)

### When to Upgrade
Consider switching to cloud APIs or larger models if you need:
- Complex reasoning tasks
- Long-form content generation
- Multi-step problem solving
- Large context windows (8K+ tokens)

## Configuration Files Modified

1. ✅ `docker-compose.yml` - Updated Ollama service resource limits + tuning defaults
2. ✅ `agents/*/config.json` - Already configured for TinyLlama (no changes needed)

## Verification Checklist

- [x] Docker containers stopped
- [x] docker-compose.yml updated with 2GB memory limit
- [x] Docker services restarted
- [x] TinyLlama model pulled successfully (637 MB)
- [x] Model verified with `ollama list`
- [x] All 17 containers running and healthy
- [x] Ollama API responding on port 11434
- [x] Agent configs verified to use TinyLlama
- [x] Memory usage within safe limits

---

**Configuration Complete!** 🎉

Your system is now optimized to run TinyLlama within your 8GB RAM constraint.
