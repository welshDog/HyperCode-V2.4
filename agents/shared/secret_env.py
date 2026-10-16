"""CANONICAL source of `read_secret` - read a secret from a Docker/Compose secret file, else a plain env var.

`read_secret("HYPERCODE_API_KEY")` returns, in order:
  1. the stripped contents of the file named by `HYPERCODE_API_KEY_FILE` (when set, readable and non-empty),
  2. else the value of the `HYPERCODE_API_KEY` environment variable,
  3. else `default` ("").

Behaviour is IDENTICAL to a bare `os.getenv(name)` until a `<NAME>_FILE` variable is actually set, so adopting
it changes nothing in existing deployments. The file wins once configured so a deployment using Compose secrets
never needs the value in `.env` or in the container's environment block.

Agents ship as isolated images/dirs and cannot all import this module, so the function below is VENDORED
(copied verbatim, between `# >>> vendored` / `# <<< vendored` markers) into each agent file that reads a key.
Edit ONLY this file, then run `python scripts/vendor_secret_env.py`; `python scripts/vendor_secret_env.py --check`
(and .github/scripts/tests/test_agent_secret_env_sync.py) fail if any copy has drifted.
"""
from __future__ import annotations

import os


def read_secret(name, default=""):
    """`<name>_FILE` (a Compose/Docker secret file) wins; else the `<name>` env var; else `default`."""
    path = os.environ.get(name + "_FILE", "").strip()
    if path:
        try:
            # utf-8-sig drops a Windows-editor BOM instead of letting it become part of the compared/sent value
            with open(path, "r", encoding="utf-8-sig") as fh:
                value = fh.read().strip()
        except (OSError, UnicodeDecodeError):
            value = ""
        if value:
            return value
    return os.environ.get(name, default)
