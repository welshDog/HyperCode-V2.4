import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone


def _env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None or val == "":
        raise SystemExit(f"Missing env var: {name}")
    return val


def _git(args: list[str]) -> str:
    out = subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL)
    return out.decode("utf-8", errors="replace").strip()


def _load_dotenv(path: str) -> None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                if not key or key in os.environ:
                    continue
                os.environ[key] = value
    except Exception:
        return


def _post_json(url: str, payload: dict, headers: dict[str, str] | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8")
    merged_headers = {"Content-Type": "application/json"}
    if headers:
        merged_headers.update(headers)
    req = urllib.request.Request(
        url,
        data=data,
        headers=merged_headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        body = resp.read().decode("utf-8")
        try:
            return json.loads(body)
        except Exception:
            return {"raw": body}

def _agent_key_headers() -> dict[str, str]:
    key = (
        os.getenv("HYPERCODE_API_KEY", "").strip()
        or os.getenv("AGENT_API_KEY", "").strip()
        or os.getenv("API_KEY", "").strip()
    )
    if not key:
        return {}
    return {"x-api-key": key}


def main() -> None:
    repo_root = ""
    try:
        repo_root = _git(["rev-parse", "--show-toplevel"])
    except Exception:
        repo_root = ""
    if repo_root:
        _load_dotenv(os.path.join(repo_root, ".env"))

    sha = _git(["rev-parse", "HEAD"])
    msg = _git(["log", "-1", "--pretty=%B"])
    first = msg.strip().splitlines()[0].strip() if msg.strip() else ""

    commit_prefix = first.split(":", 1)[0].strip().lower() if ":" in first else ""
    award_amount = {
        "fix": 25,
        "test": 20,
        "feat": 15,
        "refactor": 10,
        "docs": 5,
        "chore": 5,
    }.get(commit_prefix, 10)
    reason = f"git commit: {first}" if first else "git commit"

    hypercode_base = os.getenv("HYPERCODE_API_URL", "http://127.0.0.1:8000").rstrip("/")
    sync_secret = os.getenv("COURSE_SYNC_SECRET", "").strip()
    discord_id = (
        os.getenv("GIT_DISCORD_ID", "").strip()
        or os.getenv("PETS_DISCORD_ID", "").strip()
        or os.getenv("DISCORD_ID", "").strip()
    )

    awarded_hypercode = False
    if sync_secret and discord_id:
        try:
            res = _post_json(
                f"{hypercode_base}/api/v1/economy/award-from-course",
                {
                    "source_id": f"git_{sha}",
                    "discord_id": discord_id,
                    "tokens": award_amount,
                    "reason": reason,
                },
                headers={"X-Sync-Secret": sync_secret},
            )
            sys.stdout.write(
                json.dumps(
                    {
                        "ok": True,
                        "mode": "hypercode",
                        "sha": sha,
                        "amount": award_amount,
                        "discord_id": discord_id,
                        "result": res,
                    }
                )
            )
            awarded_hypercode = True
        except urllib.error.HTTPError as e:
            if e.code in (409,):
                sys.stdout.write(
                    json.dumps(
                        {
                            "ok": True,
                            "mode": "hypercode",
                            "sha": sha,
                            "amount": 0,
                            "discord_id": discord_id,
                            "result": {"status_code": e.code, "detail": "duplicate"},
                        }
                    )
                )
                awarded_hypercode = True
        except Exception:
            pass

    pets_discord_id = os.getenv("PETS_DISCORD_ID", "").strip()
    pets_bridge_url = os.getenv("PETS_BRIDGE_URL", "").strip().rstrip("/")
    candidates = []
    if pets_bridge_url:
        candidates.append(pets_bridge_url)
    candidates.append("http://127.0.0.1:8098")
    seen = set()
    pets_bridge_candidates = []
    for c in candidates:
        if not c or c in seen:
            continue
        seen.add(c)
        pets_bridge_candidates.append(c)

    if pets_discord_id and pets_bridge_candidates:
        headers = _agent_key_headers()
        for base in pets_bridge_candidates:
            try:
                _post_json(
                    f"{base}/xp/award",
                    {
                        "discord_id": pets_discord_id,
                        "amount": 25 if commit_prefix == "fix" else 10,
                        "reason": reason,
                        "source": "git_hook",
                    },
                    headers=headers,
                )
                streak = _post_json(
                    f"{base}/streak/commit",
                    {
                        "discord_id": pets_discord_id,
                        "commit_sha": sha,
                        "commit_message": first,
                        "committed_at": datetime.now(timezone.utc).isoformat(),
                    },
                    headers=headers,
                )
                if bool(streak.get("award_bonus")):
                    _post_json(
                        f"{base}/xp/award",
                        {
                            "discord_id": pets_discord_id,
                            "amount": 200,
                            "reason": "7-day commit streak",
                            "source": "streak_tracker",
                        },
                        headers=headers,
                    )
                sys.stdout.write(
                    json.dumps(
                        {
                            "ok": True,
                            "mode": "pets-bridge",
                            "sha": sha,
                            "fix": commit_prefix == "fix",
                            "streak": streak,
                            "hypercode_tokens_awarded": awarded_hypercode,
                        }
                    )
                )
                return
            except Exception:
                continue

    sys.stdout.write(
        json.dumps(
            {
                "ok": True,
                "mode": "noop",
                "sha": sha,
                "amount": 0,
                "discord_id": discord_id or None,
                "hypercode_tokens_awarded": awarded_hypercode,
            }
        )
    )


if __name__ == "__main__":
    main()
