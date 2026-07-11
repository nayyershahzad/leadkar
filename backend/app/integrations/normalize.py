"""Map Apify Google-Maps actor output to the LeadKar canonical schema (CLAUDE.md §8)."""

from __future__ import annotations

import json
import re
from typing import Any

# Canonical column order for CSV/XLSX deliverables. lead_score + signal_tags lead
# so buyers see the headline differentiator first (wow_factor Wave 1).
CANONICAL_FIELDS: list[str] = [
    "lead_score",
    "signal_tags",
    "name",
    "category",
    "address",
    "city",
    "phone",
    "carrier",
    "whatsapp",
    "website",
    "email",
    "rating",
    "reviews_count",
    "price_range",
    "claimed",
    "permanently_closed",
    "temporarily_closed",
    "images_count",
    "lat",
    "lng",
    "google_place_id",
    "instagram",
    "facebook",
    "twitter",
    "youtube",
    "tiktok",
    "linkedin",
    "pinterest",
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


def _is_whatsapp_likely(phone: str | None, carrier: str | None) -> bool:
    """A normalized +92 3XX mobile is *usually* on WhatsApp (cheatsheet §5). Flag
    only — never "verified". A tagged carrier means we recognised a PK mobile."""
    return bool(carrier) and bool(phone) and phone.startswith("+923")


def normalize_place(raw: dict[str, Any], scraped_at: str) -> dict[str, Any]:
    """Map one Apify place record to the canonical LeadKar lead dict.

    Extra fields beyond the original 18 come from the *same* compass actor at no
    extra Apify spend (cheatsheet §2b). ``lead_score`` / ``signal_tags`` are left
    unset here and populated by ``scoring.score_and_rank`` after enrichment.
    """
    phone, carrier = normalize_phone_pk(raw.get("phone"))
    opening_hours = raw.get("openingHours")

    # ``claimThisBusiness`` is INVERTED (verified against the live actor page):
    # True => still claimable => UNCLAIMED; False => already claimed. Only derive
    # a bool when the actor actually returned the field.
    ctb = raw.get("claimThisBusiness")
    claimed = (not ctb) if isinstance(ctb, bool) else None

    return {
        "lead_score": None,  # set by scoring.score_and_rank
        "signal_tags": None,  # set by scoring.score_and_rank
        "name": raw.get("title"),
        "category": raw.get("categoryName"),
        "address": raw.get("address"),
        "city": raw.get("city") or "",
        "phone": phone,
        "carrier": carrier,
        "whatsapp": _is_whatsapp_likely(phone, carrier),
        "website": raw.get("website"),
        "email": None,  # filled by the enrichment task (Phase 5)
        "rating": raw.get("totalScore"),
        "reviews_count": raw.get("reviewsCount"),
        "price_range": raw.get("price"),
        "claimed": claimed,
        "permanently_closed": bool(raw.get("permanentlyClosed")),
        "temporarily_closed": bool(raw.get("temporarilyClosed")),
        "images_count": raw.get("imagesCount"),
        "lat": (raw.get("location") or {}).get("lat"),
        "lng": (raw.get("location") or {}).get("lng"),
        "google_place_id": raw.get("placeId"),
        "instagram": _first(raw.get("instagrams")),
        "facebook": _first(raw.get("facebooks")),
        "twitter": _first(raw.get("twitters")),
        "youtube": _first(raw.get("youtubes")),
        "tiktok": _first(raw.get("tiktoks")),
        "linkedin": _first(raw.get("linkedIns")),
        "pinterest": _first(raw.get("pinterests")),
        "opening_hours": json.dumps(opening_hours, ensure_ascii=False)
        if opening_hours is not None
        else None,
        "source": "google_maps",
        "scraped_at": scraped_at,
    }


def normalize_dataset(items: list[dict[str, Any]], scraped_at: str) -> list[dict[str, Any]]:
    return [normalize_place(item, scraped_at) for item in items]
