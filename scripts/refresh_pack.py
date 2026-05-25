"""Trigger an Apify run for a catalog pack and write results to local disk.

Phase 3 CLI (CLAUDE.md §9). Examples:

    # Estimate cost only — never spends, never starts a run:
    python scripts/refresh_pack.py --pack-slug karachi-restaurants-dha --dry-run

    # Real run (spends Apify credit; requires APIFY_API_TOKEN):
    python scripts/refresh_pack.py --pack-slug karachi-restaurants-dha

Output: data/<slug>.csv and data/<slug>.xlsx, plus an audit row in apify_runs.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow `python scripts/refresh_pack.py` (path-run) by putting the repo root —
# which holds both the `app` and `scripts` packages — on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import Workbook

from app.config import settings
from app.db import SessionLocal
from app.integrations.apify import ApifyClient, build_gmaps_input
from app.integrations.normalize import CANONICAL_FIELDS, normalize_dataset
from scripts.catalog import CATALOG

OUTPUT_DIR = Path("data")


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CANONICAL_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_xlsx(path: Path, rows: list[dict]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "leads"
    ws.append(CANONICAL_FIELDS)
    for row in rows:
        ws.append([row.get(field) for field in CANONICAL_FIELDS])
    wb.save(path)


async def run(slug: str, dry_run: bool) -> int:
    spec = CATALOG.get(slug)
    if spec is None:
        print(f"ERROR: unknown pack slug '{slug}'. Known: {', '.join(CATALOG)}")
        return 2

    actor_id = settings.APIFY_ACTOR_GMAPS
    payload = build_gmaps_input(spec.search_strings, spec.lead_count)

    # estimate_cost is pure — safe to call without a token or DB session.
    estimate = ApifyClient().estimate_cost(actor_id, payload)
    print(f"Pack:       {spec.slug} — {spec.title}")
    print(f"Actor:      {actor_id}")
    print(f"Searches:   {spec.search_strings}")
    print(f"Per-search: {payload['maxCrawledPlacesPerSearch']} (target {spec.lead_count})")
    print(f"Estimate:   ${estimate}  (cap ${settings.APIFY_MAX_USD_PER_RUN})")

    if dry_run:
        print("DRY RUN — no run started, no spend, no DB write.")
        if estimate > settings.APIFY_MAX_USD_PER_RUN:
            print("WARNING: estimate exceeds the cap; a real run would abort.")
        return 0

    if not settings.APIFY_API_TOKEN:
        print("ERROR: APIFY_API_TOKEN is not set; cannot start a real run.")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with SessionLocal() as session:
        client = ApifyClient(session)
        run_row = await client.trigger_run(actor_id, payload, pack_id=None)
        print(f"Started Apify run {run_row.apify_run_id}; polling…")

        result = await client.poll_until_complete(
            run_row.apify_run_id, settings.APIFY_TIMEOUT_SECONDS
        )
        print(f"Run finished: status={result.status} cost=${result.cost_usd}")

        items: list[dict] = []
        if result.dataset_id:
            items = await client.fetch_dataset(result.dataset_id)

        scraped_at = (run_row.started_at or datetime.now(timezone.utc)).isoformat()
        rows = normalize_dataset(items, scraped_at)

        # Persist the audit fields.
        run_row.status = result.status
        run_row.cost_usd = result.cost_usd
        run_row.results_count = len(rows)
        run_row.finished_at = datetime.now(timezone.utc)
        await session.commit()

    csv_path = OUTPUT_DIR / f"{slug}.csv"
    xlsx_path = OUTPUT_DIR / f"{slug}.xlsx"
    _write_csv(csv_path, rows)
    _write_xlsx(xlsx_path, rows)
    print(f"Wrote {len(rows)} normalized rows -> {csv_path}, {xlsx_path}")

    if result.status != "SUCCEEDED":
        print(f"WARNING: run status was {result.status}, not SUCCEEDED.")
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh a LeadKar catalog pack via Apify.")
    parser.add_argument("--pack-slug", required=True, help="Catalog pack slug (see scripts/catalog.py)")
    parser.add_argument("--dry-run", action="store_true", help="Print cost estimate only; no spend.")
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.pack_slug, args.dry_run)))


if __name__ == "__main__":
    main()
