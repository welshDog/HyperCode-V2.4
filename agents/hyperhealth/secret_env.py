"""Load a secret from a Docker/Compose secret file, falling back to a plain env var.

`read_secret("API_KEY")` returns, in order:
  1. the stripped contents of the file named by `API_KEY_FILE` (when set, readable and non-empty),
  2. else the value of the `API_KEY` environment variable,
  3. else "".

The file wins so that a deployment using Compose secrets never needs the value in `.env` or in the
container's environment block. The plain env var remains as the fallback for local dev and tests.
"""
from __future__ import annotations

import os
from pathlib import Path


def read_secret(name: str, default: str = "") -> str:
    file_path = os.environ.get(f"{name}_FILE", "").strip()
    if file_path:
        try:
            value = Path(file_path).read_text(encoding="utf-8").strip()
        except OSError:
            value = ""
        if value:
            return value
    return os.environ.get(name, default)
