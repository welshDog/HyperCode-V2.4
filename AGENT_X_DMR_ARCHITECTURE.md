# Docker Model Runner (DMR) Integration Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Your 8GB Host                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────┐   ┌───────────────────────────┐   │
│  │   Agent X Container          │   │  DMR Sidecar Container    │   │
│  │   (port 8080)                │   │  (port 12434)             │   │
│  │                              │   │                           │   │
│  │  ┌────────────────────────┐  │   │  ┌─────────────────────┐  │   │
│  │  │ main.py               │  │   │  │ Model Runner        │  │   │
│  │  │ └─> AgentXCore        │  │   │  │ Daemon              │  │   │
│  │  │     └─> dmr_client.py │  │   │  │                     │  │   │
│  │  └────────────────────────┘  │   │  │ Qwen2.5-7B (7GB)    │  │   │
│  │         │                     │   │  │ SmolLM2-360M (1GB)  │  │   │
│  │         │ HTTP POST           │   │  │                     │  │   │
│  │         ├──────────────────────────► /v1/chat/completions │  │   │
│  │         │                     │   │  │                     │  │   │
│  │         │◄──────────────────────── │ Returns: OpenAI fmt  │  │   │
│  │         │ JSON response       │   │  │                     │  │   │
│  │  Resources:                   │   │  │ Auto-unload: 5min   │  │   │
│  │  - CPU: 1-2 CPUs             │   │  │ idle timeout        │  │   │
│  │  - RAM: 1.5-2GB              │   │  │                     │  │   │
│  └──────────────────────────────┘   │  └─────────────────────┘  │   │
│                                      │                           │   │
│                                      │  Resources:               │   │
│                                      │  - CPU: 2-3 CPUs         │   │
│                                      │  - RAM: 5-6GB            │   │
│                                      │  - Storage: model cache  │   │
│                                      │    (volume)              │   │
│                                      └───────────────────────────┘   │
│                                                                       │
│  Shared: localhost (host networking) + dmr-models-cache volume      │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Request Flow

```
1. AGENT X REQUEST
   ┌──────────────────────────────────┐
   │ agent.infer("Write Dockerfile")  │
   └──────────────────────────────────┘
                    │
                    ▼
   ┌──────────────────────────────────┐
   │ DMRClient.infer()                │
   │ ├─ Check: DMR reachable? YES     │
   │ └─ Build payload: model, prompt  │
   └──────────────────────────────────┘
                    │
                    ▼
2. HTTP REQUEST TO DMR
   ┌──────────────────────────────────┐
   │ POST /v1/chat/completions        │
   │ {                                │
   │   "model": "qwen2.5-coder:7b",   │
   │   "messages": [...]              │
   │ }                                │
   └──────────────────────────────────┘
                    │
                    ▼
3. DMR PROCESSING
   ┌──────────────────────────────────┐
   │ Check model cache                │
   ├─ Model in memory? YES ──────────┐│
   │                                  ││
   │ Model in cache? YES              ││
   ├─ Load from disk (20s) ──────────┐││
   │                                  │││
   │ Model not cached?                │││
   ├─ Download from registry (40s)   ││
   │  + Quantize                      │││
   │                                  │││
   └──────────────────────────────────┘││
                    │                   │
                    ▼                   │
   ┌──────────────────────────────────┐│
   │ Run inference (llama.cpp)        ││
   │ ├─ Prompt tokenization           ││
   │ ├─ LLM forward passes            ││
   │ └─ Stream tokens back            ││
   └──────────────────────────────────┘│
                    │                   │
                    ▼                   │
4. HTTP RESPONSE FROM DMR             │
   ┌──────────────────────────────────┐
   │ {                                │
   │   "choices": [{                  │
   │     "message": {                 │
   │       "content": "FROM python..." │
   │     }                            │
   │   }],                            │
   │   "usage": {                     │
   │     "total_tokens": 256          │
   │   }                              │
   │ }                                │
   └──────────────────────────────────┘
                    │
                    ▼
5. AGENT X PROCESSES RESPONSE
   ┌──────────────────────────────────┐
   │ Parse JSON + extract content     │
   │ Record metrics:                  │
   │ - latency_ms: 1250               │
   │ - total_tokens: 256              │
   │ - fallback_used: false           │
   └──────────────────────────────────┘
                    │
                    ▼
   ┌──────────────────────────────────┐
   │ Return response to caller        │
   └──────────────────────────────────┘
```

