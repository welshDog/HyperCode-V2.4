"""Hyper Auto Assistant - Intelligent Task Router for HyperCode V2.0."""

from __future__ import annotations
import json
import logging
import os
import time
from datetime import datetime
from typing import Any
import httpx
from fastapi import FastAPI
from metrics import init_metrics  # 👈 import

app = FastAPI()
init_metrics(app)  # 👈 auto-exposes /metrics endpoint

from pydantic import BaseModel

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({"timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname, "component": "hyper-auto-assistant",
            "message": record.getMessage()})

logger = logging.getLogger("hyper-auto-assistant")
logger.setLevel(logging.INFO)
h = logging.StreamHandler()
h.setFormatter(JSONFormatter())
logger.addHandler(h)
logger.propagate = False

BROSKI_URL = os.getenv("BROSKI_AGENT_URL", "http://localhost:8015")
START_TIME = time.time()

INTENT_MAP: dict[str, list[str]] = {
    "deploy":    ["deploy","launch","release","ship","go live","publish","prod","moon"],
    "debug":     ["debug","fix","bug","error","broken","crash","exception","issue","problem"],
    "code":      ["code","build","write","create","implement","develop","feature","script"],
    "rest":      ["rest","sleep","recharge","break","pause","chill","relax","recover"],
    "celebrate": ["celebrate","done","finished","complete","win","success","shipped","awesome","nailed"],
}
ULTRA_KEYWORDS = ["urgent","critical","asap","emergency","ultra","immediately"]

class TaskRequest(BaseModel):
    task: str
    context: str = ""
    priority: str = "normal"

class TaskResponse(BaseModel):
    task: str
    detected_intent: str
    routed_to: str
    action_fired: str
    result: str
    vibe: int
    energy: int
    processing_ms: float

def detect_intent(task: str, priority: str) -> tuple[str, bool]:
    task_lower = task.lower()
    is_ultra = priority == "ultra" or any(kw in task_lower for kw in ULTRA_KEYWORDS)
    scores = {intent: sum(1 for kw in kws if kw in task_lower)
              for intent, kws in INTENT_MAP.items()}
    best = max(scores, key=lambda k: scores[k])
    return (best if scores[best] > 0 else "celebrate"), is_ultra

app = FastAPI(title="Hyper Auto Assistant", version="1.0.0")

@app.get("/")
async def root() -> dict[str, Any]:
    return {"agent": "Hyper Auto Assistant", "status": "🦅 ROUTING ENGINE ACTIVE",
            "tip": "POST to /route with a task string!"}

@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "healthy", "uptime_seconds": time.time() - START_TIME,
            "message": "🦅 Ready to route!"}

@app.get("/intents")
async def list_intents() -> dict[str, Any]:
    return {"intents": INTENT_MAP, "ultra_triggers": ULTRA_KEYWORDS}

@app.get("/status")
async def status() -> dict[str, Any]:
    broski_ok = "❌ unreachable"
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            r = await c.get(f"{BROSKI_URL}/health")
            broski_ok = "✅ healthy" if r.status_code == 200 else f"⚠️ {r.status_code}"
    except Exception:
        pass
    uptime = time.time() - START_TIME
    return {"status": "🚀 OPERATIONAL",
            "uptime": f"{int(uptime//3600)}h {int((uptime%3600)//60)}m {int(uptime%60)}s",
            "downstream": {"super-hyper-broski-agent": broski_ok}}

@app.post("/route")
async def route_task(req: TaskRequest) -> TaskResponse:
    start = time.time()
    action, is_ultra = detect_intent(req.task, req.priority)
    logger.info(f"Routing: '{req.task}' -> {action} (ultra={is_ultra})")

    result_data: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            if is_ultra:
                resp = await client.post(f"{BROSKI_URL}/ultra-mode")
                logger.info(f"Ultra-mode: {resp.status_code}")
            r = await client.post(f"{BROSKI_URL}/broski-actions", params={"action_type": action})
            r.raise_for_status()
            result_data = r.json()
        except httpx.RequestError as e:
            logger.error(f"Downstream dead: {e}")
            raise HTTPException(status_code=502, detail="Downstream unavailable")
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Bad JSON: {e}")
            raise HTTPException(status_code=502, detail="Invalid downstream response")

    vibe, energy = 100, 100
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            v = (await c.get(f"{BROSKI_URL}/vibe-check")).json()
            vibe, energy = v.get("current_vibe", 100), v.get("energy_level", 100)
    except Exception:
        pass

    return TaskResponse(task=req.task, detected_intent=action,
        routed_to="super-hyper-broski-agent", action_fired=action,
        result=result_data.get("result", "✅ Routed!"),
        vibe=vibe, energy=energy, processing_ms=round((time.time()-start)*1000, 2))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8016)), log_level="info")
