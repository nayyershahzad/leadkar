"""Backfill Wave-1 lead scores + tags onto the existing catalog deliverables.

Zero Apify spend: re-reads the already-scraped rows, applies scoring/tagging,
rewrites the S3 CSV+XLSX with the richer columns, and refreshes the pack's
`sample_preview` (stats + top-3) so the storefront shows the wow immediately.

By default it backfills `karachi-restaurants-dha` from the local 136-lead CSV
(the only pack with real data). Run inside the backend container:

    docker compose exec backend python scripts/backfill_scores.py
    docker compose exec backend python scripts/backfill_scores.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.db import SessionLocal
from app.integrations.exporters import (
    CSV_CONTENT_TYPE,
    XLSX_CONTENT_TYPE,
    to_csv_bytes,
    to_xlsx_bytes,
)
from app.integrations.normalize import CANONICAL_FIELDS
from app.integrations.storage import S3Storage
from app.models.pack import Pack
from app.services.scoring import build_sample_preview, score_and_rank

DATA_DIR = Path("data")


def _coerce(row: dict[str, str]) -> dict:
    """Old 18-column CSV row → canonical new-schema dict (unknown extras None)."""
    def val(key):
        v = row.get(key)
        return v if v not in ("", None) else None

    phone = val("phone")
    carrier = val("carrier")
    return {
        "lead_score": None,
        "signal_tags": None,
        "name": val("name"),
        "category": val("category"),
        "address": val("address"),
        "city": val("city") or "",
        "phone": phone,
        "carrier": carrier,
        "whatsapp": bool(carrier) and bool(phone) and phone.startswith("+923"),
        "website": val("website"),
        "email": val("email"),
        "rating": float(row["rating"]) if val("rating") else None,
        "reviews_count": int(row["reviews_count"]) if val("reviews_count") else None,
        "price_range": None,
        "claimed": None,  # not in the old scrape
        "permanently_closed": False,
        "temporarily_closed": False,
        "images_count": None,
        "lat": val("lat"),
        "lng": val("lng"),
        "google_place_id": val("google_place_id"),
        "instagram": val("instagram"),
        "facebook": val("facebook"),
        "twitter": None,
        "youtube": None,
        "tiktok": None,
        "linkedin": None,
        "pinterest": None,
        "opening_hours": val("opening_hours"),
        "source": val("source") or "google_maps",
        "scraped_at": val("scraped_at"),
    }


async def backfill(slug: str, dry_run: bool) -> int:
    csv_path = DATA_DIR / f"{slug}.csv"
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found.")
        return 1

    with csv_path.open(encoding="utf-8") as fh:
        rows = [_coerce(r) for r in csv.DictReader(fh)]
    rows = score_and_rank(rows)
    sample = build_sample_preview(rows)
    stats = sample["stats"]

    print(f"Pack:        {slug}")
    print(f"Leads:       {stats['lead_count']}")
    print(f"Avg score:   {stats['avg_lead_score']}")
    print(f"WhatsApp:    {stats['pct_whatsapp']}%   Email: {stats['pct_email']}%   "
          f"Website: {stats['pct_website']}%")
    print(f"Hidden gems: {stats['hidden_gems']}")
    print("Top 5 by score:")
    for r in rows[:5]:
        print(f"  {r['lead_score']:>3}  {r['name'][:34]:<34}  {r['signal_tags']}")

    if dry_run:
        print("\nDRY RUN — no S3 write, no DB update.")
        return 0

    async with SessionLocal() as session:
        pack = await session.scalar(select(Pack).where(Pack.slug == slug))
        if pack is None:
            print(f"ERROR: pack '{slug}' not in DB.")
            return 1

        csv_key = pack.s3_key_csv or f"packs/{slug}.csv"
        xlsx_key = pack.s3_key_xlsx or f"packs/{slug}.xlsx"
        storage = S3Storage()
        storage.put_bytes(csv_key, to_csv_bytes(rows), CSV_CONTENT_TYPE)
        storage.put_bytes(xlsx_key, to_xlsx_bytes(rows), XLSX_CONTENT_TYPE)

        pack.s3_key_csv = csv_key
        pack.s3_key_xlsx = xlsx_key
        pack.sample_preview = sample
        pack.last_refreshed_at = datetime.now(timezone.utc)
        await session.commit()

    # Also refresh the local copies so they carry the new columns.
    (DATA_DIR / f"{slug}.csv").write_bytes(to_csv_bytes(rows))
    (DATA_DIR / f"{slug}.xlsx").write_bytes(to_xlsx_bytes(rows))
    print(f"\nWrote S3 {csv_key} + {xlsx_key} ({len(CANONICAL_FIELDS)} cols) and "
          f"updated pack.sample_preview.")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill Wave-1 scores onto a pack.")
    ap.add_argument("--pack-slug", default="karachi-restaurants-dha")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.exit(asyncio.run(backfill(args.pack_slug, args.dry_run)))


if __name__ == "__main__":
    main()
