"""Apify integration wrapper (CLAUDE.md §8).

Isolates all Apify API specifics behind a single class. Every actor invocation
is cost-checked against APIFY_MAX_USD_PER_RUN *before* spending, and recorded in
the ``apify_runs`` table (Rule #6).
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from apify_client import ApifyClientAsync
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.apify_run import ApifyRun

# compass/crawler-google-places bills roughly $5 per 1000 results (CLAUDE.md §8).
UNIT_COST_PER_RESULT = Decimal("0.005")

# Apify run lifecycle terminal states.
_TERMINAL_STATES = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}


class ApifyError(RuntimeError):
    """Generic Apify failure."""


class ApifyCostExceeded(ApifyError):
    """Estimated cost exceeds APIFY_MAX_USD_PER_RUN; the run was not started."""


@dataclass
class ApifyRunResult:
    apify_run_id: str
    status: str
    cost_usd: Decimal | None
    dataset_id: str | None
    results_count: int | None = None


class ApifyClient:
    """Thin async wrapper around ApifyClientAsync with cost guarding + auditing.

    A ``session`` is required only for ``trigger_run`` (which persists an
    ``apify_runs`` row). ``estimate_cost`` is pure and needs neither a token nor
    a session, so the CLI dry-run path can call it freely.
    """

    def __init__(
        self,
        session: AsyncSession | None = None,
        *,
        token: str | None = None,
        client: ApifyClientAsync | None = None,
    ) -> None:
        self._session = session
        self._token = token if token is not None else settings.APIFY_API_TOKEN
        self._client = client

    @property
    def client(self) -> ApifyClientAsync:
        if self._client is None:
            if not self._token:
                raise ApifyError("APIFY_API_TOKEN is not set")
            self._client = ApifyClientAsync(self._token)
        return self._client

    def estimate_cost(self, actor_id: str, input_payload: dict[str, Any]) -> Decimal:
        """Best-effort pre-run estimate: per_search_cap * search_count * unit_cost."""
        per_search = int(input_payload.get("maxCrawledPlacesPerSearch", 0) or 0)
        searches = input_payload.get("searchStringsArray") or []
        search_count = max(len(searches), 1)
        return (Decimal(per_search) * Decimal(search_count) * UNIT_COST_PER_RESULT).quantize(
            Decimal("0.0001")
        )

    async def trigger_run(
        self,
        actor_id: str,
        input_payload: dict[str, Any],
        order_id: UUID | None = None,
        pack_id: UUID | None = None,
    ) -> ApifyRun:
        """Cost-check, start the actor, and persist an ``apify_runs`` row."""
        estimate = self.estimate_cost(actor_id, input_payload)
        cap = settings.APIFY_MAX_USD_PER_RUN
        if estimate > cap:
            raise ApifyCostExceeded(
                f"Estimated ${estimate} exceeds APIFY_MAX_USD_PER_RUN ${cap}"
            )

        if self._session is None:
            raise ApifyError("trigger_run requires a database session")

        run_row = ApifyRun(
            order_id=order_id,
            pack_id=pack_id,
            actor_id=actor_id,
            input_payload=input_payload,
            status="STARTING",
            started_at=datetime.now(timezone.utc),
        )
        self._session.add(run_row)
        await self._session.flush()

        logger.info(
            "Starting Apify actor {} (estimate ${}, cap ${})", actor_id, estimate, cap
        )
        started = await self.client.actor(actor_id).start(run_input=input_payload)

        run_row.apify_run_id = started.get("id")
        run_row.status = started.get("status", "RUNNING")
        await self._session.commit()
        await self._session.refresh(run_row)
        return run_row

    async def poll_until_complete(
        self, apify_run_id: str, timeout_seconds: int
    ) -> ApifyRunResult:
        """Poll the run every 30s until terminal or timeout."""
        deadline = asyncio.get_event_loop().time() + timeout_seconds
        while True:
            run = await self.client.run(apify_run_id).get()
            if run is None:
                raise ApifyError(f"Apify run {apify_run_id} not found")
            status = run.get("status", "")
            if status in _TERMINAL_STATES:
                cost = run.get("usageTotalUsd")
                return ApifyRunResult(
                    apify_run_id=apify_run_id,
                    status=status,
                    cost_usd=Decimal(str(cost)) if cost is not None else None,
                    dataset_id=run.get("defaultDatasetId"),
                    results_count=run.get("itemCount"),
                )
            if asyncio.get_event_loop().time() >= deadline:
                raise ApifyError(
                    f"Apify run {apify_run_id} timed out after {timeout_seconds}s "
                    f"(last status {status})"
                )
            await asyncio.sleep(30)

    async def fetch_dataset(self, dataset_id: str) -> list[dict[str, Any]]:
        """Fetch all items from the run's default dataset."""
        items: list[dict[str, Any]] = []
        offset = 0
        page_size = 1000
        while True:
            page = await self.client.dataset(dataset_id).list_items(
                offset=offset, limit=page_size
            )
            batch = page.items
            items.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        return items


def build_gmaps_input(
    search_strings: list[str], target_count: int, *, language: str | None = None
) -> dict[str, Any]:
    """Build the Google-Maps actor input payload (CLAUDE.md §8 template).

    ``maxCrawledPlacesPerSearch`` caps results *per search string*, so the cap is
    the target divided across the search strings.
    """
    per_search = max(1, math.ceil(target_count / max(len(search_strings), 1)))
    return {
        "searchStringsArray": search_strings,
        "maxCrawledPlacesPerSearch": per_search,
        "language": language or settings.APIFY_DEFAULT_LANGUAGE,
        "includeImages": False,
        "scrapeContacts": True,
        "scrapePlaceDetailPage": True,
        "skipClosedPlaces": True,
    }
