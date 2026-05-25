"""Reconciliation safety net (CLAUDE.md §7).

Every 15 minutes, scan orders still `pending` for >10 minutes that have a
PayPro invoice, and ask PayPro directly — catching webhooks that never arrived.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from loguru import logger
from sqlalchemy import select

from app.db import SessionLocal
from app.integrations.paypro import PayProClient
from app.models.order import Order, OrderStatus
from app.tasks.celery_app import celery_app


async def _reconcile() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    reconciled = 0
    client = PayProClient()

    async with SessionLocal() as session:
        stale = (
            await session.scalars(
                select(Order).where(
                    Order.status == OrderStatus.pending,
                    Order.paypro_invoice_id.is_not(None),
                    Order.created_at < cutoff,
                )
            )
        ).all()

        for order in stale:
            try:
                status = await client.get_invoice_status(order.paypro_invoice_id)
            except Exception as exc:  # noqa: BLE001 — log and continue per order
                logger.warning("Reconcile failed for order {}: {}", order.id, exc)
                continue

            now = datetime.now(timezone.utc)
            if status.is_paid:
                order.status = OrderStatus.paid
                order.paid_at = now
                celery_app.send_task("deliver_order", args=[str(order.id)])
                reconciled += 1
            elif status.is_failed:
                order.status = OrderStatus.failed
                order.failed_reason = f"PayPro status (reconcile): {status.status}"
                reconciled += 1

        await session.commit()

    if reconciled:
        logger.info("Reconciliation updated {} order(s)", reconciled)
    return reconciled


@celery_app.task(name="reconcile_pending_orders")
def reconcile_pending_orders() -> int:
    """Celery entrypoint; runs the async reconcile in a fresh event loop."""
    return asyncio.run(_reconcile())
