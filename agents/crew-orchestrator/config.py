from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, List, Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORCHESTRATOR_")

    redis_url: str = "redis://redis:6379"
    log_level: str = "INFO"
    api_key: Optional[str] = None
    cors_allow_origins: str = "http://localhost:8088,http://localhost:3000"
    enabled_agents: Optional[str] = None

    # Agent Service URLs (defaults based on docker-compose service names)
    agents: Dict[str, str] = {
        "project_strategist": "http://project-strategist:8001",
        "frontend_specialist": "http://frontend-specialist:8012",
        "backend_specialist": "http://backend-specialist:8003",
        "database_architect": "http://database-architect:8004",
        "qa_engineer": "http://qa-engineer:8005",
        "devops_engineer": "http://devops-engineer:8006",
        "security_engineer": "http://security-engineer:8007",
        "system_architect": "http://system-architect:8008",
        "coder": "http://coder:8000",
        "coder_agent": "http://coder:8000",
        "agent_x": "http://agent-x:8000",
    }

    def parsed_cors_allow_origins(self) -> List[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    def enabled_agent_keys(self) -> List[str]:
        if not self.enabled_agents:
            return list(self.agents.keys())
        enabled: List[str] = []
        for raw in self.enabled_agents.split(","):
            key = raw.strip().lower().replace("-", "_")
            if not key:
                continue
            if key in self.agents:
                enabled.append(key)
        return enabled


settings = Settings()
