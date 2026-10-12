"""PROOF-ONLY stand-in for crew-orchestrator. Answers /execute like a healthy specialist would, so the
crew flow can be proved end to end without LLM agents. Counts calls in $STUB_COUNT_FILE.
Run with:  uvicorn crew_proof_stub_orchestrator:app --app-dir scripts
"""

import os

from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/execute")
async def execute(request: Request) -> dict:
    body = await request.json()
    agent, kind = body.get("agent", "agent"), body.get("type", "")
    path = os.environ.get("STUB_COUNT_FILE")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{kind}\n")
    if kind == "crew_verify":
        text = "The proposal is small and matches the goal.\nVERDICT: PASS"
    else:
        text = "```diff\n+def health():\n+    return {'ok': True}\n```\nAdds a health route."
    return {"status": "completed", "results": {agent: {"result": text}}}
