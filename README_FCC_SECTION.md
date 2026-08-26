## 🆓 Free Claude Code Integration

HyperCode-V2.4 includes native support for **Free Claude Code (FCC)** — an open-source proxy that routes Claude Code traffic to free AI backends including local Ollama, NVIDIA NIM free tier, OpenRouter, and Gemini.

### Quick Start

```bash
cp fcc.env.example .env
docker compose -f docker-compose.fcc.yml up -d --build
curl http://localhost:8082/health
```

### VS Code Setup

```json
"claudeCode.disableLoginPrompt": true,
"claudeCode.environmentVariables": [
  { "name": "ANTHROPIC_BASE_URL", "value": "http://localhost:8082" },
  { "name": "ANTHROPIC_AUTH_TOKEN", "value": "freecc" }
]
```

### Free Model Backends

| Provider | Environment Variable | Free Allowance |
|----------|---------------------|----------------|
| Local Ollama | OLLAMA_BASE_URL | Unlimited (local) |
| NVIDIA NIM | NVIDIA_NIM_API_KEY | 40 req/min |
| OpenRouter | OPENROUTER_API_KEY | Free tier routes |
| Gemini | GEMINI_API_KEY | Free tier |

See QUICKSTART_FCC.md for full setup guide.
