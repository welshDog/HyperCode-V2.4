import json
import os
import sys
import urllib.request


def _env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None or val == "":
        raise SystemExit(f"Missing env var: {name}")
    return val


def main() -> None:
    if len(sys.argv) < 4:
        raise SystemExit("usage: award_xp.py <amount> <reason> <source>")

    amount = int(sys.argv[1])
    reason = sys.argv[2]
    source = sys.argv[3]

    base = _env("PETS_BRIDGE_URL", "http://127.0.0.1:8098").rstrip("/")
    discord_id = _env("PETS_DISCORD_ID")

    body = json.dumps(
        {"discord_id": discord_id, "amount": amount, "reason": reason, "source": source}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/xp/award",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read().decode("utf-8")
            sys.stdout.write(data)
    except Exception as e:
        raise SystemExit(str(e))


if __name__ == "__main__":
    main()
