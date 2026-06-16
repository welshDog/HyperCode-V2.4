import requests
import random
from datetime import datetime

BRAIN_API = "http://localhost:8100"
XP_ENDPOINT = f"{BRAIN_API}/economy/earn"

# XP tiers — random within range keeps it exciting!
XP_REWARDS = {
    "task_complete": (15, 35),
    "bonus_streak": (10, 20),
}

def award_xp():
    base_xp = random.randint(*XP_REWARDS["task_complete"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    payload = {
        "source": "trae_hook",
        "event": "agent_task_complete",
        "xp": base_xp,
        "timestamp": now,
        "note": "Auto-awarded by TRAE PostToolUse hook"
    }

    try:
        response = requests.post(XP_ENDPOINT, json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            total = data.get("total_broski_coins", "?")
            print(f"\n🪙 +{base_xp} BROski$ earned! — Task complete")
            print(f"💰 Total balance: {total} BROski$")
            print(f"⚡ Keep building Bro! HyperFocus Z0ne — {now}")
        else:
            print(f"⚠️  Brain API responded {response.status_code} — XP not recorded")
    except requests.exceptions.ConnectionError:
        # Brain container might be off — log locally instead
        print(f"\n🪙 +{base_xp} BROski$ earned (offline mode — Brain container not running)")
        _log_offline(base_xp, now)

def _log_offline(xp, timestamp):
    """Fallback: log to local file if Brain API is down."""
    with open(".broski_xp_log.txt", "a") as f:
        f.write(f"{timestamp} | +{xp} XP | agent_task_complete | pending sync\n")
    print("💾 XP logged offline — will sync when Brain container is up.")

award_xp()
