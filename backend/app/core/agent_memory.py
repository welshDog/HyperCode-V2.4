"""
agent_memory.py — Redis-backed inter-agent memory for HyperCode V2.0

Provides:
  - Per-conversation turn history (short-term memory)
  - Agent-to-agent handoff notes
  - Secret redaction before any persistence or injection
  - Bounded lists + TTL so memory never silently bloats

Design spec: docs/architecture/INTER_AGENT_MEMORY_SHARING.md
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — tune in config later if needed
# ---------------------------------------------------------------------------
HISTORY_MAX_ENTRIES = 50          # max turns kept per conversation
HANDOFF_MAX_ENTRIES = 100         # max handoff notes per agent inbox
HISTORY_TTL_SECONDS = 60 * 60 * 24 * 7     # 7 days
HANDOFF_TTL_SECONDS = 60 * 60 * 24 * 30    # 30 days

# Patterns that should NEVER be stored — fail closed
_SECRET_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)(api[_-]?key|bearer|token|secret|password|passwd|pwd)\s*[:=]\s*\S+"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),          # OpenAI-style keys
    re.compile(r"pplx-[A-Za-z0-9]{20,}"),         # Perplexity keys
    re.compile(r"[A-Za-z0-9+/]{40,}={0,2}"),      # raw base64 blobs
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _redact(text: str) -> str:
    """Strip secrets before any content enters memory."""
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_redis():
    """Lazy import — returns a redis.Redis client or None if unavailable."""
    try:
        from app.core.config import settings
        import redis
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        client.ping()
        return client
    except Exception as exc:
        logger.warning(f"[AGENT_MEMORY] Redis unavailable — memory disabled: {exc}")
        return None


# ---------------------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------------------

def append_turn(
    conversation_id: str,
    agent_id: str,
    role: str,
    content: str,
    task_id: int | None = None,
    tags: list[str] | None = None,
) -> bool:
    """
    Append one turn to a conversation history list in Redis.

    Returns True on success, False if Redis is unavailable (never raises).
    """
    r = _get_redis()
    if r is None:
        return False
    try:
        entry = json.dumps({
            "ts": _now_iso(),
            "agent_id": agent_id,
            "role": role,
            "content": _redact(content),
            "task_id": task_id,
            "tags": tags or [],
        })
        key = f"memory:conversation:{conversation_id}"
        pipe = r.pipeline()
        pipe.rpush(key, entry)
        pipe.ltrim(key, -HISTORY_MAX_ENTRIES, -1)   # keep last N entries
        pipe.expire(key, HISTORY_TTL_SECONDS)
        pipe.execute()
        logger.debug(f"[AGENT_MEMORY] Appended turn to {key} (role={role})")
        return True
    except Exception as exc:
        logger.warning(f"[AGENT_MEMORY] append_turn failed: {exc}")
        return False


def get_history(
    conversation_id: str,
    last_n: int = 10,
) -> list[dict[str, Any]]:
    """
    Return the last `last_n` turns for a conversation.
    Returns [] if Redis unavailable or key missing (never raises).
    """
    r = _get_redis()
    if r is None:
        return []
    try:
        key = f"memory:conversation:{conversation_id}"
        raw_entries = r.lrange(key, -last_n, -1)
        return [json.loads(e) for e in raw_entries]
    except Exception as exc:
        logger.warning(f"[AGENT_MEMORY] get_history failed: {exc}")
        return []


def clear_conversation(conversation_id: str) -> bool:
    """Admin/incident-response: wipe a full conversation from memory."""
    r = _get_redis()
    if r is None:
        return False
    try:
        r.delete(f"memory:conversation:{conversation_id}")
        logger.info(f"[AGENT_MEMORY] Purged conversation: {conversation_id}")
        return True
    except Exception as exc:
        logger.warning(f"[AGENT_MEMORY] clear_conversation failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Agent-to-agent handoff notes
# ---------------------------------------------------------------------------

def write_handoff(
    to_agent_id: str,
    from_agent_id: str,
    summary: str,
    links: list[Any] | None = None,
) -> bool:
    """
    Leave a structured handoff note in the target agent's inbox.

    Returns True on success, False if Redis unavailable (never raises).
    """
    r = _get_redis()
    if r is None:
        return False
    try:
        note = json.dumps({
            "ts": _now_iso(),
            "from_agent_id": from_agent_id,
            "to_agent_id": to_agent_id,
            "summary": _redact(summary),
            "links": links or [],
        })
        key = f"memory:handoff:{to_agent_id}"
        pipe = r.pipeline()
        pipe.rpush(key, note)
        pipe.ltrim(key, -HANDOFF_MAX_ENTRIES, -1)
        pipe.expire(key, HANDOFF_TTL_SECONDS)
        pipe.execute()
        logger.info(f"[AGENT_MEMORY] Handoff written: {from_agent_id} -> {to_agent_id}")
        return True
    except Exception as exc:
        logger.warning(f"[AGENT_MEMORY] write_handoff failed: {exc}")
        return False


def read_handoffs(
    agent_id: str,
    limit: int = 5,
    consume: bool = False,
) -> list[dict[str, Any]]:
    """
    Read the latest `limit` handoff notes for an agent.

    If consume=True, removes the returned notes from the inbox
    (so each note is processed exactly once).

    Returns [] if Redis unavailable (never raises).
    """
    r = _get_redis()
    if r is None:
        return []
    try:
        key = f"memory:handoff:{agent_id}"
        raw_notes = r.lrange(key, 0, limit - 1)
        notes = [json.loads(n) for n in raw_notes]
        if consume and notes:
            # Trim the consumed entries from the front of the list
            pipe = r.pipeline()
            pipe.ltrim(key, len(notes), -1)
            pipe.execute()
            logger.debug(f"[AGENT_MEMORY] Consumed {len(notes)} handoffs for {agent_id}")
        return notes
    except Exception as exc:
        logger.warning(f"[AGENT_MEMORY] read_handoffs failed: {exc}")
        return []


def clear_handoffs(agent_id: str) -> bool:
    """Admin/incident-response: wipe all handoff notes for an agent."""
    r = _get_redis()
    if r is None:
        return False
    try:
        r.delete(f"memory:handoff:{agent_id}")
        logger.info(f"[AGENT_MEMORY] Cleared handoff inbox for {agent_id}")
        return True
    except Exception as exc:
        logger.warning(f"[AGENT_MEMORY] clear_handoffs failed: {exc}")
        return False
