"""PayPro webhook endpoint (CLAUDE.md §7 webhook handler flow)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.integrations.paypro import (
    PayProClient,
    classify_status,
    extract_webhook_fields,
)
from app.models.order import Order, OrderStatus
from app.models.paypro_event import PayProEvent
from app.tasks.celery_app import celery_app

router = APIRouter()


@router.post("/webhooks/paypro")
async def paypro_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Response:
    raw_body = await request.body()
    headers = dict(request.headers)

    client = PayProClient()
    valid = client.verify_webhook_signature(raw_body, headers)

    # Step 2: reject unsigned / invalid-signature webhooks with 401, but record
    # the attempt. Unverified payloads are untrusted, so we store no event_id
    # (avoids polluting the dedup index with attacker-supplied ids).
    if not valid:
        logger.warning(
            "Rejected PayPro webhook with invalid signature from {}",
            request.client.host if request.client else "unknown",
        )
        session.add(
            PayProEvent(
                payload=_safe_json(raw_body),
                signature_valid=False,
                processed=False,
            )
        )
        await session.commit()
        return Response(status_code=401)

    payload = _safe_json(raw_body)
    fields = extract_webhook_fields(payload)

    # Step 4: dedup — if we've already processed this event, ack immediately.
    if fields.event_id:
        existing = await session.scalar(
            select(PayProEvent).where(
                PayProEvent.paypro_event_id == fields.event_id,
                PayProEvent.processed.is_(True),
            )
        )
        if existing:
            return Response(status_code=200)

    # Step 3: record the verified event.
    event = PayProEvent(
        paypro_event_id=fields.event_id,
        event_type=fields.event_type,
        payload=payload,
        signature_valid=True,
        processed=False,
    )
    session.add(event)

    # Step 5: match the order.
    order: Order | None = None
    if fields.invoice_id:
        order = await session.scalar(
            select(Order).where(Order.paypro_invoice_id == fields.invoice_id)
        )

    if order is not None:
        event.order_id = order.id
        is_paid, is_failed = classify_status(fields.status)
        now = datetime.now(timezone.utc)

        # Steps 6/7: idempotent state transitions from `pending` only.
        if is_paid and order.status == OrderStatus.pending:
            order.status = OrderStatus.paid
            order.paid_at = now
            # Step 6: kick off delivery (deliver_order is implemented in Phase 4).
            celery_app.send_task("deliver_order", args=[str(order.id)])
        elif is_failed and order.status == OrderStatus.pending:
            order.status = OrderStatus.failed
            order.failed_reason = f"PayPro status: {fields.status}"
    else:
        logger.warning(
            "PayPro webhook for unknown invoice_id={}", fields.invoice_id
        )

    # Step 8: mark processed. Whole handler is one transaction (step retry-safety).
    event.processed = True
    await session.commit()

    # Step 9.
    return Response(status_code=200)


def _safe_json(raw_body: bytes) -> dict:
    try:
        data = json.loads(raw_body or b"{}")
        return data if isinstance(data, dict) else {"_raw": data}
    except (ValueError, TypeError):
        return {"_unparseable": raw_body.decode("utf-8", "replace")[:2000]}
