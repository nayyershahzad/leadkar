"""Email enrichment (CLAUDE.md §8): best-effort scrape of lead websites.

Fetches each lead's homepage + /contact + /about and regex-extracts an email.
Best-effort and bounded — failures and timeouts are skipped, never fatal.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx
from loguru import logger

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_IMG_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
_PATHS = ("", "/contact", "/contact-us", "/about")


def extract_emails(html: str) -> list[str]:
    """Return de-duplicated, plausible emails from HTML (drops image artifacts)."""
    seen: list[str] = []
    for match in _EMAIL_RE.findall(html or ""):
        low = match.lower()
        if low.endswith(_IMG_EXTS) or low in (s.lower() for s in seen):
            continue
        seen.append(match)
    return seen


async def enrich_emails(
    rows: list[dict[str, Any]], *, timeout: float = 5.0, concurrency: int = 10
) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True, headers={"User-Agent": "LeadKar/1.0"}
    ) as client:

        async def enrich_one(row: dict[str, Any]) -> None:
            if row.get("email") or not row.get("website"):
                return
            base = str(row["website"]).rstrip("/")
            async with sem:
                for path in _PATHS:
                    try:
                        resp = await client.get(base + path)
                    except (httpx.HTTPError, ValueError):
                        continue
                    emails = extract_emails(resp.text)
                    if emails:
                        row["email"] = emails[0]
                        return

        await asyncio.gather(*(enrich_one(r) for r in rows), return_exceptions=True)

    hit = sum(1 for r in rows if r.get("email"))
    logger.info("Enrichment found emails for {}/{} leads", hit, len(rows))
    return rows
