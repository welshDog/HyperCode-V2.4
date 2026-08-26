# Free Claude Code (FCC) — Quick Start Guide

HyperCode-V2.4 Integration | 26 August 2026

## What Is Free Claude Code?

Free Claude Code (FCC) is an open-source proxy that intercepts traffic from Claude Code CLI/VS Code/JetBrains and reroutes it to free AI backends.

Official source: https://github.com/Alishahryar1/free-claude-code

> Only use the official repo above — fake repos distributing malware circulated in early 2026.

## Step 1 — Get Free API Keys

NVIDIA NIM: https://build.nvidia.com/settings/api-keys (recommended, 40 req/min)
OpenRouter: https://openrouter.ai/keys
Gemini: https://aistudio.google.com/app/apikey

## Step 2 — Configure Environment

```bash
cp fcc.env.example .env
```

## Step 3 — Build and Start

```bash
docker compose -f docker-compose.fcc.yml up -d --build
docker logs fcc-proxy -f
curl http://localhost:8082/health
```

## Step 4 — VS Code Setup

```json
"claudeCode.disableLoginPrompt": true,
"claudeCode.environmentVariables": [
  { "name": "ANTHROPIC_BASE_URL", "value": "http://localhost:8082" },
  { "name": "ANTHROPIC_AUTH_TOKEN", "value": "freecc" }
]
```

## Troubleshooting

- Port 8082 in use: change PORT in .env
- Network not found: verify hypercode_agents-net with `docker network ls`
- Ollama models missing: `docker exec hypercode-ollama ollama pull llama3.1`
- NVIDIA NIM 401: check API key, restart with `docker compose -f docker-compose.fcc.yml restart`
