"""Order delivery task (CLAUDE.md §9 Phase 4).

For catalog orders: presign the pack's CSV + XLSX in S3, email the links, and
mark the order delivered. Idempotent — a re-run on an already-delivered order
is a no-op. Enqueued by the PayPro webhook + reconciliation on payment.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from loguru import logger

from app.config import settings
from app.db import SessionLocal
from app.integrations.email import Mailer, build_delivery_email
from app.integrations.storage import S3Storage
from app.models.order import Order, OrderStatus, OrderType
from app.models.pack import Pack
from app.tasks.celery_app import celery_app


async def _deliver(order_id: UUID, *, storage=None, mailer=None) -> str:
    storage = storage or S3Storage()
    mailer = mailer or Mailer()

    async with SessionLocal() as session:
        order = await session.get(Order, order_id)
        if order is None:
            logger.warning("deliver_order: order {} not found", order_id)
            return "not_found"
        if order.status == OrderStatus.delivered:
            return "already_delivered"
        # Catalog arrives as `paid`; custom arrives as `processing` (post-scrape).
        if order.status not in (OrderStatus.paid, OrderStatus.processing):
            logger.warning(
                "deliver_order: order {} not deliverable (status={})", order_id, order.status
            )
            return "not_paid"

        # Resolve the deliverable S3 keys + email title per order type.
        if order.order_type == OrderType.catalog:
            pack = await session.get(Pack, order.pack_id) if order.pack_id else None
            if pack is None or not pack.s3_key_csv or not pack.s3_key_xlsx:
                order.status = OrderStatus.failed
                order.failed_reason = "pack files missing"
                await session.commit()
                return "pack_files_missing"
            csv_key, xlsx_key, title = pack.s3_key_csv, pack.s3_key_xlsx, pack.title
            order.delivery_s3_csv = csv_key
            order.delivery_s3_xlsx = xlsx_key
        else:  # custom — scrape_for_order already wrote the files + set the keys
            csv_key, xlsx_key = order.delivery_s3_csv, order.delivery_s3_xlsx
            if not csv_key or not xlsx_key:
                order.status = OrderStatus.failed
                order.failed_reason = "deliverables missing"
                await session.commit()
                return "deliverables_missing"
            spec = order.custom_spec or {}
            title = f"{spec.get('vertical', 'leads')} in {spec.get('city', '')}".strip()

        from app.models.customer import Customer

        customer = await session.get(Customer, order.customer_id)
        if customer is None:
            order.status = OrderStatus.failed
            order.failed_reason = "customer missing"
            await session.commit()
            return "customer_missing"

        ttl = settings.S3_PRESIGNED_URL_TTL_HOURS
        csv_url = storage.presign_get(csv_key)
        xlsx_url = storage.presign_get(xlsx_key)

        subject, html, text = build_delivery_email(
            customer_name=customer.name or "there",
            pack_title=title,
            csv_url=csv_url,
            xlsx_url=xlsx_url,
            ttl_hours=ttl,
        )
        mailer.send(to=customer.email, subject=subject, html=html, text=text)

        now = datetime.now(timezone.utc)
        order.delivery_email_sent_at = now
        order.delivered_at = now
        order.status = OrderStatus.delivered
        await session.commit()

    logger.info("Delivered order {}", order_id)
    return "delivered"


@celery_app.task(name="deliver_order")
def deliver_order(order_id: str) -> str:
    return asyncio.run(_deliver(UUID(order_id)))
