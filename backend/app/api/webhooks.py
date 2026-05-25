"""PayPro callback endpoint (CLAUDE.md §7, adapted for PayPro Pakistan).

PayPro PK does not sign callbacks, so we trust nothing in the request body: the
callback is only a trigger to re-query PayPro's status API (ggosboi). An order is
marked paid ONLY when PayPro itself reports OrderStatus=PAID (Nayyer's decision,
2026-05-25). The 15-minute reconciliation task is the backstop if a callback is
never delivered.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.integrations.paypro import PayProClient, PayProError
from app.models.order import Order, OrderStatus
from app.models.paypro_event import PayProEvent

router = APIRouter()

# Field names PayPro might use to identify the order in a callback. We match our
# OrderNumber (== our order_id) first, then fall back to PayProId.
_ORDER_NUMBER_KEYS = ("OrderNumber", "order_number", "Order_Id", "orderid", "OrderId")
_PAYPRO_ID_KEYS = ("PayProId", "payproid", "cpayId", "cpayid")


@router.post("/webhooks/paypro")
async def paypro_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Response:
    payload = await _parse_body(request)

    # Locate our order from whatever identifier the callback carries.
    order = await _match_order(session, payload)

    event = PayProEvent(
        paypro_event_id=_first(payload, _ORDER_NUMBER_KEYS + _PAYPRO_ID_KEYS),
        event_type="callback",
        payload=payload,
        signature_valid=False,  # set True once verified via PayPro's status API
        processed=False,
    )
    session.add(event)

    if order is None:
        logger.warning("PayPro callback for unrecognized order: {}", payload)
        event.processed = True
        await session.commit()
        return Response(status_code=200)  # ack; reconciliation will catch real ones

    event.order_id = order.id

    # Authoritative check: ask PayPro directly. Never trust the callback body.
    try:
        status = await PayProClient().get_invoice_status(str(order.id))
    except PayProError as exc:
        # PayPro unreachable/auth issue — ack and let reconciliation retry.
        logger.warning("PayPro status check failed for order {}: {}", order.id, exc)
        event.processed = True
        await session.commit()
        return Response(status_code=200)
    event.signature_valid = status.raw != {}  # we reached PayPro and got a result

    if order.status == OrderStatus.pending:
        now = datetime.now(timezone.utc)
        if status.is_paid:
            order.status = OrderStatus.paid
            order.paid_at = now
            # deliver_order is implemented in Phase 4.
            from app.tasks.celery_app import celery_app

            celery_app.send_task("deliver_order", args=[str(order.id)])
        elif status.is_failed:
            order.status = OrderStatus.failed
            order.failed_reason = f"PayPro status: {status.status}"

    event.processed = True
    await session.commit()
    return Response(status_code=200)


async def _parse_body(request: Request) -> dict:
    """PayPro may post JSON or urlencoded; handle both without python-multipart."""
    raw = await request.body()
    ctype = request.headers.get("content-type", "")
    text = (raw or b"").decode("utf-8", "replace")

    if "application/x-www-form-urlencoded" in ctype:
        from urllib.parse import parse_qsl

        return dict(parse_qsl(text))

    # Default to JSON; fall back to urlencoded if it looks like a query string.
    try:
        data = json.loads(text or "{}")
        return data if isinstance(data, dict) else {"_raw": data}
    except (ValueError, TypeError):
        from urllib.parse import parse_qsl

        parsed = dict(parse_qsl(text))
        return parsed or {"_unparseable": text[:2000]}


async def _match_order(session: AsyncSession, payload: dict) -> Order | None:
    order_number = _first(payload, _ORDER_NUMBER_KEYS)
    if order_number:
        order = await session.scalar(
            select(Order).where(Order.id == _as_uuid(order_number))
        )
        if order:
            return order
    paypro_id = _first(payload, _PAYPRO_ID_KEYS)
    if paypro_id:
        return await session.scalar(
            select(Order).where(Order.paypro_invoice_id == str(paypro_id))
        )
    return None


def _first(payload: dict, keys: tuple[str, ...]) -> str | None:
    for k in keys:
        if payload.get(k):
            return str(payload[k])
    return None


def _as_uuid(value: str):
    import uuid

    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return uuid.UUID(int=0)  # non-matching sentinel
