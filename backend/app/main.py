"""FastAPI entrypoint (Phase 1: health check only)."""

from fastapi import FastAPI

from app.api import webhooks
from app.config import settings

app = FastAPI(title=settings.APP_NAME)

# Mounted under /api so the route is /api/webhooks/paypro (CLAUDE.md §7).
app.include_router(webhooks.router, prefix="/api")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
