"""Secret redaction for anything a crew agent returns, before it is stored or shown.

Never trust an agent, tool or log to remove secrets for you. Applied to every dispatch result
before it enters run history, evidence or a Calm Card. Adapted from the AG-UI adapter research
(``redaction.py``) and extended with the repo's own ``scrub_text``.
"""

from __future__ import annotations

import re
from typing import Any

from app.broski_operator.recover import scrub_text

REDACTED = "[REDACTED]"

_SENSITIVE_KEY_PARTS = (
    "api_key", "apikey", "authorization", "cookie", "password", "passwd",
    "secret", "token", "private_key", "credential",
)

_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),                       # OpenAI/Anthropic style keys
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),                  # GitHub tokens
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[A-Z0-9]{16}"),                             # AWS access key id
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),                 # Slack tokens
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),  # JWTs
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)"),
)


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


def redact_text(text: str) -> str:
    out = text
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub(REDACTED, out)
    return scrub_text(out)


def redact_value(value: Any, key: str = "") -> Any:
    """Redact strings, and whole values under sensitive keys, through dicts and lists."""
    if key and is_sensitive_key(key):
        return REDACTED
    if isinstance(value, dict):
        return {k: redact_value(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value
