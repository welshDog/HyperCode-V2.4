"""
Application configuration using Pydantic Settings.
Loads settings from environment variables with validation.
"""
from functools import lru_cache
from typing import Any, Dict, Optional

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="BROski-Bot", description="Application name")
    app_version: str = Field(default="4.0.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development/staging/production)")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Discord
    discord_token: str = Field(..., description="Discord bot token")
    discord_command_prefix: str = Field(default="/", description="Command prefix")
    discord_intents_all: bool = Field(default=False, description="Enable all intents")
    discord_owner_ids: list[int] = Field(default_factory=list, description="Bot owner user IDs")
    
    # Database
    database_url: PostgresDsn = Field(..., description="PostgreSQL connection URL")
    database_pool_size: int = Field(default=20, description="Database connection pool size")
    database_max_overflow: int = Field(default=10, description="Max overflow connections")
    database_pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    database_echo: bool = Field(default=False, description="Echo SQL queries")
    
    # Redis Cache
    redis_url: RedisDsn = Field(..., description="Redis connection URL")
    redis_max_connections: int = Field(default=50, description="Redis max connections")
    redis_socket_timeout: int = Field(default=5, description="Redis socket timeout")
    cache_ttl: int = Field(default=300, description="Default cache TTL in seconds")
    
    # Economy System
    economy_daily_reward: int = Field(default=100, description="Daily reward tokens")
    economy_daily_streak_bonus: int = Field(default=50, description="Streak bonus tokens per day")
    economy_max_streak_days: int = Field(default=30, description="Max streak days for bonus")
    economy_starting_balance: int = Field(default=500, description="New user starting balance")
    
    # Focus System
    focus_base_reward: int = Field(default=200, description="Base focus session reward")
    focus_hyperfocus_threshold: int = Field(default=25, description="Hyperfocus minutes threshold")
    focus_hyperfocus_multiplier: float = Field(default=1.5, description="Hyperfocus reward multiplier")
    focus_max_session_minutes: int = Field(default=180, description="Max focus session length")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_user: int = Field(default=10, description="Commands per user per minute")
    rate_limit_per_guild: int = Field(default=100, description="Commands per guild per minute")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json/console)")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    sentry_environment: str = Field(default="development", description="Sentry environment")
    sentry_traces_sample_rate: float = Field(default=0.1, description="Sentry traces sample rate")
    
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    prometheus_port: int = Field(default=8000, description="Prometheus metrics port")
    
    # Security
    allowed_origins: list[str] = Field(default_factory=list, description="CORS allowed origins")
    secret_key: str = Field(..., description="Secret key for encryption")
    
    # Backup
    backup_enabled: bool = Field(default=True, description="Enable automatic backups")
    backup_interval_hours: int = Field(default=6, description="Backup interval in hours")
    backup_retention_days: int = Field(default=30, description="Backup retention period")
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v_upper
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration dictionary."""
        return {
            "pool_size": self.database_pool_size,
            "max_overflow": self.database_max_overflow,
            "pool_timeout": self.database_pool_timeout,
            "echo": self.database_echo,
        }


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: Application settings
    """
    return Settings()


# Global settings instance
settings = get_settings()
