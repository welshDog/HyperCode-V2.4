"""Shell-free startup for the HyperHealth DHI runtime."""
from __future__ import annotations

import os
import subprocess
import sys


if sys.argv[1:] == ["api"]:
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    os.execvp(
        "uvicorn",
        ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090", "--workers", "2"],
    )

if len(sys.argv) < 2:
    raise SystemExit("Expected 'api' or a command to execute")

# Compose overrides the API CMD for the worker service. Keep that command's
# arguments and process behavior intact without relying on a shell.
os.execvp(sys.argv[1], sys.argv[1:])
