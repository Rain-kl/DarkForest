"""Application configuration with environment variable support."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "DarkForest"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://darkforest:darkforest@localhost:5432/darkforest"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production-use-a-strong-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Admin defaults
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123456"
    ADMIN_EMAIL: str = "admin@darkforest.local"

    # Room defaults
    DEFAULT_ROOM_TIMEOUT_MINUTES: int = 10
    DEFAULT_MESSAGE_RETENTION_HOURS: int = 24

    # Rate limiting defaults
    DEFAULT_MAX_ROOMS_PER_HOUR: int = 5
    DEFAULT_MAX_JOINS_PER_HOUR: int = 10
    DEFAULT_MAX_MESSAGES_PER_MINUTE: int = 30

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": True}


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
