# Brain Patterns & Gotchas

## Adding a new agent that uses Brain

1. Import `Brain` from `backend/app/agents/brain.py`
2. Initialise with `agent_id`, `persona`, `model` params
3. Call `await brain.think(user_message, conversation_id=...)`
4. Brain handles all memory — you don't manually call Redis
5. Set `auto_evolve: true` in `agent_spec.json` if agent should self-improve

## Memory not persisting between sessions?

- Check `conversation_id` is consistent — different IDs = separate history
- Redis TTL is 7 days — history expires naturally
- History capped at 50 turns — oldest entries pruned automatically

## RAG returning irrelevant results?

- Re-ingest with better chunking: `POST /api/v1/memory/ingest`
- Query is capped at 500 chars — keep it focused
- Default `limit=20` results — tune down for speed
- Chunk overlap (200) helps with boundary splits

## Handoff inbox filling up?

- Max 100 entries, TTL 30 days
- `read_handoffs()` clears the inbox on read (destructive read)
- Don't call `read_handoffs()` more than once per agent cycle

## Prompt injection protection

- `aad` binding in HyperSync envelopes prevents cross-endpoint payload replay
- Brain does NOT currently sanitise user input before LLM — add if exposing to untrusted users
- Secret redaction runs on STORAGE (append_turn), not on the live prompt assembly
