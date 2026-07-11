"""Lead scoring + signal tags (wow_factor Wave 1 · leadgen_cheatsheet §3–§4).

Pure, server-side, zero Apify spend. The score is a 0–100 sort key that ranks
leads *within a deliverable* best-first; the tags are human-readable qualifiers.

Design note (cheatsheet §4): inside one pack every lead shares the same
city+vertical, so "fit" is constant and useless for intra-pack sorting. We spend
all the weight on the three axes that *vary per row*:
Contactability (40) + Business quality (35) + Digital maturity (25), minus
freshness/quality negatives.

The US review-count bands (50/500) are wrong for Pakistan (a real Karachi
restaurant scrape yields ~136 leads with far lower review counts than US norms),
so the bands here are PK-scaled starting hypotheses — recalibrate per
city×vertical from `lead_density_stats` once there's enough data.
"""

from __future__ import annotations

import math
from typing import Any

# Role-based local-parts: a function, not a person. Present but low-value, so
# they don't earn the "non-generic email" contactability points.
_GENERIC_EMAIL_PREFIXES = (
    "info@",
    "sales@",
    "contact@",
    "admin@",
    "support@",
    "hello@",
    "office@",
    "enquiry@",
    "enquiries@",
    "help@",
    "mail@",
)

_SOCIAL_FIELDS = (
    "instagram",
    "facebook",
    "twitter",
    "youtube",
    "tiktok",
    "linkedin",
    "pinterest",
)

# PK-scaled review-count bands (cheatsheet §3 — deliberately lower than US).
_NEW_UNPROVEN_MAX = 20
_ESTABLISHED_MAX = 150


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int:
    f = _to_float(value)
    return int(f) if f is not None else 0


def _truthy(value: Any) -> bool:
    """A field counts as present when it's a non-empty, non-false value."""
    if value in (None, "", False):
        return False
    return True


def _has_email(row: dict[str, Any]) -> bool:
    return _truthy(row.get("email"))


def _has_non_generic_email(row: dict[str, Any]) -> bool:
    email = row.get("email")
    if not _truthy(email):
        return False
    return not str(email).strip().lower().startswith(_GENERIC_EMAIL_PREFIXES)


def _any_social(row: dict[str, Any]) -> bool:
    return any(_truthy(row.get(f)) for f in _SOCIAL_FIELDS)


def _is_closed(row: dict[str, Any]) -> bool:
    return bool(row.get("permanently_closed")) or bool(row.get("temporarily_closed"))


def compute_lead_score(row: dict[str, Any], *, is_duplicate: bool = False) -> int:
    """0–100 contactability/quality/maturity score (cheatsheet §4).

    ``is_duplicate`` is supplied by the caller (it needs cross-row context on
    ``google_place_id``) and applies the −15 duplicate penalty.
    """
    has_phone = _truthy(row.get("phone"))
    has_website = _truthy(row.get("website"))
    has_social = _any_social(row)

    # Contactability (40)
    contactability = 0
    if has_phone:
        contactability += 15
    if _has_non_generic_email(row):
        contactability += 15
    if has_website:
        contactability += 5
    if has_social:
        contactability += 5

    # Business quality (35)
    rating = _to_float(row.get("rating"))
    reviews = _to_int(row.get("reviews_count"))
    quality = 0.0
    if rating is not None:
        quality += max(0.0, min(20.0, ((rating - 3.0) / 2.0) * 20.0))
    if reviews > 0:
        quality += min(15.0, 5.0 * math.log10(1 + reviews))

    # Digital maturity (25)
    maturity = 0
    if has_website:
        maturity += 10
    if has_social:
        maturity += 10
    if _truthy(row.get("opening_hours")):
        maturity += 5

    # Negatives
    negatives = 0
    if _is_closed(row):
        negatives -= 30
    if not has_phone and not _has_email(row):
        negatives -= 20
    if is_duplicate:
        negatives -= 15

    score = contactability + quality + maturity + negatives
    return int(max(0, min(100, round(score))))


