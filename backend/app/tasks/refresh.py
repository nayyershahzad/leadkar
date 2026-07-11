"""Quarterly catalog refresh (CLAUDE.md §5, §9 Phase 8).

Re-scrapes every active pack and refreshes its S3 deliverables + sample preview.
OFF by default (CATALOG_REFRESH_ENABLED) because it spends real Apify credit
(Rule #6). Beat schedules it; this task no-ops until explicitly enabled.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.integrations.apify import ApifyClient, ApifyError, build_gmaps_input
from app.integrations.exporters import (
    CSV_CONTENT_TYPE,
    XLSX_CONTENT_TYPE,
    to_csv_bytes,
    to_xlsx_bytes,
)
from app.integrations.normalize import normalize_dataset
from app.integrations.storage import S3Storage
from app.models.pack import Pack
from app.services.scoring import build_sample_preview, score_and_rank
from app.tasks.celery_app import celery_app


async def _refresh() -> str:
    if not settings.CATALOG_REFRESH_ENABLED:
        logger.info("Catalog refresh disabled (CATALOG_REFRESH_ENABLED=false); skipping")
        return "disabled"

    storage = S3Storage()
    actor_id = settings.APIFY_ACTOR_GMAPS
    refreshed = 0

    async with SessionLocal() as session:
        packs = (await session.scalars(select(Pack).where(Pack.is_active.is_(True)))).all()
        for pack in packs:
            payload = build_gmaps_input([f"{pack.vertical} in {pack.city}"], pack.lead_count)
            apify = ApifyClient(session)
            try:
                run = await apify.trigger_run(actor_id, payload, pack_id=pack.id)
                result = await apify.poll_until_complete(
                    run.apify_run_id, settings.APIFY_TIMEOUT_SECONDS
                )
                items = await apify.fetch_dataset(result.dataset_id) if result.dataset_id else []
            except ApifyError as exc:
                logger.warning("Refresh failed for pack {}: {}", pack.slug, exc)
                continue

            scraped_at = (run.started_at or datetime.now(timezone.utc)).isoformat()
            rows = normalize_dataset(items, scraped_at)
            rows = score_and_rank(rows)
            run.status = result.status
            run.cost_usd = result.cost_usd
            run.results_count = len(rows)
            run.finished_at = datetime.now(timezone.utc)

            csv_key = pack.s3_key_csv or f"packs/{pack.slug}.csv"
            xlsx_key = pack.s3_key_xlsx or f"packs/{pack.slug}.xlsx"
            storage.put_bytes(csv_key, to_csv_bytes(rows), CSV_CONTENT_TYPE)
            storage.put_bytes(xlsx_key, to_xlsx_bytes(rows), XLSX_CONTENT_TYPE)

            pack.s3_key_csv = csv_key
            pack.s3_key_xlsx = xlsx_key
            pack.sample_preview = build_sample_preview(rows)
            pack.last_refreshed_at = datetime.now(timezone.utc)
            refreshed += 1

        await session.commit()

    logger.info("Catalog refresh complete: {} pack(s)", refreshed)
    return f"refreshed:{refreshed}"


@celery_app.task(name="refresh_catalog")
def refresh_catalog() -> str:
    return asyncio.run(_refresh())
