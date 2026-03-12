from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://wattwise:wattwise_secret@postgres:5432/wattwise"
    DATABASE_URL_SYNC: str = "postgresql://wattwise:wattwise_secret@postgres:5432/wattwise"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # API
    SECRET_KEY: str = "change-me-in-production"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:80"

    # Tariff rates
    PEAK_RATE: float = 0.28
    OFF_PEAK_RATE: float = 0.12
    STANDARD_RATE: float = 0.18

    # Streamer
    STREAM_INTERVAL_SECONDS: int = 5
    STREAM_HOME_ID: int = 1
    STREAM_ERROR_RATE: float = 0.05

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
