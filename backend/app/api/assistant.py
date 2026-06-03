"""Conversational quoting endpoints (Phase 9 §15.9).

`/assistant/chat` runs the Groq chat + server-side quote; `/assistant/quote/{id}/
accept` turns a locked quote into an order + PayPro invoice. The assistant is
enhancement-only: if Groq isn't configured the chat returns `enabled=false` and
the frontend falls back to the plain form (§15.2 guardrail #3).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_groq_client, get_paypro_client
from app.api.orders import _upsert_customer
from app.config import settings
from app.db import get_session
from app.integrations.llm import GroqClient, GroqError
from app.integrations.paypro import PayProClient, PayProError
from app.models.order import Order, OrderStatus, OrderType
from app.models.pack import Pack
from app.models.quote import Quote
from app.schemas.assistant import (
    AcceptQuoteRequest,
    ChatRequest,
    ChatResponse,
    QuoteOut,
)
from app.schemas.order import OrderCreateResponse
from app.services.quoting import build_quote

router = APIRouter()


def _prettify(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.replace("_", " ").split())


async def _quote_out(session: AsyncSession, quote: Quote) -> QuoteOut:
    if quote.kind == "catalog" and quote.pack_id:
        pack = await session.get(Pack, quote.pack_id)
        title = pack.title if pack else _prettify(quote.vertical or "leads")
    else:
        title = f"{_prettify(quote.vertical or 'leads')} in {quote.city or ''}".strip()
    rows = (quote.preview or {}).get("rows", []) if isinstance(quote.preview, dict) else []
    return QuoteOut(
        quote_id=quote.id,
        kind=quote.kind,  # type: ignore[arg-type]
        title=title,
        price_pkr=quote.price_pkr,
        guaranteed_min=quote.guaranteed_min,
        likely_low=quote.likely_low,
        likely_high=quote.likely_high,
        preview_rows=rows,
    )


@router.get("/assistant/status")
async def status(groq: GroqClient = Depends(get_groq_client)) -> dict[str, bool]:
    """Cheap probe so the frontend can pick chat-vs-form without a Groq call."""
    return {"enabled": groq.is_configured}


@router.post("/assistant/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    session: AsyncSession = Depends(get_session),
    groq: GroqClient = Depends(get_groq_client),
) -> ChatResponse:
    if not groq.is_configured:
        return ChatResponse(enabled=False, reply="", quote=None)

    history = [{"role": m.role, "content": m.content} for m in payload.messages]
    try:
        intent = await groq.chat(history)
    except GroqError:
        # Transient Groq failure — stay graceful, nudge to the form.
        return ChatResponse(
            enabled=True,
            reply="Sorry, I'm having a hiccup. You can use the quick form below and "
            "we'll get you a quote right away.",
            quote=None,
        )

    quote_out: QuoteOut | None = None
    if intent.ready and intent.city and intent.vertical:
        quote = await build_quote(
            session,
            city=intent.city,
            vertical_text=intent.vertical,
            count_wanted=intent.count_wanted,
        )
        await session.commit()
        quote_out = await _quote_out(session, quote)

    return ChatResponse(enabled=True, reply=intent.reply, quote=quote_out)


@router.post("/assistant/quote/{quote_id}/accept", response_model=OrderCreateResponse)
async def accept_quote(
    quote_id: uuid.UUID,
    payload: AcceptQuoteRequest,
    session: AsyncSession = Depends(get_session),
    paypro: PayProClient = Depends(get_paypro_client),
) -> OrderCreateResponse:
    quote = await session.get(Quote, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="quote not found")

    # Idempotent accept: a repeat with the same key returns the original order.
    if payload.idempotency_key:
        existing = await session.scalar(
            select(Order).where(Order.idempotency_key == payload.idempotency_key)
        )
        if existing is not None:
            return OrderCreateResponse(
                order_id=existing.id,
                payment_url=existing.paypro_invoice_url or "",
                status=existing.status.value,
            )

    if quote.status != "open":
        raise HTTPException(status_code=409, detail="quote already used")
    if quote.expires_at < datetime.now(timezone.utc):
        quote.status = "expired"
        await session.commit()
        raise HTTPException(status_code=410, detail="quote expired")

    cust = await _upsert_customer(session, payload.customer)

    # Price and counts come ONLY from the locked quote — never the client (§15.2).
    if quote.kind == "catalog":
        order = Order(
            customer_id=cust.id,
            pack_id=quote.pack_id,
            order_type=OrderType.catalog,
            status=OrderStatus.pending,
            amount_pkr=quote.price_pkr,
            idempotency_key=payload.idempotency_key or str(uuid.uuid4()),
            quote_id=quote.id,
        )
        pack = await session.get(Pack, quote.pack_id) if quote.pack_id else None
        description = pack.title if pack else "LeadKar pack"
    else:
        target = quote.count_wanted or quote.guaranteed_min or 0
        order = Order(
            customer_id=cust.id,
            order_type=OrderType.custom,
            status=OrderStatus.pending,
            amount_pkr=quote.price_pkr,
            idempotency_key=payload.idempotency_key or str(uuid.uuid4()),
            quote_id=quote.id,
            guaranteed_min_leads=quote.guaranteed_min,
            custom_spec={
                "city": quote.city,
                "vertical": quote.vertical,
                "target_count": target,
            },
        )
        description = f"Custom leads: {quote.vertical} in {quote.city} ({target})"

    session.add(order)
    await session.flush()

    try:
        invoice = await paypro.create_invoice(
            order_id=order.id,
            amount_pkr=quote.price_pkr,
            customer_email=cust.email,
            customer_name=cust.name or "Customer",
            customer_phone=cust.phone,
            description=description,
            return_url=settings.PAYPRO_RETURN_URL,
            cancel_url=settings.PAYPRO_CANCEL_URL,
        )
    except PayProError as exc:
        logger.error("PayPro create_invoice failed for quote {}: {}", quote_id, exc)
        raise HTTPException(status_code=502, detail="payment provider error") from exc

    order.paypro_invoice_id = invoice.invoice_id
    order.paypro_invoice_url = invoice.payment_url
    quote.status = "accepted"
    await session.commit()

    return OrderCreateResponse(
        order_id=order.id, payment_url=invoice.payment_url, status=OrderStatus.pending.value
    )
