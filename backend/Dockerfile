FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# procps gives pgrep for the worker/beat healthchecks; asyncpg ships wheels so no
# compiler toolchain is needed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for layer caching. Kept in sync with pyproject.toml.
RUN pip install \
    "fastapi" \
    "uvicorn[standard]" \
    "sqlalchemy[asyncio]>=2.0" \
    "asyncpg" \
    "alembic" \
    "celery[redis]>=5.3" \
    "redis" \
    "pydantic-settings" \
    "loguru" \
    "httpx" \
    "apify-client" \
    "openpyxl" \
    "boto3" \
    "email-validator"

# Application code + migration tooling.
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations

# Run as non-root (CLAUDE.md §11).
RUN useradd --create-home --uid 10001 leadkar && chown -R leadkar:leadkar /app
USER leadkar

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
