# agents/shared — Fleet-Wide Shared Utilities

Python helpers available to **every agent** in HyperCode V2.4.
Import from here instead of duplicating code across agents.

---

## 📣 HyperAlert — Discord Alerts from Any Agent

### Setup (one-time)

Add to your `.env`:
```bash
# General fleet alerts (all agents — separate channel recommended)
DISCORD_ALERTS_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN

# Healer-specific OOM / crash-loop alerts (already set up)
DISCORD_OOM_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN
```

Tip: use **different webhooks** so OOM alerts and general amber alerts go to different Discord channels. Keeps noise separate.

---

### Usage

```python
from shared.hyper_alert import HyperAlert

# One-liner pre-built helpers
await HyperAlert.disk_warning("coder-agent", "/data", 92.5)   # 🟡 Amber
await HyperAlert.api_quota("broski-bot", "OpenAI", 88.0)      # 🟡 Amber
await HyperAlert.cert_expiry("hyperfocuszone.com", 12)         # 🟡 Amber / 🔴 Red
await HyperAlert.agent_started("coder-agent", "v2.4.1")        # 🟢 Green
await HyperAlert.agent_recovered("coder-agent", "OOM kill")    # 🟢 Green

# Custom alert — full control
await HyperAlert.warn(
    title="Rate Limit Hit",
    description="`broski-bot` hit the Discord API rate limit. Backing off for 60s.",
    fields=[
        {"name": "Agent", "value": "`broski-bot`", "inline": True},
        {"name": "Retry In", "value": "60s", "inline": True},
    ],
    agent_name="broski-bot",
)

# Fire-and-forget (non-blocking inside sync code)
asyncio.create_task(HyperAlert.error("Something broke", "Details here..."))
```

### Alert levels

| Method | Colour | When to use |
|--------|--------|-------------|
| `HyperAlert.info()` | 🔵 Blue | Informational, no action needed |
| `HyperAlert.warn()` | 🟡 Amber | Needs attention soon |
| `HyperAlert.error()` | 🔴 Red | Broken / needs immediate action |
| `HyperAlert.success()` | 🟢 Green | Milestone / recovery / good news |

### Secrets safety

- `DISCORD_ALERTS_WEBHOOK_URL` is read **once at import time** and stored in a private module variable.
- It is **never logged, printed, echoed, or returned** anywhere.
- If the env var is missing, alerts are **silently skipped** with a log warning only — no crashes.
