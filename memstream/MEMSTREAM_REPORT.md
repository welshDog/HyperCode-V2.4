# 🧠 MemStream Engine — Phase 1 & 2 Completion Report

> **Built by:** Lyndz Williams (@welshDog) — Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁥  
> **Date:** 06 April 2026  
> **Part of:** [HyperCode V2.4](https://github.com/welshDog/HyperCode-V2.4) — Neurodivergent-first AI coding ecosystem

---

## 🎯 What Is MemStream?

MemStream is a **smart local AI inference engine** built for budget hardware.  
It runs a full Mistral 7B model on a GTX 1650 (3.9GB VRAM) with:
- Automatic hardware tier detection
- Graceful degradation cascade (GPU → CPU → 4bit → token stream)
- RAM pressure monitoring + self-throttling
- Full HTTP API with SSE streaming

> "Smart memory, not expensive memory."

---

## 🏆 Performance Journey — One Day

| Time | Mode | Speed | What Changed |
|---|---|---|---|
| Morning | TOKEN_STREAM | 0.1 tok/s | Starting point — RAM starved |
| After RAM fix | TOKEN_STREAM | 0.6 tok/s | Freed system RAM (6x boost) |
| GPU unlocked | GPU_LAYERS 10 | 0.7 tok/s | Fixed VRAM threshold (was 4.0 → 3.5) |
| 20 layers | GPU_LAYERS 20 | 0.9 tok/s | More layers on VRAM |
| 28 layers | GPU_LAYERS 28 | 1.1 tok/s | Pushing harder |
| 32 layers | GPU_LAYERS 32 | 1.3 tok/s | 🏆 FULL MODEL ON GPU! |

**Result: 13x faster on the same machine. Zero hardware upgrades.**

---

## 🛠️ Architecture

```
memstream/src/
├── memstream.ts     ← CLI entrypoint (npm start)
├── server.ts        ← HTTP server entrypoint (npm run serve)
├── api.ts           ← POST /generate endpoint
├── health.ts        ← Health server + throttle control
├── hardware.ts      ← RAM/VRAM detection
├── degradation.ts   ← Run mode selector
└── logger.ts        ← CSV telemetry writer
```

---

## 🌐 HTTP API

### Start the server
```powershell
$env:MEMSTREAM_HEALTH_TOKEN = "your-health-token"
$env:MEMSTREAM_API_TOKEN    = "your-api-token"
$env:MEMSTREAM_GPU_LAYERS   = "32"
$env:MEMSTREAM_CTX_TOKENS   = "1024"
npm run serve
```

### Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/generate` | API token | Run inference |
| GET | `/health/memstream` | Health token | RAM, pressure, tok/s |
| POST | `/throttle` | Health token | Set per-token delay |
| GET | `/metrics` | Health token | Prometheus format |

### Example — Non-Streaming
```powershell
$h = @{ Authorization = "Bearer your-api-token" }
$body = @{ prompt = "What is HyperCode?"; stream = $false; max_tokens = 200 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8011/generate" -Headers $h -Body $body -ContentType "application/json"
```

### Example Response
```json
{
  "id": "gen_1775511941801",
  "model": "mistral-7b-instruct-v0.2.Q2_K",
  "output": "HyperCode is a neurodivergent-first AI coding ecosystem...",
  "finish_reason": "stop",
  "elapsed_ms": 107556,
  "tokens": 45,
  "health": {
    "ram_used_percent": 93.8,
    "ram_free_gb": 0.48,
    "tokens_per_sec": 0.43,
    "current_mode": "api_generate",
    "pressure": "🔴 HIGH",
    "timestamp": "2026-04-06T21:45:41Z"
  }
}
```

### Example — SSE Streaming
```powershell
$body = @{ prompt = "Tell me about HyperCode"; stream = $true; max_tokens = 100 } | ConvertTo-Json
Invoke-WebRequest -Uri "http://127.0.0.1:8011/generate" -Method POST -Headers $h -Body $body
```

Stream events:
```
event: open
data: {"id":"gen_xxx","model":"mistral-7b-instruct-v0.2.Q2_K"}

event: token
data: {"text":"HyperCode "}

event: done
data: {"finish_reason":"stop","elapsed_ms":12345,"tokens":42}
```

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MEMSTREAM_HEALTH_TOKEN` | *(required)* | Bearer token for health endpoints |
| `MEMSTREAM_API_TOKEN` | *(required)* | Bearer token for /generate |
| `MEMSTREAM_HEALTH_PORT` | `8009` | Health server port |
| `MEMSTREAM_API_PORT` | `8011` | API server port |
| `MEMSTREAM_GPU_LAYERS` | auto | Override GPU layer count |
| `MEMSTREAM_CTX_TOKENS` | auto | Override context window size |
| `MEMSTREAM_MIN_FREE_RAM_GB` | `2.0` | Minimum free RAM for GPU mode |

---

## 🔥 Degradation Cascade

MemStream automatically picks the best mode for your hardware:

```
🟢 GPU_LAYERS   → VRAM >= 3.5GB + RAM OK  → fastest
🟡 CPU          → RAM >= 8GB free          → medium  
🟠 CPU_4BIT     → RAM >= min threshold     → slower
🔴 TOKEN_STREAM → any hardware             → slowest but never crashes
```

---

## 📊 Telemetry

Every run writes to `./logs/layer_times.csv`:
- Token timestamps
- Tokens per second
- RAM pressure state
- Run mode used

---

## 🚀 What's Next

- [ ] Phase 2D — Dashboard widget in Mission Control
- [ ] Phase 3A — Discord bot `!ask` command
- [ ] Phase 3B — HyperCode agents calling local AI
- [ ] Phase 3C — Docker mode + Healer auto-restart
- [ ] Phase 4 — Multi-model support

---

## 💜 Built With

- [`node-llama-cpp`](https://github.com/withcatai/node-llama-cpp) — GGUF inference in Node.js
- [Mistral 7B Instruct v0.2 Q2_K](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF) — the model
- TypeScript + tsx
- Windows 11 + GTX 1650 4GB
- Pure determination 🏴󠁧󠁢󠁷󠁬󠁳󠁥⚡

---

> *"Smart memory, not expensive memory."*  
> *Built in one day. By one developer. On a budget machine. For everyone.*  
> — Lyndz Williams, HyperCode 🧠
