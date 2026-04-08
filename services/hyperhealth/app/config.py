# Basic config + env loader
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/hypercode"
    REDIS_URL: str = "redis://redis:6379"
    HEALER_URL: str = "http://healer-agent:8008"
    
settings = Settings()
