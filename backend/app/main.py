"""FastAPI entrypoint (Phase 1: health check only)."""

from fastapi import FastAPI

from app.api import assistant, orders, packs, webhooks
from app.config import settings
from app.utils.logging import configure_logging

configure_logging("backend")

app = FastAPI(title=settings.APP_NAME)

# All API routes are mounted under /api (CLAUDE.md §3/§4).
app.include_router(packs.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
