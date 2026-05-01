"""
Government Scheme Eligibility API - Configuration

Loads environment variables using pydantic-settings for type-safe config.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://schemes_user:schemes_pass@db:5432/schemes_db"

    # Cache
    # memory://local keeps the API runnable with only PostgreSQL.
    # A redis:// URL can still be used later if you want an external cache.
    REDIS_URL: str = "memory://local"

    # JWT
    SECRET_KEY: str = ""
    PRIVATE_API_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # App
    ENVIRONMENT: str = "development"
    APP_NAME: str = "Government Scheme Eligibility API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    SQL_ECHO: bool = False

    # Seed/admin bootstrap values. Keep real values in .env, not README.
    ADMIN_EMAIL: str = "admin@example.local"
    ADMIN_PASSWORD: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
