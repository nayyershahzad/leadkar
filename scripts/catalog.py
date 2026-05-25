"""Initial 10-pack catalog (CLAUDE.md §10).

Single source of truth shared by the Phase 3 refresh CLI and the Phase 7 seeder.
``search_strings`` drive the Apify Google-Maps actor; ``lead_count`` is the target
result count, divided across the search strings as the per-search cap.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PackSpec:
    slug: str
    title: str
    city: str
    vertical: str
    lead_count: int
    price_pkr: int
    search_strings: list[str]


CATALOG: dict[str, PackSpec] = {
    p.slug: p
    for p in [
        PackSpec(
            "karachi-restaurants-dha",
            "Karachi Restaurants (DHA + Clifton)",
            "Karachi",
            "restaurants",
            500,
            3999,
            ["restaurants in DHA Karachi", "restaurants in Clifton Karachi"],
        ),
        PackSpec(
            "karachi-dental-clinics",
            "Karachi Dental Clinics",
            "Karachi",
            "dental_clinics",
            400,
            3999,
            ["dental clinics in Karachi"],
        ),
        PackSpec(
            "karachi-schools-private",
            "Karachi Private Schools",
            "Karachi",
            "schools",
            600,
            4499,
            ["private schools in Karachi"],
        ),
        PackSpec(
            "karachi-real-estate",
            "Karachi Real Estate Agencies",
            "Karachi",
            "real_estate",
            500,
            4499,
            ["real estate agencies in Karachi"],
        ),
        PackSpec(
            "lahore-salons-spas",
            "Lahore Salons & Spas",
            "Lahore",
            "salons",
            750,
            4999,
            ["salons in Lahore", "spas in Lahore"],
        ),
        PackSpec(
            "lahore-wedding-venues",
            "Lahore Wedding Venues & Planners",
            "Lahore",
            "wedding",
            500,
            5499,
            ["wedding venues in Lahore", "wedding planners in Lahore"],
        ),
        PackSpec(
            "lahore-gyms-fitness",
            "Lahore Gyms & Fitness Centers",
            "Lahore",
            "gyms",
            400,
            3999,
            ["gyms in Lahore", "fitness centers in Lahore"],
        ),
        PackSpec(
            "islamabad-real-estate",
            "Islamabad Real Estate Agencies",
            "Islamabad",
            "real_estate",
            400,
            3999,
            ["real estate agencies in Islamabad"],
        ),
        PackSpec(
            "islamabad-medical-clinics",
            "Islamabad Medical Clinics",
            "Islamabad",
            "medical_clinics",
            500,
            4499,
            ["medical clinics in Islamabad"],
        ),
        PackSpec(
            "faisalabad-garment-mfg",
            "Faisalabad Garment Manufacturers",
            "Faisalabad",
            "garment_mfg",
            300,
            5999,
            ["garment manufacturers in Faisalabad"],
        ),
    ]
}
