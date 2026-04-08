---
name: hypercode-brain
description: The cognitive core of HyperCode. Handles LLM prompt assembly, memory injection, conversation history, RAG retrieval, and agent handoffs. Use when working on Brain.think(), memory caps, context overflow, prompt engineering, conversation persistence, or the handoff system between agents.
---

# HyperCode Brain Skill

## What is The Brain?

`backend/app/agents/brain.py` is the **cognitive core** — every agent that needs to
"think" calls `brain.think()`. It assembles the full LLM prompt by injecting:

1. System persona / role instructions
2. RAG snippets (Chroma vector search)
3. Agent handoff messages (from Redis inbox)
4. Conversation history (from Redis list)
5. The user's current message

Then calls the LLM, persists the response, and returns it.

---

## Key Files

| File | Purpose |
|---|---|
| `backend/app/agents/brain.py` | Core `Brain` class + `think()` method |
| `backend/app/core/agent_memory.py` | Redis memory primitives |
| `backend/app/core/rag.py` | Chroma vector store — ingest + query |
| `backend/app/services/plan_executor.py` | Writes handoffs between plan phases |
| `backend/app/api/v1/endpoints/memory.py` | REST API for memory ingest/query |

---

## Memory Architecture

### Short-term (Redis Lists)

```
memory:conversation:{conversation_id}   → capped list, max 50 entries, TTL 7 days
memory:handoff:{agent_id}               → capped list, max 100 entries, TTL 30 days
```

- `append_turn(conversation_id, role, content)` — adds a turn, auto-trims
- `get_history(conversation_id, n=20)` — fetches last N turns
- `write_handoff(to_agent_id, from_agent_id, summary, links)` — agent-to-agent messaging
- `read_handoffs(agent_id)` — reads + clears the inbox

### Long-term (Chroma RAG)

```
chunk_size=1000, chunk_overlap=200
POST /api/v1/memory/ingest  → content max 20,000 chars (superuser only)
POST /api/v1/memory/query   → query max 500 chars, limit ≤ 20 results
```

---

## Memory Injection Caps (Brain)

Hard character limits enforced in `_build_memory_context()`:

```python
MAX_HANDOFF_CHARS = 1500   # handoff messages injected into prompt
MAX_RAG_CHARS     = 2000   # RAG snippets injected into prompt
MAX_HISTORY_CHARS = 2000   # conversation history injected into prompt
```

Total injected context ceiling ≈ **5,500 chars** before the user message.
If total prompt approaches LLM context limit → trigger HyperSync handoff.

---

## Brain.think() Flow

```
1. Load agent persona / system prompt
2. _build_memory_context()
   ├─ read_handoffs()     → cap to MAX_HANDOFF_CHARS
   ├─ rag.query()         → cap to MAX_RAG_CHARS
   └─ get_history()       → cap to MAX_HISTORY_CHARS
3. Assemble full_prompt
4. ⚡ OVERFLOW CHECK — if len(full_prompt) > threshold → write_handoff() + HyperSync
5. Call LLM (OpenRouter / Anthropic / Ollama)
6. append_turn(user_message)    → persist user turn
7. append_turn(llm_response)    → persist assistant turn
8. Return response
```

---

## Handoff System

Handoffs carry context between agents without overloading prompts:

```python
# Write a handoff to another agent
write_handoff(
    to_agent_id="summarizer",
    from_agent_id="brain",
    summary="Context overflow — conversation compressed",
    links={"full_plan": plan_json, "conversation_id": conv_id}
)

# Read + clear inbox
handoffs = read_handoffs(agent_id="summarizer")
```

Plan execution writes a handoff per phase → `plan_executor.py` lines 97–124.

---

## Context Overflow Strategy

When `len(full_prompt) > OVERFLOW_THRESHOLD`:

1. `write_handoff()` to a **summarizer agent** with full conversation
2. Summarizer compresses → writes back a short summary handoff
3. Brain injects only the summary (fits within `MAX_HANDOFF_CHARS`)
4. OR trigger **HyperSync handoff** for cross-session continuity

Best hook point: `brain.py` after `full_prompt` is assembled, before LLM call.

---

## Secret Redaction

`agent_memory.py` auto-redacts secrets before storing turns:
- Patterns: API keys, tokens, passwords in content strings
- Runs on every `append_turn()` call
- Non-configurable — always on (hardened safety measure)

---

## LLM Config

```python
# max_tokens passed through to OpenRouter payload
# model_routes.py lines 92–127

# memstream API validates:
maxTokens: 1–4096
```

- Model selection via `model_routes.py` — supports OpenRouter, Anthropic, local Ollama
- All calls are async (`async/await`)
