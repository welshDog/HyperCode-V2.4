from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Literal
from uuid import UUID
import asyncio
import os
from sqlalchemy import create_engine, Column, String, Integer, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hyperhealth.db")
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database model
class CheckDefinitionDB(Base):
    __tablename__ = "checks"
    id = Column(String, primary_key=True)
    name = Column(String, index=True)
    type = Column(String)
    target = Column(String)
    environment = Column(String)
    interval_seconds = Column(Integer)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="HyperHealth v1.0", version="1.0.0")

CheckType = Literal["cpu","memory","disk","http","db","queue","cache","tls","vuln_scan","compliance"]

class Thresholds(BaseModel):
    warn: float
    crit: float
    window_minutes: int

class CheckDefinitionCreate(BaseModel):
    name: str
    type: CheckType
    target: str
    environment: str
    interval_seconds: int
    thresholds: Dict[str, Thresholds]

class CheckDefinitionOut(BaseModel):
    id: str
    name: str
    type: CheckType
    target: str
    environment: str
    interval_seconds: int

    class Config:
        from_attributes = True

def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/checks", response_model=List[CheckDefinitionOut])
async def list_checks(db: Session = Depends(get_db)):
    """List all check definitions from persistent storage."""
    checks = db.query(CheckDefinitionDB).all()
    return checks

@app.post("/checks", response_model=CheckDefinitionOut)
async def create_check(check: CheckDefinitionCreate, db: Session = Depends(get_db)):
    """Create a new check definition and persist it."""
    check_id = str(UUID(int=int.from_bytes(os.urandom(16), 'big')))
    db_check = CheckDefinitionDB(
        id=check_id,
        name=check.name,
        type=check.type,
        target=check.target,
        environment=check.environment,
        interval_seconds=check.interval_seconds,
    )
    db.add(db_check)
    db.commit()
    db.refresh(db_check)
    return db_check

@app.get("/health/report")
async def get_health_report(env: str = "prod", db: Session = Depends(get_db)):
    """Get aggregated health report for an environment."""
    checks = db.query(CheckDefinitionDB).filter(CheckDefinitionDB.environment == env).all()
    return {
        "environment": env,
        "overall_status": "UNKNOWN",  # TODO: aggregate real check results
        "checks_total": len(checks),
        "incidents_open": 0,  # TODO: query from incident storage
        "self_heals_today": 0,  # TODO: query from audit log
        "timestamp": "2026-03-26T19:35:00Z"
    }

@app.get("/metrics")
async def metrics(db: Session = Depends(get_db)):
    """Prometheus metrics endpoint."""
    checks_total = db.query(CheckDefinitionDB).count()
    return f"""# HELP hyperhealth_up HyperHealth API status
# TYPE hyperhealth_up gauge
hyperhealth_up 1
hyperhealth_checks_total {checks_total}
hyperhealth_incidents_open 0
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
