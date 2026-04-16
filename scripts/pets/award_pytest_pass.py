import os
import subprocess
import sys


def _env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None or val == "":
        raise SystemExit(f"Missing env var: {name}")
    return val


def main() -> None:
    rc = subprocess.call([sys.executable, "-m", "pytest"])
    if rc != 0:
        raise SystemExit(rc)
    subprocess.check_call(
        [sys.executable, "scripts/pets/award_xp.py", "50", "Pytest all green", "pytest_local"],
        env=os.environ,
    )


if __name__ == "__main__":
    main()
