"""Application settings loaded from environment / .env.

Only the values needed to boot the Phase 1 infrastructure are declared as
required. Integration secrets (PayPro, Apify, S3, SMTP) are intentionally
optional here and validated in their own integration modules in later phases,
so the app can start before those credentials exist. `extra="ignore"` lets the
full .env (CLAUDE.md §5) carry keys this model doesn't yet declare.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    APP_NAME: str = "leadkar"
    ENVIRONMENT: str = "production"
    SECRET_KEY: str = ""

    # Database (required to boot)
    DATABASE_URL: str

    # Redis / Celery
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"


settings = Settings()
