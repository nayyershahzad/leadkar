"""FastAPI entrypoint (Phase 1: health check only)."""

from fastapi import FastAPI

from app.config import settings

app = FastAPI(title=settings.APP_NAME)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