## Fallback Flow (On Timeout)

```
1. PRIMARY MODEL SLOW
   ┌────────────────────────────────────┐
   │ infer("Generate code")             │
   │ timeout_ms=60,000 (60s max)        │
   └────────────────────────────────────┘
                    │
                    ▼
   ┌────────────────────────────────────┐
   │ POST /v1/chat/completions          │
   │ model: "qwen2.5-coder:7b"          │
   │ (model loading + inference)        │
   └────────────────────────────────────┘
                    │
      ┌─────┬──────┴──────┬──────┐
      │ 30s │    45s      │ 60s+ │
      ▼     ▼             ▼      ▼
   LOAD  WAIT FOR     WAITING  TIMEOUT!
                      RESPONSE
                                 │
                                 ▼
2. FALLBACK TRIGGERED
   ┌────────────────────────────────────┐
   │ Primary timeout → use fallback     │
   │ Retry with: "smollm2:360m"         │
   │ (loads instantly, ~3GB)            │
   └────────────────────────────────────┘
                    │
                    ▼
   ┌────────────────────────────────────┐
   │ POST /v1/chat/completions          │
   │ model: "smollm2:360m"              │
   │ (loads in ~1s, infers ~500ms)      │
   └────────────────────────────────────┘
                    │
                    ▼
   ┌────────────────────────────────────┐
   │ Response arrives (2s total)        │
   │ Metrics recorded:                  │
   │ - fallback_used: TRUE ✓            │
   │ - model: "smollm2:360m"            │
   │ - latency_ms: 2000                 │
   └────────────────────────────────────┘
```

## Model Lifecycle

```
TIMELINE: Time from when Agent X starts

t=0s ──────────────────────────────────────────────────────────────
     Container startup

t=5s ──────────────────────────────────────────────────────────────
     preload_models() called
     ├─ Background task: download + load Qwen2.5-7B
     ├─ Background task: download + load SmolLM2-360M
     └─ Both return immediately (background)

t=20s ─────────────────────────────────────────────────────────────
      User: infer("Write code")
      ├─ Qwen2.5-7B already loaded ✓
      └─ Inference starts immediately (500ms-2s)

t=25s ─────────────────────────────────────────────────────────────
      Response returned, model stays in memory

t=30s ─────────────────────────────────────────────────────────────
      [idle, no requests]
      
      ...

t=330s ────────────────────────────────────────────────────────────
       [5 minutes with no requests]
       ├─ Qwen2.5-7B: auto-unloaded from memory
       │  (model still cached on disk, can reload in ~500ms)
       │
       └─ SmolLM2-360M: auto-unloaded from memory
          (model still cached on disk, can reload in ~100ms)

t=335s ────────────────────────────────────────────────────────────
       User: infer("Another task")
       ├─ Models not in memory, load from cache (1-2s)
       └─ Inference runs

t=340s ────────────────────────────────────────────────────────────
       Response returned, models stay in memory until 340+300=640s
```

## Deployment Diagram

```
┌───────────────────────────────────────────────────┐
│ docker-compose.yml (your existing setup)          │
│                                                   │
│ services:                                         │
│   agent-x:                                        │
│     image: hypercode-v24-agent-x:dmr             │
│     environment:                                  │
│       DMR_HOST: http://127.0.0.1:12434           │
│       DMR_MODEL: ai/qwen2.5-coder:7b             │
│       DMR_FALLBACK: ai/smollm2:360m              │
│     network_mode: host                            │
│     depends_on: [dmr-runner]                      │
└───────────────────────────────────────────────────┘
                         │
                         ▼
┌───────────────────────────────────────────────────┐
│ docker-compose.dmr.yml (NEW - DMR sidecar)        │
│                                                   │
│ services:                                         │
│   dmr-runner:                                     │
│     image: docker:latest                          │
│     network_mode: host                            │
│     volumes:                                      │
│       - /var/run/docker.sock:/var/run/docker.so  │
│       - dmr-models-cache:/var/lib/dmr             │
│     deploy:                                       │
│       cpus: '3'                                   │
│       memory: 6G                                  │
│                                                   │
│ volumes:                                          │
│   dmr-models-cache: {}                            │
└───────────────────────────────────────────────────┘
                         │
                         ▼
  Run: docker compose -f docker-compose.yml \
                     -f docker-compose.dmr.yml \
                     up agent-x
```

