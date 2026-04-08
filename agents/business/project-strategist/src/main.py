"""
Project Strategist Agent — Entry Point
Registered in Orchestrator as: http://project-strategist:8001
"""
import uvicorn
import os
import sys

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import ProjectStrategist
from base_agent import AgentConfig

def create_app():
    config = AgentConfig()
    # Ensure correct identity — overrides any env defaults
    config.name = os.getenv("AGENT_NAME", "project-strategist")
    config.role = os.getenv("AGENT_ROLE", "Project Strategist")
    config.port = int(os.getenv("AGENT_PORT", "8001"))

    agent = ProjectStrategist(config)
    return agent.app  # FastAPI app with /health + /execute already wired

# Expose app for uvicorn
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("AGENT_PORT", "8001"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
