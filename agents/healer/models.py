from pydantic import BaseModel
from typing import Optional

class ContainerStatus(BaseModel):
    name: str
    status: str  # running, exited, dead, etc.
    health: str  # healthy, unhealthy, starting, none
    started_at: Optional[str] = None
    restart_count: int = 0

class HealResult(BaseModel):
    agent: str
    status: str
    action: str
    details: Optional[str] = None
    timestamp: str

class HealRequest(BaseModel):
    agent_name: str
    agent_url: str
    attempts: int = 3
    timeout: float = 10.0

class HealerException(Exception):
    def __init__(self, message: str, agent: str, status: str, details: str):
        super().__init__(message)
        self.agent = agent
        self.status = status
        self.details = details