def signal_tags(row: dict[str, Any]) -> list[str]:
    """Human-readable qualifiers. Compound signals; never tag on one field alone
    (cheatsheet §3). Returned lowest-noise-first for display."""
    tags: list[str] = []

    if _is_closed(row):
        tags.append("closed")

    rating = _to_float(row.get("rating"))
    reviews = _to_int(row.get("reviews_count"))
    has_website = _truthy(row.get("website"))

    # Reputation.
    if rating is not None and rating <= 3.5 and reviews >= 5:
        tags.append("reputation_risk")

    # Hidden gem: strong rating + a small (but real) review base + a website —
    # three compounded signals, not rating alone.
    if (
        rating is not None
        and rating >= 4.5
        and 5 <= reviews <= 30
        and has_website
    ):
        tags.append("hidden_gem")

    # Maturity bands (PK-scaled).
    if reviews > 0:
        if reviews < _NEW_UNPROVEN_MAX:
            tags.append("new_unproven")
        elif reviews <= _ESTABLISHED_MAX:
            tags.append("established")
        else:
            tags.append("major_chain")

    # GBP / web presence.
    if row.get("claimed") is False:
        tags.append("unclaimed")
    tags.append("has_website" if has_website else "no_website")

    # The PK wow field.
    if row.get("whatsapp"):
        tags.append("whatsapp_reachable")

    return tags


def score_and_rank(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Populate ``lead_score`` + ``signal_tags`` on every row (in place) and
    return the list sorted by score desc so buyers see best-first.

    ``signal_tags`` is stored as a ``|``-joined string so it survives CSV/XLSX
    export as one column; the structured list stays available via
    :func:`signal_tags` for stats.
    """
    seen_place_ids: set[str] = set()
    for row in rows:
        pid = row.get("google_place_id")
        is_dup = bool(pid) and pid in seen_place_ids
        if pid:
            seen_place_ids.add(pid)
        row["lead_score"] = compute_lead_score(row, is_duplicate=is_dup)
        row["signal_tags"] = "|".join(signal_tags(row))
    rows.sort(key=lambda r: r.get("lead_score") or 0, reverse=True)
    return rows


def _pct(part: int, whole: int) -> int:
    return round(100 * part / whole) if whole else 0


def build_sample_preview(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Pack-level quality summary + top-3 preview rows for the storefront.

    Shape: ``{"rows": [...3 best...], "stats": {...}}``. ``rows`` stays
    backwards-compatible with the existing frontend (`sampleRows`); ``stats`` is
    the Wave-1 wow (avg score, %WhatsApp, %email, hidden-gem count, freshness).
    """
    total = len(rows)
    scored = [r for r in rows if r.get("lead_score") is not None]
    avg_score = round(sum(int(r["lead_score"]) for r in scored) / len(scored)) if scored else 0

    def _tagset(r: dict[str, Any]) -> set[str]:
        raw = r.get("signal_tags")
        if isinstance(raw, str):
            return set(filter(None, raw.split("|")))
        if isinstance(raw, list):
            return set(raw)
        return set()

    whatsapp = sum(1 for r in rows if r.get("whatsapp"))
    with_email = sum(1 for r in rows if _has_email(r))
    with_phone = sum(1 for r in rows if _truthy(r.get("phone")))
    with_website = sum(1 for r in rows if _truthy(r.get("website")))
    hidden_gems = sum(1 for r in rows if "hidden_gem" in _tagset(r))

    return {
        "rows": rows[:3],
        "stats": {
            "lead_count": total,
            "avg_lead_score": avg_score,
            "pct_whatsapp": _pct(whatsapp, total),
            "pct_email": _pct(with_email, total),
            "pct_phone": _pct(with_phone, total),
            "pct_website": _pct(with_website, total),
            "hidden_gems": hidden_gems,
        },
    }
