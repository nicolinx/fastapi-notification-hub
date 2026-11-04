from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, loaded from environment variables and `.env`.

    Field names map to env vars case-insensitively: `app_env` <- `APP_ENV`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FastAPI Notification Hub"
    app_env: str = "development"

    # Allowed browser origins (CORS). Wide open in dev; restrict in production.
    cors_origins: list[str] = ["*"]

    # Required: no defaults, so the app refuses to start if they are missing.
    # Set them in `.env` (local) or real environment variables (Docker/production).
    database_url: str  # async URL, used by the API
    sync_database_url: str  # sync URL, used by the Celery worker
    redis_url: str


@lru_cache
def get_settings() -> Settings:
    """Return one cached Settings instance (built once, reused everywhere)."""
    return Settings()
