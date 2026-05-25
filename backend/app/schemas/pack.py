"""Pack request/response schemas (Phase 4)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    title: str
    city: str
    vertical: str
    lead_count: int
    price_pkr: int
    description: str | None = None
    sample_preview: dict | None = None
    last_refreshed_at: datetime | None = None
