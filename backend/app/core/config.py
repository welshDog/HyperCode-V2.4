from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Literal

PrivacyMode = Literal["redact", "none"]

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "HyperCode Core"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # Auth
    API_KEY: Optional[str] = None
    JWT_SECRET: str = "dev-secret-key"
    HYPERCODE_JWT_SECRET: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    JWT_ISSUER: Optional[str] = None
    JWT_AUDIENCE: Optional[str] = None
    ALLOW_PUBLIC_SIGNUP: bool = True
    
    # Database & Redis
    HYPERCODE_DB_URL: str = "postgresql://postgres:postgres@postgres:5432/hypercode"
    HYPERCODE_REDIS_URL: str = "redis://redis:6379/0"

    ORCHESTRATOR_URL: str = "http://crew-orchestrator:8080"
    ORCHESTRATOR_API_KEY: Optional[str] = None
    
    # AI
    PERPLEXITY_API_KEY: Optional[str] = None
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
    PERPLEXITY_SESSION_AUTH: bool = False

    # Brain / memory (privacy defaults)
    # If enabled, Brain.recall_context may read recent files from object storage when RAG is unavailable.
    # Default is False to avoid pulling arbitrary bucket contents into prompts.
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
    MINIO_ENDPOINT: str = "http://minio:9000" # Internal Docker Hostname
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_REPORTS: str = "agent-reports"
    MINIO_SECURE: bool = False # False for local MinIO (http)
    
    # RAG (ChromaDB)
    CHROMA_HOST: str = "chroma"
    CHROMA_PORT: int = 8000
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2" # Fast, local model

    # Telemetry (OpenTelemetry)
    OTLP_ENDPOINT: str = "http://tempo:4317"
    OTLP_EXPORTER_DISABLED: bool = True
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
            if not self.JWT_SECRET or self.JWT_SECRET == "dev-secret-key":
                raise ValueError("JWT_SECRET must be set to a strong value for non-development environments")
            if self.MINIO_ACCESS_KEY == "minioadmin" and self.MINIO_SECRET_KEY == "minioadmin":
                raise ValueError("MinIO credentials must be set to non-default values for non-development environments")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Allow extra fields in env
    )

settings = Settings()

from functools import lru_cache

@lru_cache()
def get_settings() -> Settings:
    return Settings()
