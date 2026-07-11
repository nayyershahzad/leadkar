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
    LOG_DIR: str = "/app/logs"

    # Quarterly catalog refresh is OFF by default: it spends real Apify credit,
    # so it must be explicitly enabled (Rule #6). Beat still schedules it.
    CATALOG_REFRESH_ENABLED: bool = False

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

    # Object storage (S3-compatible: MinIO now, swappable to Hetzner OS / R2).
    S3_ENDPOINT: str = ""          # internal endpoint for uploads (e.g. http://minio:9000)
    S3_PUBLIC_ENDPOINT: str = ""   # public endpoint for presigned download links
    S3_REGION: str = "us-east-1"
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

    # Custom order pricing (PKR). amount = base + per_lead * target_count.
    # Finalized with Nayyer 2026-05-26: base 4,999 + 8/lead, max 1,000 leads
    # (keeps margin ≥70% at the cap and 1,000 leads = 12,999 = top of the §0 band).
    CUSTOM_ORDER_BASE_PKR: int = 4999
    CUSTOM_ORDER_PER_LEAD_PKR: int = 8
    MAX_LEADS_PER_CUSTOM_ORDER: int = 1000

    # Groq conversational assistant (Phase 9 §15). Enhancement-only: with no
    # GROQ_API_KEY (or ASSISTANT_ENABLED=false) the chat degrades to the plain
    # /custom form + /packs — it must never block a sale (§15.2 guardrail #3).
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_TIMEOUT_SECONDS: int = 20
    ASSISTANT_ENABLED: bool = True

    # Custom guaranteed-minimum quoting (§15.4): the conservative floor we promise
    # when we have no density history, as a fraction of the requested count.
    CUSTOM_GUARANTEE_FRACTION: float = 0.6
    QUOTE_TTL_MINUTES: int = 60

    # Volume catalog pricing (§15.6, confirmed 2026-05-26): low headline price to
    # drive volume. price = max(MIN, round_to_×99(lead_count * PER_LEAD)).
    CATALOG_PKR_PER_LEAD: int = 6
    CATALOG_MIN_PRICE_PKR: int = 1999

    # Apify
    APIFY_API_TOKEN: str = ""
    APIFY_ACTOR_GMAPS: str = "compass/crawler-google-places"
    APIFY_MAX_USD_PER_RUN: Decimal = Decimal("10")
    APIFY_DEFAULT_LANGUAGE: str = "en"
    APIFY_TIMEOUT_SECONDS: int = 1800


settings = Settings()
