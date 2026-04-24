import os
from typing import Any, Dict, List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORCHESTRATOR_")

    environment: str = "development"
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
        "coder": "http://coder-agent:8002",
        "coder_agent": "http://coder-agent:8002",
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

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        prefix = "ORCHESTRATOR_"

        def _file_env_settings() -> dict[str, Any]:
            data: dict[str, Any] = {}
            for field_name in settings_cls.model_fields:
                env_name = f"{prefix}{field_name.upper()}_FILE"
                file_path = os.getenv(env_name)
                if not file_path:
                    continue
                try:
                    if os.path.exists(file_path):
                        with open(file_path, "r", encoding="utf-8") as fh:
                            value = fh.read().strip()
                        if value != "":
                            data[field_name] = value
                except OSError:
                    continue
            return data

        return (
            init_settings,
            env_settings,
            _file_env_settings,
            dotenv_settings,
            file_secret_settings,
        )


settings = Settings()
