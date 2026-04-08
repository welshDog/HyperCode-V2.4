from fastapi import FastAPI
from src.api.routes import economy
from src.core.database import db

app = FastAPI(
    title="BROski Bot API",
    version="1.0.0",
    description="API for BROski Bot Economy and Achievements",
)

@app.on_event("startup")
async def startup_event():
    await db.init()

@app.on_event("shutdown")
async def shutdown_event():
    await db.close()

app.include_router(economy.router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
