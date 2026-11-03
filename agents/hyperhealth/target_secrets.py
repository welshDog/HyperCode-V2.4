"""Keep credentials out of HyperHealth check definitions.

A check ``target`` is stored in the database and returned by ``GET /checks``. A DSN such as
``postgresql://user:password@host/db`` would therefore leak its password to every API-key holder.

Two small helpers fix that:

* ``resolve_target("env:DATABASE_URL")`` - the worker looks the real value up in its own
  environment at check time, so the stored target is only the variable's *name*.
* ``mask_target(text)`` - replaces the password in any ``scheme://user:password@host`` found in
  ``text`` with ``***``. Applied to API output and to check messages as defence in depth, so a
  credential someone stores directly is still not echoed back.

Dependency-free on purpose (stdlib only) so it can be unit-tested without FastAPI or a database.
"""
from __future__ import annotations

import os
import re

ENV_PREFIX = "env:"

# scheme://<userinfo>@  - userinfo runs to the LAST '@' of the authority (a password may contain '@').
_URL_USERINFO = re.compile(r"(?P<scheme>[A-Za-z][A-Za-z0-9+.\-]*://)(?P<userinfo>[^/\s?#]*)@")


def mask_target(text):
    """Return ``text`` with any URL password replaced by ``***`` (non-strings pass through)."""
    if not isinstance(text, str):
        return text

    def _sub(match: "re.Match[str]") -> str:
        userinfo = match.group("userinfo")
        if ":" not in userinfo:  # user only, no password
            return match.group(0)
        user = userinfo.split(":", 1)[0]
        return f"{match.group('scheme')}{user}:***@"

    return _URL_USERINFO.sub(_sub, text)


def resolve_target(target: str) -> str:
    """Resolve ``env:NAME`` to the value of environment variable NAME; anything else is unchanged.

    Raises ``ValueError`` (naming the variable, never its value) when the variable is unset/empty.
    """
    if isinstance(target, str) and target.startswith(ENV_PREFIX):
        name = target[len(ENV_PREFIX):].strip()
        value = os.environ.get(name, "")
        if not value:
            raise ValueError(f"target environment variable {name or '(empty name)'} is not set")
        return value
    return target