## File Layout

```
agents/agent-x/
├── Dockerfile                      (existing, no changes)
├── requirements.txt                (+ dmr_requirements.txt)
├── agentx/
│   ├── main.py                     (updated to use DMRClient)
│   ├── dmr_client.py              (✨ NEW)
│   ├── integration_example.py      (✨ NEW)
│   └── ... (other agent modules)
└── dmr_requirements.txt            (✨ NEW)

Project root:
├── docker-compose.yml              (existing)
├── docker-compose.dmr.yml          (✨ NEW)
├── test_dmr_client.py              (✨ NEW)
├── AGENT_X_DMR_INTEGRATION.md       (✨ NEW)
└── AGENT_X_DMR_SUMMARY.md          (✨ NEW)
```

## State Transitions

```
AGENT X STATE MACHINE
═════════════════════════════════════════════════════

[Starting] 
    │
    ├─ await agent.startup()
    │
    ▼
[Initializing DMR]
    │
    ├─ DMRClient.__init__()
    ├─ await dmr_client._ensure_session()
    ├─ await dmr_client.preload_models()
    │
    ▼
[Ready] ◄─────────────────────────────┐
    │                                  │
    ├─ User: await agent.infer(...)   │
    │                                  │
    ├─ DMRClient._call_api()          │
    │  ├─ [Calling DMR]               │
    │  │  ├─ [Model Loading]          │
    │  │  ├─ [Inference]              │
    │  │  └─ [Streaming Response]     │
    │  │                              │
    │  └─ [Response Complete]         │
    │                                  │
    ├─ Record metrics                  │
    │                                  │
    └─ Return response ─────────────────┘

[Idle] (5 min)
    │
    ├─ Models auto-unload
    │
    └─ Back to [Ready] on next request
```

## Error Handling Tree

```
infer() called
    │
    ├─ Try primary model (qwen2.5-7b)
    │   │
    │   ├─ Status 200? ✓ Return response
    │   │
    │   ├─ Status 503 (loading)?
    │   │   ├─ Attempt < max_retries?
    │   │   │   ├─ YES: Wait 1-10s, retry
    │   │   │   └─ NO: Raise ModelNotAvailableError
    │   │   │
    │   │   └─ use_fallback=True?
    │   │       ├─ YES: Try fallback model ▼
    │   │       └─ NO: Re-raise
    │   │
    │   ├─ Status 429 (rate limited)?
    │   │   ├─ Attempt < max_retries?
    │   │   │   ├─ YES: Wait 5s, retry
    │   │   │   └─ NO: Raise DMRClientError
    │   │   │
    │   │   └─ use_fallback=True?
    │   │       ├─ YES: Try fallback ▼
    │   │       └─ NO: Re-raise
    │   │
    │   ├─ Status 400 (bad request)?
    │   │   └─ Raise DMRClientError (model not valid)
    │   │
    │   ├─ Timeout?
    │   │   └─ use_fallback=True?
    │   │       ├─ YES: Try fallback ▼
    │   │       └─ NO: Raise InferenceTimeoutError
    │   │
    │   └─ Other error? Raise DMRClientError
    │
    ├─ Try fallback model (smollm2-360m)
    │   │
    │   ├─ Status 200? ✓ Return response + fallback_used=TRUE
    │   │
    │   ├─ Status 503?
    │   │   └─ Raise ModelNotAvailableError
    │   │
    │   └─ Other error?
    │       └─ Raise DMRClientError
    │
    └─ Metrics recorded
        (including fallback_used flag)
```

---

**This is the complete architecture for Agent X + DMR integration. Ready to deploy! 🚀**
