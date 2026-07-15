import os
from functools import lru_cache
from typing import Any, Optional, List, Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource

PrivacyMode = Literal["redact", "none"]

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "HyperCode Core"
    VERSION: str = "2.4.2"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # Auth
    API_KEY: Optional[str] = None
    BOT_API_KEY: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("BOT_API_KEY", "HYPERCODE_BOT_API_KEY"),
    )
    JWT_SECRET: str = "dev-secret-key"
    HYPERCODE_JWT_SECRET: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    JWT_ISSUER: Optional[str] = None
    JWT_AUDIENCE: Optional[str] = None
    ALLOW_PUBLIC_SIGNUP: bool = True
    
    # Database & Redis
    HYPERCODE_DB_URL: str = "postgresql://postgres:postgres@postgres:5432/hypercode"
    HYPERCODE_REDIS_URL: str = "redis://redis:6379/0"

    # DB connection pool — read by app.db.session for both sync and async engines
    DB_POOL_SIZE: int = 5
    DB_POOL_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE_TIMEOUT: int = 3600

    ORCHESTRATOR_URL: str = "http://crew-orchestrator:8080"
    ORCHESTRATOR_API_KEY: Optional[str] = None
    DOCKER_SOCKET_PROXY_URL: str = "http://docker-socket-proxy:2375"

    # Phase 2: Token Sync — shared secret between Supabase edge fn and this API
    COURSE_SYNC_SECRET: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("COURSE_SYNC_SECRET", "COURSE_WEBHOOK_SECRET"),
    )

    # Phase 3: Agent Access + Shop Bridge
    SHOP_SYNC_SECRET: Optional[str] = None          # shared secret for provision-access edge fn
    DISCORD_BOT_TOKEN: Optional[str] = None         # bot token — used to send DMs via HTTP API
    MISSION_CONTROL_URL: str = "http://localhost:8088"  # URL sent to students in DM
    
    # AI
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    HYPERCODE_MEMORY_KEY: Optional[str] = None
    OLLAMA_HOST: str = "http://hypercode-ollama:11434"
    DEFAULT_LLM_MODEL: str = "auto"
    OLLAMA_MODEL_PREFERRED: str = "tinyllama:latest,tinyllama,phi3:latest,phi3"
    OLLAMA_MAX_MODEL_SIZE_MB: int = 2500
    OLLAMA_MODEL_REFRESH_SECONDS: int = 300
    OLLAMA_TEMPERATURE: float = 0.3
    OLLAMA_TOP_P: float = 0.9
    OLLAMA_TOP_K: int = 40
    OLLAMA_REPEAT_PENALTY: float = 1.1
    OLLAMA_NUM_CTX: int = 2048
    OLLAMA_NUM_PREDICT: int = 256
    OLLAMA_SEED: Optional[int] = None
    PETS_BRIDGE_URL: str = "http://broski-pets-bridge:8098"

    NEMOCLAW_URL: str = "http://nemoclaw-agent:8099"
    NEMOCLAW_TIMEOUT_SECONDS: float = 90.0

    FOCUS_MIN_MINUTES: int = 5

    # Layer 3 Voice — auto-post a code-health pulse only when the grade changes
    # or the score moves by at least this many points.
    CODE_HEALTH_PULSE_THRESHOLD: int = 5

    # Server Guardian Phase 3a — reversible auto-mod only (never ban/kick here).
    MOD_DEFAULT_TIMEOUT_SECONDS: int = 600

    # Server Guardian Phase 3b — raid auto-lockdown (reversible).
    RAID_LOCKDOWN_MINUTES: int = 10

    # Server Guardian Phase 3c — veto-gated ban (SPEC LOCKED, binding).
    # SAFETY INVARIANT: a ban NEVER happens except on explicit APPROVE click.
    # Silence / window-expiry = downgrade to a long timeout, never a ban.
    GUARDIAN_ESCALATION_STRIKES: int = 3
    GUARDIAN_ESCALATION_WINDOW_DAYS: int = 7
    GUARDIAN_VETO_WINDOW_MINUTES: int = 60
    GUARDIAN_DOWNGRADE_TIMEOUT_SECONDS: int = 604800  # 7 days, reversible

    # Brain / memory (privacy defaults)
    BRAIN_ALLOW_FILE_FALLBACK: bool = False

    HUNTER_ALPHA_ENABLED: bool = False
    HUNTER_ALPHA_MODEL: str = "openrouter/openrouter/hunter-alpha"
    HUNTER_ALPHA_BASE_URL: str = "https://openrouter.ai/api/v1"
    HUNTER_ALPHA_ROUTE_TAG: str = "meta-architect"
    HUNTER_ALPHA_MAX_TOKENS: int = 16000
    HUNTER_ALPHA_PRIVACY_MODE: PrivacyMode = "redact"

    HEALER_ALPHA_ENABLED: bool = False
    HEALER_ALPHA_MODEL: str = "openrouter/openrouter/healer-alpha"
    HEALER_ALPHA_BASE_URL: str = "https://openrouter.ai/api/v1"
    HEALER_ALPHA_ROUTE_TAG: str = "incident-healing"
    HEALER_ALPHA_MAX_TOKENS: int = 12000
    HEALER_ALPHA_PRIVACY_MODE: PrivacyMode = "redact"

    def ollama_generate_options(self) -> dict:
        options: dict = {
            "temperature": self.OLLAMA_TEMPERATURE,
            "top_p": self.OLLAMA_TOP_P,
            "top_k": self.OLLAMA_TOP_K,
            "repeat_penalty": self.OLLAMA_REPEAT_PENALTY,
            "num_ctx": self.OLLAMA_NUM_CTX,
            "num_predict": self.OLLAMA_NUM_PREDICT,
        }
        if self.OLLAMA_SEED is not None:
            options["seed"] = self.OLLAMA_SEED
        return options

    # Storage (MinIO/S3)
    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_REPORTS: str = "agent-reports"
    MINIO_SECURE: bool = False
    
    # RAG (ChromaDB)
    CHROMA_HOST: str = "chroma"
    CHROMA_PORT: int = 8000
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Telemetry (OpenTelemetry)
    OTLP_ENDPOINT: str = "http://tempo:4317"
    OTLP_EXPORTER_DISABLED: bool = False
    SERVICE_NAME: str = "hypercode-core"

    # HTTP security
    CORS_ALLOW_ORIGINS: str = "http://localhost:8088,http://127.0.0.1:8088,http://localhost:3000,http://127.0.0.1:3000"
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_MAX_REQUESTS: int = 120
    HYPERSYNC_MASTER_KEY: Optional[str] = None
    HYPERSYNC_INLINE_MAX_BYTES: int = 32768
    HYPERSYNC_TOKEN_TTL_SECONDS: int = 900
    HYPERSYNC_SESSION_TTL_SECONDS: int = 3600

    def parsed_cors_allow_origins(self) -> List[str]:
        return [o.strip() for o in self.CORS_ALLOW_ORIGINS.split(",") if o.strip()]

    def validate_security(self) -> None:
        if self.ENVIRONMENT.lower() in {"production", "staging"}:
            if self.HYPERCODE_JWT_SECRET and self.JWT_SECRET == "dev-secret-key":
                self.JWT_SECRET = self.HYPERCODE_JWT_SECRET

            if not self.JWT_SECRET or self.JWT_SECRET == "dev-secret-key":
                raise ValueError("JWT_SECRET must be set to a strong value for non-development environments")

            minio_endpoint_overridden = bool(os.getenv("MINIO_ENDPOINT")) or self.MINIO_ENDPOINT != "http://minio:9000"
            if minio_endpoint_overridden:
                if self.MINIO_ACCESS_KEY == "minioadmin" and self.MINIO_SECRET_KEY == "minioadmin":
                    raise ValueError("MinIO credentials must be set to non-default values for non-development environments")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        def _file_env_settings() -> dict[str, Any]:
            data: dict[str, Any] = {}
            for field_name in settings_cls.model_fields:
                file_path = os.getenv(f"{field_name}_FILE")
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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        env_ignore_empty=True,
        extra="ignore"
    )
_settings_boot_error: str | None = None
try:
    settings = Settings()
except Exception as exc:
    _settings_boot_error = str(exc)
    settings = Settings.model_validate({})

@lru_cache()
def get_settings() -> Settings:
    return settings

def get_settings_boot_error() -> str | None:
    return _settings_boot_error
