"""Custom-order scrape task (CLAUDE.md §9 Phase 5).

On payment, a custom order runs: Apify scrape -> normalize -> enrich -> write
CSV+XLSX to S3 -> enqueue deliver_order. Every Apify run is cost-guarded and
audited in apify_runs (Rule #6).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from loguru import logger

from app.config import settings
from app.db import SessionLocal
from app.integrations.apify import ApifyClient, ApifyCostExceeded, ApifyError, build_gmaps_input
from app.integrations.exporters import (
    CSV_CONTENT_TYPE,
    XLSX_CONTENT_TYPE,
    to_csv_bytes,
    to_xlsx_bytes,
)
from app.integrations.normalize import normalize_dataset
from app.integrations.storage import S3Storage
from app.models.order import Order, OrderStatus, OrderType
from app.services.quoting import record_density
from app.tasks.celery_app import celery_app
from app.tasks.enrich import enrich_emails


async def _scrape(order_id: UUID, *, make_apify=None, storage=None) -> str:
    make_apify = make_apify or (lambda session: ApifyClient(session))
    storage = storage or S3Storage()
    actor_id = settings.APIFY_ACTOR_GMAPS

    async with SessionLocal() as session:
        order = await session.get(Order, order_id)
        if order is None:
            return "not_found"
        if order.status == OrderStatus.delivered:
            return "already_delivered"
        if order.order_type != OrderType.custom:
            return "not_custom"
        if order.status not in (OrderStatus.paid, OrderStatus.processing):
            logger.warning("scrape: order {} not paid (status={})", order_id, order.status)
            return "not_paid"

        spec = order.custom_spec or {}
        city, vertical = spec.get("city", ""), spec.get("vertical", "")
        target = min(int(spec.get("target_count", 0)), settings.MAX_LEADS_PER_CUSTOM_ORDER)
        payload = build_gmaps_input([f"{vertical} in {city}"], target)

        order.status = OrderStatus.processing
        await session.flush()

        apify = make_apify(session)
        try:
            run_row = await apify.trigger_run(actor_id, payload, order_id=order.id)
        except ApifyCostExceeded as exc:
            order.status = OrderStatus.failed
            order.failed_reason = str(exc)
            await session.commit()
            return "cost_exceeded"

        try:
            result = await apify.poll_until_complete(
                run_row.apify_run_id, settings.APIFY_TIMEOUT_SECONDS
            )
        except ApifyError as exc:
            run_row.status = "FAILED"
            run_row.finished_at = datetime.now(timezone.utc)
            order.status = OrderStatus.failed
            order.failed_reason = f"Apify: {exc}"
            await session.commit()
            return "scrape_failed"

        run_row.status = result.status
        run_row.cost_usd = result.cost_usd
        run_row.finished_at = datetime.now(timezone.utc)

        items = await apify.fetch_dataset(result.dataset_id) if result.dataset_id else []
        scraped_at = (run_row.started_at or datetime.now(timezone.utc)).isoformat()
        rows = normalize_dataset(items, scraped_at)
        try:
            rows = await enrich_emails(rows)
        except Exception as exc:  # noqa: BLE001 — enrichment is best-effort
            logger.warning("Enrichment failed (continuing): {}", exc)
        run_row.results_count = len(rows)

        csv_key = f"orders/{order.id}/leads.csv"
        xlsx_key = f"orders/{order.id}/leads.xlsx"
        storage.put_bytes(csv_key, to_csv_bytes(rows), CSV_CONTENT_TYPE)
        storage.put_bytes(xlsx_key, to_xlsx_bytes(rows), XLSX_CONTENT_TYPE)
        order.delivery_s3_csv = csv_key
        order.delivery_s3_xlsx = xlsx_key

        # Phase 9 §15.5: record what we actually delivered, flag a refund if we
        # missed the guaranteed minimum, and feed the density estimator (§15.4).
        delivered = len(rows)
        order.delivered_leads = delivered
        if order.guaranteed_min_leads and delivered < order.guaranteed_min_leads:
            shortfall = order.guaranteed_min_leads - delivered
            order.refund_due_pkr = settings.CUSTOM_ORDER_PER_LEAD_PKR * shortfall
            logger.warning(
                "Order {} under guarantee: delivered {} < {} → refund_due PKR {} "
                "(manual via PayPro, §13)",
                order_id, delivered, order.guaranteed_min_leads, order.refund_due_pkr,
            )
        if city and vertical:
            await record_density(session, city, vertical, delivered)

        if result.status != "SUCCEEDED":
            order.status = OrderStatus.failed
            order.failed_reason = f"Apify run status {result.status}"
            await session.commit()
            return "scrape_failed"

        await session.commit()

    celery_app.send_task("deliver_order", args=[str(order_id)])
    logger.info("Scraped custom order {} ({} leads)", order_id, len(rows))
    return "scraped"


@celery_app.task(name="scrape_for_order")
def scrape_for_order(order_id: str) -> str:
    return asyncio.run(_scrape(UUID(order_id)))
