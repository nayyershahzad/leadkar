"""Order endpoints (Phase 4: catalog orders)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_paypro_client
from app.config import settings
from app.db import get_session
from app.integrations.paypro import PayProClient, PayProError
from app.models.customer import Customer
from app.models.order import Order, OrderStatus, OrderType
from app.models.pack import Pack
from app.schemas.order import CatalogOrderRequest, OrderCreateResponse

router = APIRouter()


@router.post("/orders/catalog", response_model=OrderCreateResponse)
async def create_catalog_order(
    payload: CatalogOrderRequest,
    session: AsyncSession = Depends(get_session),
    paypro: PayProClient = Depends(get_paypro_client),
) -> OrderCreateResponse:
    pack = await session.scalar(
        select(Pack).where(Pack.slug == payload.pack_slug, Pack.is_active.is_(True))
    )
    if pack is None:
        raise HTTPException(status_code=404, detail="pack not found")

    # Idempotent creation: a repeat with the same key returns the original order.
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

    # Upsert customer by email.
    cust = await session.scalar(
        select(Customer).where(Customer.email == payload.customer.email)
    )
    if cust is None:
        cust = Customer(
            email=payload.customer.email,
            name=payload.customer.name,
            phone=payload.customer.phone,
            company=payload.customer.company,
        )
        session.add(cust)
        await session.flush()
    else:
        cust.name = payload.customer.name or cust.name
        cust.phone = payload.customer.phone or cust.phone
        cust.company = payload.customer.company or cust.company

    order = Order(
        customer_id=cust.id,
        pack_id=pack.id,
        order_type=OrderType.catalog,
        status=OrderStatus.pending,
        amount_pkr=pack.price_pkr,
        idempotency_key=payload.idempotency_key or str(uuid.uuid4()),
    )
    session.add(order)
    await session.flush()

    try:
        invoice = await paypro.create_invoice(
            order_id=order.id,
            amount_pkr=pack.price_pkr,
            customer_email=cust.email,
            customer_name=cust.name or "Customer",
            customer_phone=cust.phone,
            description=pack.title,
            return_url=settings.PAYPRO_RETURN_URL,
            cancel_url=settings.PAYPRO_CANCEL_URL,
        )
    except PayProError as exc:
        # Order not committed -> session rolls back on exit; client can retry.
        logger.error("PayPro create_invoice failed for pack {}: {}", pack.slug, exc)
        raise HTTPException(status_code=502, detail="payment provider error") from exc

    order.paypro_invoice_id = invoice.invoice_id
    order.paypro_invoice_url = invoice.payment_url
    await session.commit()

    return OrderCreateResponse(
        order_id=order.id, payment_url=invoice.payment_url, status=OrderStatus.pending.value
    )
