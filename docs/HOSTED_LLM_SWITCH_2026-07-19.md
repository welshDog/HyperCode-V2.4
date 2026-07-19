# 🧠 Switch agents to hosted Claude — runbook

**Why:** 8GB machine → 4GB WSL2. Ollama needs ~3GB for one 3B model. Verified
2026-07-19: `ollama ps` empty, inference returned `EOF` (OOM). Every agent
depending on local inference was answering `/health` and doing nothing else.

**The fix is one env var per service** — the code already supports it:

```python
# agents/base-agent/agent.py :: _build_llm_client()
if os.getenv("ANTHROPIC_API_KEY"):
    return AsyncAnthropic(api_key=...)     # ← Claude
return _OllamaAdapter(...)                 # ← local fallback
```

Only **5 of 42** services were given the key, so 37 fell back to dead Ollama.
`docker-compose.hosted-llm.yml` hands it to all 19 that actually reason.

> This is also the architecture you already teach in Course M3:
> *"Claude = the strategist · Copilot = the sprinter · Ollama = the local player."*

---

## 1 · Set the key (one time)

The value is in `secrets/anthropic_api_key.txt`. Put it in `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

`.env` is gitignored — never commit it. The override uses `${ANTHROPIC_API_KEY:?...}`
so compose **fails loudly** if it's missing rather than silently falling back.

## 2 · Stop Ollama, free ~3GB

```powershell
docker stop hypercode-ollama
docker rm hypercode-ollama

# reclaim ~10GB of models nothing uses
docker exec hypercode-ollama ollama rm llama2:7b      # 3.8GB   (run BEFORE stopping)
docker exec hypercode-ollama ollama rm mistral:latest # 4.4GB
docker exec hypercode-ollama ollama rm phi3:latest    # dup of phi3:mini (same ID)
```

Keep `qwen2.5-coder:3b` + `nomic-embed-text` if you ever want local mode back.

## 3 · Bring agents up on Claude

```powershell
cd "H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4"
docker compose -f docker-compose.core.yml `
               -f docker-compose.agents.yml `
               -f docker-compose.hosted-llm.yml up -d
```

Preview the merge first if you want:
```powershell
docker compose -f docker-compose.agents.yml -f docker-compose.hosted-llm.yml config | Select-String "AGENT_MODEL"
```

## 4 · ✅ Prove an agent actually works

This is the step that matters — *not* a healthcheck.

```powershell
# key reached the container?
docker exec coder-agent printenv ANTHROPIC_API_KEY | ForEach-Object { $_.Substring(0,12) + "..." }
docker exec coder-agent printenv AGENT_MODEL

# real task, real output
curl -X POST http://127.0.0.1:8002/task `
  -H "Content-Type: application/json" `
  -d '{\"task\":\"Write a Python function that reverses a string. Code only.\"}'
```

**Green = actual generated code comes back.** If you get a 200 with an empty or
error body, the agent is still scenery — check `docker logs coder-agent --tail 30`.

---

## 💰 Cost control (your sacred rule)

Defaults in the override:

| Role | Model | Why |
|---|---|---|
| crew-orchestrator, hyper-architect, project-strategist, agent-x | **Sonnet** | reasoning + orchestration quality matters |
| the other 14 specialists | **Haiku** | fast, cheap, plenty for scoped tasks |
| all | `AGENT_MAX_TOKENS=1000` | hard cap on every response |

Tune in `.env` without touching compose:
```
AGENT_MODEL=claude-haiku-4-5-20251001
AGENT_MODEL_REASONING=claude-sonnet-4-6
AGENT_MAX_TOKENS=1000
```

⚠️ **Watch for polling.** 19 agents on a loop is how a bill runs away. Check any
agent that calls the LLM on a timer rather than on demand — that's the single
biggest cost risk in this design.

---

## ↩️ Revert to local inference

Nothing in your original compose files was modified. Just drop the override:

```powershell
docker compose -f docker-compose.core.yml -f docker-compose.agents.yml up -d
```

Ollama comes back as the fallback automatically — but remember it OOMs on 8GB
unless you're running a very small profile.

---

## Checklist

- [ ] `ANTHROPIC_API_KEY` in `.env`
- [ ] Unused models removed (~10GB back)
- [ ] Ollama stopped (~3GB back)
- [ ] Agents up with the override
- [ ] **Real task returns real output** (step 4)
- [ ] `docker stats` under load — should be far healthier without Ollama

> 🐶♾️ A healthcheck proves a web server is listening. Only a real task proves an agent works.
