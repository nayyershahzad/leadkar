"""Assistant request/response schemas (Phase 9 §15.9)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.order import CustomerIn


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)


class QuoteOut(BaseModel):
    """Authoritative quote shown to the customer — numbers come from the server."""

    quote_id: UUID
    kind: Literal["catalog", "custom"]
    title: str
    price_pkr: int
    guaranteed_min: int | None = None
    likely_low: int | None = None
    likely_high: int | None = None
    preview_rows: list[dict] = []


class ChatResponse(BaseModel):
    enabled: bool
    reply: str
    quote: QuoteOut | None = None


class AcceptQuoteRequest(BaseModel):
    customer: CustomerIn
    idempotency_key: str | None = None
