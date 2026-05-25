"""
Agent Training API — Backend for Trae IDE agent communication
Enables bidirectional chat, training data exchange, skill sharing
"""

from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import httpx
import logging
import redis
from sqlalchemy import create_engine, Column, String, JSON, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Training API", version="1.0")

# Database
DATABASE_URL = "postgresql://skills:skills-secure@skill-repository:5432/skill_store"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Redis for session management
redis_client = redis.Redis(host="redis", port=6379, db=1, decode_responses=True)

# ─────────────────────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────────────────────

class AgentMessage(BaseModel):
    """Message to send to agent."""
    agent_name: str
    message: str
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None

class TrainingData(BaseModel):
    """Training data for agent skill development."""
    agent_name: str
    skill: str
    examples: List[Dict[str, str]]
    metadata: Optional[Dict[str, Any]] = None

class TrainingSession(Base):
    """Training session record."""
    __tablename__ = "training_sessions"
    
    session_id = Column(String, primary_key=True)
    agent_name = Column(String)
    messages = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class AgentSkill(Base):
    """Agent trained skill."""
    __tablename__ = "agent_skills"
    
    skill_id = Column(String, primary_key=True)
    agent_name = Column(String)
    skill_name = Column(String)
    training_data = Column(JSON)
    performance_metrics = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# ─────────────────────────────────────────────────────────────────────────────
# DOCKER AGENT CLIENTS
# ─────────────────────────────────────────────────────────────────────────────

AGENT_PORTS = {
    "frontend-specialist": 8012,
    "backend-specialist": 8003,
    "database-architect": 8004,
    "qa-engineer": 8005,
    "devops-engineer": 8006,
    "coder-agent": 8002,
    "crew-orchestrator": 8080,
    "healer-agent": 8008,
}

async def get_agent_client(agent_name: str) -> Optional[httpx.AsyncClient]:
    """Get HTTP client for Docker agent."""
    if agent_name not in AGENT_PORTS:
        return None
    
    port = AGENT_PORTS[agent_name]
    return httpx.AsyncClient(base_url=f"http://localhost:{port}")

async def send_to_agent(agent_name: str, message: str, context: Optional[Dict] = None) -> Dict:
    """Send message to running Docker agent."""
    client = await get_agent_client(agent_name)
    
    if not client:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    try:
        payload = {
            "message": message,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = await client.post("/chat", json=payload, timeout=60)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Agent returned {response.status_code}"}
    
    except Exception as e:
        logger.error(f"Error communicating with {agent_name}: {e}")
        raise HTTPException(status_code=503, detail=f"Agent communication error: {str(e)}")
    
    finally:
        await client.aclose()

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS — Trae IDE API
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/agents")
async def list_agents():
    """List all available agents and their capabilities."""
    agents = []
    
    for agent_name, port in AGENT_PORTS.items():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:{port}/health", timeout=5)
                if response.status_code == 200:
                    agents.append({
                        "name": agent_name,
                        "port": port,
                        "status": "online",
                        "url": f"http://localhost:{port}"
                    })
        except:
            agents.append({
                "name": agent_name,
                "port": port,
                "status": "offline"
            })
    
    return {"agents": agents, "count": len(agents)}

@app.post("/chat")
async def chat_with_agent(msg: AgentMessage):
    """Send message to agent and get response."""
    
    # Send to agent
    response = await send_to_agent(msg.agent_name, msg.message, msg.context)
    
    # Log conversation
    session_id = msg.session_id or datetime.utcnow().isoformat()
    redis_client.hset(f"chat:{session_id}", mapping={
        "user_message": msg.message,
        "agent_response": json.dumps(response),
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {
        "session_id": session_id,
        "agent": msg.agent_name,
        "user_message": msg.message,
        "agent_response": response,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/train")
async def train_agent(training: TrainingData):
    """Train agent with new skill/examples."""
    
    # Send training data to agent
    training_payload = {
        "action": "train",
        "skill": training.skill,
        "examples": training.examples,
        "metadata": training.metadata or {}
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:{AGENT_PORTS[training.agent_name]}/train",
                json=training_payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Store skill in repository
                skill_id = f"{training.agent_name}_{training.skill}_{datetime.utcnow().timestamp()}"
                db = SessionLocal()
                skill_record = AgentSkill(
                    skill_id=skill_id,
                    agent_name=training.agent_name,
                    skill_name=training.skill,
                    training_data=training.dict(),
                    performance_metrics=result.get("metrics", {})
                )
                db.add(skill_record)
                db.commit()
                
                return {
                    "skill_id": skill_id,
                    "agent": training.agent_name,
                    "skill": training.skill,
                    "status": "trained",
                    "result": result
                }
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@app.get("/skills/{agent_name}")
async def get_agent_skills(agent_name: str):
    """Get all trained skills for an agent."""
    db = SessionLocal()
    skills = db.query(AgentSkill).filter_by(agent_name=agent_name).all()
    
    return {
        "agent": agent_name,
        "skills": [
            {
                "skill_id": s.skill_id,
                "skill_name": s.skill_name,
                "created_at": s.created_at.isoformat(),
                "performance": s.performance_metrics
            }
            for s in skills
        ]
    }

@app.get("/sessions/{session_id}")
async def get_session_history(session_id: str):
    """Get conversation history for a session."""
    history = redis_client.hgetall(f"chat:{session_id}")
    return {"session_id": session_id, "history": history}

@app.websocket("/ws/agent/{agent_name}")
async def websocket_agent_chat(websocket: WebSocket, agent_name: str):
    """WebSocket for real-time agent interaction."""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Send to agent
            response = await send_to_agent(agent_name, data)
            
            # Send response back via WebSocket
            await websocket.send_json({
                "agent": agent_name,
                "response": response,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

@app.post("/multi-agent-request")
async def multi_agent_request(agents: List[str], message: str):
    """Send message to multiple agents in parallel."""
    import asyncio
    
    tasks = [send_to_agent(agent, message) for agent in agents if agent in AGENT_PORTS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return {
        "message": message,
        "agents_queried": agents,
        "responses": {
            agent: (result if not isinstance(result, Exception) else {"error": str(result)})
            for agent, result in zip(agents, results)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
