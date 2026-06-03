"""Server-authoritative quoting (CLAUDE.md §15.2/§15.4/§15.6).

ALL money and lead counts originate here, never in the LLM. The assistant passes
free-text intent in; this module decides catalog-vs-custom, computes the price and
(for custom) a conservative guaranteed minimum, and persists a locked ``Quote``.
An order is later created by referencing that quote id.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.pack import Pack
from app.models.quote import LeadDensityStat, Quote

# Free-text business type -> our catalog vertical slugs. Keys are substrings
# matched against a lowercased query; first hit wins.
_VERTICAL_SYNONYMS: list[tuple[tuple[str, ...], str]] = [
    (("restaurant", "cafe", "coffee", "eatery", "dining"), "restaurants"),
    (("dental", "dentist", "orthodont"), "dental_clinics"),
    (("school", "montessori", "academy", "college"), "schools"),
    (("real estate", "property", "estate agent", "realtor", "builder"), "real_estate"),
    (("salon", "spa", "parlour", "parlor", "beauty", "barber"), "salons"),
    (("wedding", "marquee", "banquet", "event planner"), "wedding"),
    (("gym", "fitness", "crossfit", "yoga"), "gyms"),
    (("clinic", "doctor", "hospital", "medical", "physician"), "medical_clinics"),
    (("garment", "textile", "apparel", "clothing factory", "manufactur"), "garment_mfg"),
]


def normalize_vertical(text: str | None) -> str:
    """Map free text to a known vertical slug, falling back to a slugified form."""
    if not text:
        return ""
    low = text.lower()
    for needles, slug in _VERTICAL_SYNONYMS:
        if any(n in low for n in needles):
            return slug
    return "_".join(low.split())


def round_to_x99(amount: int) -> int:
    """Round up to the nearest hundred, then to a ...99 ending (e.g. 2000->1999)."""
    hundreds = (amount + 99) // 100 * 100
    return hundreds - 1


def catalog_price(lead_count: int) -> int:
    """Volume catalog price (§15.6): max(floor, round99(leads * per_lead))."""
    by_rule = round_to_x99(lead_count * settings.CATALOG_PKR_PER_LEAD)
    return max(settings.CATALOG_MIN_PRICE_PKR, by_rule)


def custom_price(guaranteed_min: int) -> int:
    """Custom price (§Phase-5 formula) applied to the GUARANTEED floor, not the ask."""
    return settings.CUSTOM_ORDER_BASE_PKR + settings.CUSTOM_ORDER_PER_LEAD_PKR * guaranteed_min


async def match_catalog(session: AsyncSession, city: str, vertical: str) -> Pack | None:
    """Find a deliverable active pack for this city+vertical (case-insensitive city)."""
    if not city or not vertical:
        return None
    return await session.scalar(
        select(Pack)
        .where(
            func.lower(Pack.city) == city.lower(),
            Pack.vertical == vertical,
            Pack.is_active.is_(True),
            Pack.s3_key_csv.isnot(None),
            Pack.s3_key_xlsx.isnot(None),
        )
        .order_by(Pack.lead_count.desc())
    )


async def estimate_minimum(
    session: AsyncSession, city: str, vertical: str, count_wanted: int
) -> tuple[int, int, int]:
    """Conservative guaranteed minimum + likely range (§15.4).

    Anchor on historical delivered counts when we have them; otherwise fall back
    to a fraction of the requested count. Always bounded by the ask and the cap.
    """
    cap = settings.MAX_LEADS_PER_CUSTOM_ORDER
    want = max(1, min(count_wanted or 0, cap)) if count_wanted else min(cap, 200)

    stat = await session.scalar(
        select(LeadDensityStat).where(
            func.lower(LeadDensityStat.city) == city.lower(),
            LeadDensityStat.vertical == vertical,
        )
    )
    if stat is not None and stat.last_count:
        anchor = min(stat.last_count, want)
        guaranteed = max(1, int(anchor * 0.8))
        low, high = anchor, min(int(anchor * 1.25), want)
    else:
        # No history: promise only a fraction of the ask, give a soft range.
        guaranteed = max(1, int(want * settings.CUSTOM_GUARANTEE_FRACTION))
        low, high = guaranteed, want
    return guaranteed, low, max(high, guaranteed)


def _preview_rows(pack: Pack) -> dict:
    sp = pack.sample_preview
    if isinstance(sp, list):
        rows = sp[:3]
    elif isinstance(sp, dict):
        rows = (sp.get("rows") or [])[:3]
    else:
        rows = []
    return {"rows": rows}


async def build_quote(
    session: AsyncSession, *, city: str, vertical_text: str, count_wanted: int | None
) -> Quote:
    """Decide catalog vs custom, compute the locked quote, persist and return it."""
    vertical = normalize_vertical(vertical_text)
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.QUOTE_TTL_MINUTES)

    pack = await match_catalog(session, city, vertical)
    if pack is not None:
        quote = Quote(
            kind="catalog",
            pack_id=pack.id,
            city=pack.city,
            vertical=pack.vertical,
            count_wanted=count_wanted,
            guaranteed_min=pack.lead_count,
            likely_low=pack.lead_count,
            likely_high=pack.lead_count,
            price_pkr=pack.price_pkr,
            preview=_preview_rows(pack),
            expires_at=expires,
        )
    else:
        guaranteed, low, high = await estimate_minimum(
            session, city, vertical, count_wanted or 0
        )
        quote = Quote(
            kind="custom",
            city=city,
            vertical=vertical,
            count_wanted=count_wanted,
            guaranteed_min=guaranteed,
            likely_low=low,
            likely_high=high,
            price_pkr=custom_price(guaranteed),
            preview={"rows": []},
            expires_at=expires,
        )
    session.add(quote)
    await session.flush()
    return quote


async def record_density(
    session: AsyncSession, city: str, vertical: str, delivered: int
) -> None:
    """Update the estimator's learning table with an actual delivered count."""
    stat = await session.scalar(
        select(LeadDensityStat).where(
            func.lower(LeadDensityStat.city) == city.lower(),
            LeadDensityStat.vertical == vertical,
        )
    )
    if stat is None:
        session.add(
            LeadDensityStat(city=city, vertical=vertical, samples=1, last_count=delivered)
        )
    else:
        stat.samples += 1
        stat.last_count = delivered
        stat.updated_at = datetime.now(timezone.utc)
