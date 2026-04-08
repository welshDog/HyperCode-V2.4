import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request


DATA_PATH = Path(os.getenv("ALERT_WEBHOOK_DATA_PATH", "/data/alerts.jsonl"))

app = FastAPI()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/alerts")
async def alerts(request: Request) -> dict:
    payload = await request.json()
    record = {
        "received_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "payload": payload,
    }

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return {"ok": True}
