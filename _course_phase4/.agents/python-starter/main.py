from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="python-starter")


class EchoRequest(BaseModel):
    text: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/tools/echo_text")
async def echo_text(payload: EchoRequest):
    return {"text": payload.text}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3100)
