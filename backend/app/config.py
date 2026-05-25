"""Application settings loaded from environment / .env.

Only the values needed to boot the Phase 1 infrastructure are declared as
required. Integration secrets (PayPro, Apify, S3, SMTP) are intentionally
optional here and validated in their own integration modules in later phases,
so the app can start before those credentials exist. `extra="ignore"` lets the
full .env (CLAUDE.md §5) carry keys this model doesn't yet declare.
"""

from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    APP_NAME: str = "leadkar"
    APP_BASE_URL: str = "https://leadkar.pk"
    ENVIRONMENT: str = "production"
    SECRET_KEY: str = ""

    # Database (required to boot)
    DATABASE_URL: str

    # Redis / Celery
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # PayPro v2 (Pakistan). No webhook signing exists — payment is verified by
    # a server-to-server status query, so there is no webhook secret.
    PAYPRO_CLIENT_ID: str = ""
    PAYPRO_CLIENT_SECRET: str = ""
    PAYPRO_USERNAME: str = ""  # userName for status/ggosboi (login, e.g. Engs_Tech)
    PAYPRO_MERCHANT_ID: str = ""  # MerchantId for create-order (e.g. Engstech_PKR)
    PAYPRO_API_BASE_URL: str = ""  # demo: https://demoapi.paypro.com.pk
    PAYPRO_RETURN_URL: str = ""
    PAYPRO_CANCEL_URL: str = ""
    PAYPRO_TIMEOUT_SECONDS: int = 20
    PAYPRO_TOKEN_TTL_SECONDS: int = 1500  # no documented expiry; refresh-on-401 too
    PAYPRO_ORDER_DUE_DAYS: int = 7

    # Hetzner Object Storage (S3 API)
    S3_ENDPOINT: str = ""
    S3_REGION: str = "fsn1"
    S3_BUCKET: str = "leadkar-deliverables"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_PRESIGNED_URL_TTL_HOURS: int = 72

    # Email (SMTP)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@leadkar.pk"
    SMTP_FROM_NAME: str = "LeadKar"

    # Apify
    APIFY_API_TOKEN: str = ""
    APIFY_ACTOR_GMAPS: str = "compass/crawler-google-places"
    APIFY_MAX_USD_PER_RUN: Decimal = Decimal("10")
    APIFY_DEFAULT_LANGUAGE: str = "en"
    APIFY_TIMEOUT_SECONDS: int = 1800


settings = Settings()
