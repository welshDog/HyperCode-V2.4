# 🐳 Docker Model Runner — Integration Guide

> **Port:** 11434
> **Role:** Local LLM runner — OpenAI-compatible API
> **Last Updated:** 2026-03-25

---

## 🧠 What is Docker Model Runner?

Docker Model Runner lets you **run LLMs locally inside Docker** — no OpenAI API key needed, no cloud costs, full privacy.

Agent X uses it to power all autonomous agent decisions.

Think of it like:
> 🧠 "Your own private brain — runs on your machine, talks OpenAI language."

---

## ⚡ Quick Start

### Pull a model:
```bash
docker exec model-runner ollama pull tinyllama
```

### Test it's working:
```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tinyllama",
    "messages": [{"role": "user", "content": "Say hello!"}]
  }'
```

### List downloaded models:
```bash
docker exec model-runner ollama list
```

---

## 🤖 Supported Models

| Model | Size | Best for | Speed |
|-------|------|----------|-------|
| `tinyllama` | 637MB | Quick tasks, low RAM | ⚡⚡⚡ |
| `phi` | 1.6GB | Code tasks | ⚡⚡ |
| `mistral` | 4.1GB | Complex reasoning | ⚡ |
| `codellama` | 3.8GB | Code generation | ⚡ |
| `llama3` | 4.7GB | General purpose | ⚡ |

> 💡 **Default:** TinyLlama (fastest, works on most machines)

---

## 🔗 Agent X Integration

Agent X connects to Docker Model Runner automatically.

Config in `agents/agent_x/config.yaml`:
```yaml
model_runner:
  api_base: http://localhost:11434/v1
  default_model: tinyllama
  fallback_models:
    - phi
    - mistral
  timeout_seconds: 60
  max_tokens: 2048
  temperature: 0.7
```

---

## 🐳 Docker Compose Setup

In `docker-compose.yml`:
```yaml
model-runner:
  image: ollama/ollama:latest
  ports:
    - "11434:11434"
  volumes:
    - ollama_data:/root/.ollama
  restart: unless-stopped
  deploy:
    resources:
      reservations:
        devices:
          - capabilities: [gpu]  # Remove if no GPU
```

---

## ⚙️ Switching Models at Runtime

```python
import httpx

response = httpx.post(
    "http://localhost:11434/v1/chat/completions",
    json={
        "model": "mistral",  # swap model here
        "messages": [{"role": "user", "content": "Write a Python class"}]
    }
)
```

---

## 🚨 Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 11434 not responding | `docker restart model-runner` |
| Model not found | Pull it: `docker exec model-runner ollama pull <model>` |
| Out of memory | Switch to `tinyllama` (smallest model) |
| Slow responses | Normal for CPU-only — use GPU if available |
| GPU not detected | Check Docker Desktop GPU settings |

---

## 💾 Storage

Models stored in Docker volume `ollama_data`.
To save disk space — only pull what you use!

```bash
# Remove a model
docker exec model-runner ollama rm mistral

# Check disk usage
docker exec model-runner ollama list
```

---
> **built with WelshDog + BROski 🚀🌙**
