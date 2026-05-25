"""Order request/response schemas (Phase 4)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr


class CustomerIn(BaseModel):
    email: EmailStr
    name: str
    phone: str | None = None
    company: str | None = None


class CatalogOrderRequest(BaseModel):
    pack_slug: str
    customer: CustomerIn
    # Optional client-supplied key for idempotent order creation (CLAUDE.md Rule #7).
    idempotency_key: str | None = None


class OrderCreateResponse(BaseModel):
    order_id: UUID
    payment_url: str
    status: str
