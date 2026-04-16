import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone


def _env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None or val == "":
        raise SystemExit(f"Missing env var: {name}")
    return val


def _git(args: list[str]) -> str:
    out = subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL)
    return out.decode("utf-8", errors="replace").strip()


def _post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        body = resp.read().decode("utf-8")
        try:
            return json.loads(body)
        except Exception:
            return {"raw": body}


def main() -> None:
    base = _env("PETS_BRIDGE_URL", "http://127.0.0.1:8098").rstrip("/")
    discord_id = _env("PETS_DISCORD_ID")

    sha = _git(["rev-parse", "HEAD"])
    msg = _git(["log", "-1", "--pretty=%B"])
    first = msg.strip().splitlines()[0].strip() if msg.strip() else ""
    is_fix = first.lower().startswith("fix:")

    amount = 25 if is_fix else 10
    reason = f"git commit: {first}" if first else "git commit"

    _post_json(
        f"{base}/xp/award",
        {"discord_id": discord_id, "amount": amount, "reason": reason, "source": "git_hook"},
    )

    streak = _post_json(
        f"{base}/streak/commit",
        {
            "discord_id": discord_id,
            "commit_sha": sha,
            "commit_message": first,
            "committed_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    if bool(streak.get("award_bonus")):
        _post_json(
            f"{base}/xp/award",
            {
                "discord_id": discord_id,
                "amount": 200,
                "reason": "7-day commit streak",
                "source": "streak_tracker",
            },
        )

    sys.stdout.write(json.dumps({"ok": True, "sha": sha, "fix": is_fix, "streak": streak}))


if __name__ == "__main__":
    main()
