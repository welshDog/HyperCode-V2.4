# Inter-Agent Memory Sharing (Redis + RAG) — Design Notes

## Goal

Make `Brain.think()` stateful across calls and capable of cross-agent collaboration by:

- Persisting per-agent conversation history (short-term memory) in Redis
- Publishing/consuming “handoff notes” between agents in Redis
- Storing durable knowledge artifacts in a vector store (RAG) for retrieval inside prompts

## Scope (Phase 1: Safe + Minimal)

- Add conversation history support to `Brain.think()` without changing external behavior by default.
- Support “agent-to-agent notes” (handoffs) that can be read before a think() call.
- Keep memory bounded, expiring, and secrets-safe.

## Data Model

### Conversation history (Redis)

- Key: `memory:conversation:{conversation_id}`
- Type: Redis list (append-only)
- Entry (JSON):
  - `ts` (ISO)
  - `agent_id` (string)
  - `role` (`system|user|assistant|tool`)
  - `content` (string)
  - `task_id` (optional int)
  - `tags` (optional list[str])
- Retention:
  - Cap list length (e.g., last 50 entries)
  - TTL (e.g., 7 days) to prevent unbounded growth

### Handoff notes (Redis)

- Key: `memory:handoff:{target_agent_id}`
- Type: Redis list (append-only)
- Entry (JSON):
  - `ts` (ISO)
  - `from_agent_id`
  - `to_agent_id`
  - `summary` (short, structured, bullet-friendly)
  - `links` (optional list of task ids / artifacts)
- Retention:
  - Cap list length (e.g., last 100)
  - TTL (e.g., 30 days)

### Durable memory (RAG)

- Store stable artifacts only (runbooks, decisions, “known-good fixes”, interface contracts).
- Store a normalized “memory document” format:
  - `doc_id`, `title`, `body`, `tags`, `source` (task/report/guide), `created_at`
- Retrieval returns top-k snippets for prompt injection.

## Prompt Integration (Brain.think)

### New inputs

- `conversation_id: str | None`
- `agent_id: str` (caller)
- `memory_mode: none|self|shared`
- `handoff_mode: none|inbox|inbox+rag`

### Prompt assembly order (recommended)

1. System instructions (existing)
2. “Handoff inbox” (if enabled, newest first, hard-capped)
3. Retrieved RAG snippets (if enabled, top-k, hard-capped)
4. Conversation history (if enabled, last N turns)
5. Current task prompt

### Guardrails

- Run content through existing secret-redaction before persistence and before injection.
- Hard cap injected memory tokens/characters (fail closed by truncating memory, not task prompt).
- Never store raw credentials, tokens, or full environment dumps.

## Integration Points

- Agent completions:
  - On successful completion, write a “handoff note” to relevant downstream agents.
  - Optionally write a “summary memory doc” into RAG if it’s durable knowledge.
- Task pipeline:
  - Create a `conversation_id` per task and thread it through Router → Agents → Brain.

## Testing Requirements

- Unit tests:
  - Memory append + trim + TTL behavior (Redis mocked)
  - Handoff read/clear semantics
  - Prompt builder includes memory in correct order and respects caps
  - Secret-redaction applied before persistence and injection
- Integration tests:
  - Two agents share a note; downstream agent consumes it and removes/marks handled

## Security & Privacy

- Treat all memory as sensitive by default.
- Minimize data: store summaries, not raw dumps.
- Add an allowlist of which fields can enter durable RAG.
- Provide a “purge conversation” operation (admin-only) for incident response.

