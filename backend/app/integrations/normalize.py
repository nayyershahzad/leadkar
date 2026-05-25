"""Map Apify Google-Maps actor output to the LeadKar canonical schema (CLAUDE.md §8)."""

from __future__ import annotations

import json
import re
from typing import Any

# Canonical column order for CSV/XLSX deliverables.
CANONICAL_FIELDS: list[str] = [
    "name",
    "category",
    "address",
    "city",
    "phone",
    "carrier",
    "website",
    "email",
    "rating",
    "reviews_count",
    "lat",
    "lng",
    "google_place_id",
    "instagram",
    "facebook",
    "opening_hours",
    "source",
    "scraped_at",
]

# Second digit of the +92 3XX mobile prefix -> carrier (CLAUDE.md §8).
_CARRIER_BY_PREFIX: dict[str, str] = {
    "30": "Jazz",
    "31": "Zong",
    "32": "Warid (now Jazz)",
    "33": "Ufone",
    "34": "Telenor",
    "35": "SCOM",
}

_NON_DIGIT = re.compile(r"\D")


def normalize_phone_pk(phone: str | None) -> tuple[str | None, str | None]:
    """Return (normalized_phone, carrier).

    A local mobile starting with ``03`` becomes ``+92`` + the number without its
    leading 0, and is tagged by carrier. Anything else is returned as-is with no
    carrier (CLAUDE.md §8).
    """
    if not phone:
        return None, None

    raw = phone.strip()
    digits = _NON_DIGIT.sub("", raw)

    # Local format: 03XXXXXXXXX (11 digits).
    if digits.startswith("03") and len(digits) == 11:
        national = digits[1:]  # drop leading 0 -> 3XXXXXXXXX
        normalized = "+92" + national
        carrier = _CARRIER_BY_PREFIX.get(national[:2])
        return normalized, carrier

    # Already +92 / 0092 form.
    if digits.startswith("92") and len(digits) == 12:
        national = digits[2:]  # 3XXXXXXXXX
        normalized = "+92" + national
        carrier = _CARRIER_BY_PREFIX.get(national[:2]) if national.startswith("3") else None
        return normalized, carrier

    return raw, None


def _first(seq: Any) -> Any:
    if isinstance(seq, list) and seq:
        return seq[0]
    return None


def normalize_place(raw: dict[str, Any], scraped_at: str) -> dict[str, Any]:
    """Map one Apify place record to the canonical LeadKar lead dict."""
    phone, carrier = normalize_phone_pk(raw.get("phone"))
    opening_hours = raw.get("openingHours")

    return {
        "name": raw.get("title"),
        "category": raw.get("categoryName"),
        "address": raw.get("address"),
        "city": raw.get("city") or "",
        "phone": phone,
        "carrier": carrier,
        "website": raw.get("website"),
        "email": None,  # filled by the enrichment task (Phase 5)
        "rating": raw.get("totalScore"),
        "reviews_count": raw.get("reviewsCount"),
        "lat": (raw.get("location") or {}).get("lat"),
        "lng": (raw.get("location") or {}).get("lng"),
        "google_place_id": raw.get("placeId"),
        "instagram": _first(raw.get("instagrams")),
        "facebook": _first(raw.get("facebooks")),
        "opening_hours": json.dumps(opening_hours, ensure_ascii=False)
        if opening_hours is not None
        else None,
        "source": "google_maps",
        "scraped_at": scraped_at,
    }


def normalize_dataset(items: list[dict[str, Any]], scraped_at: str) -> list[dict[str, Any]]:
    return [normalize_place(item, scraped_at) for item in items]
