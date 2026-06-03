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
            2999,  # §15.6 target price (500 leads). LIVE pack holds 136 leads, so
            #        its DB price was set to the 136-lead rule price (1999) on
            #        2026-05-26 until the pack is topped up toward 500.
            [
                "restaurants in DHA Phase 2 Karachi",
                "restaurants in DHA Phase 5 Karachi",
                "restaurants in DHA Phase 6 Karachi",
                "restaurants in DHA Phase 8 Karachi",
                "restaurants in Khadda Market DHA Karachi",
                "restaurants in Clifton Karachi",
                "cafes in DHA Karachi",
                "cafes in Clifton Karachi",
            ],
        ),
        PackSpec(
            "karachi-dental-clinics",
            "Karachi Dental Clinics",
            "Karachi",
            "dental_clinics",
            400,
            2399,
            [
                "dental clinics in DHA Karachi",
                "dental clinics in Clifton Karachi",
                "dental clinics in Gulshan-e-Iqbal Karachi",
                "dentists in North Nazimabad Karachi",
                "orthodontists in Karachi",
            ],
        ),
        PackSpec(
            "karachi-schools-private",
            "Karachi Private Schools",
            "Karachi",
            "schools",
            600,
            3599,
            [
                "private schools in DHA Karachi",
                "private schools in Gulshan-e-Iqbal Karachi",
                "private schools in North Nazimabad Karachi",
                "schools in Clifton Karachi",
                "montessori in Karachi",
            ],
        ),
        PackSpec(
            "karachi-real-estate",
            "Karachi Real Estate Agencies",
            "Karachi",
            "real_estate",
            500,
            2999,
            [
                "real estate agencies in DHA Karachi",
                "real estate agencies in Clifton Karachi",
                "property dealers in Gulshan-e-Iqbal Karachi",
                "estate agents in Bahadurabad Karachi",
            ],
        ),
        PackSpec(
            "lahore-salons-spas",
            "Lahore Salons & Spas",
            "Lahore",
            "salons",
            750,
            4499,
            [
                "salons in DHA Lahore",
                "salons in Gulberg Lahore",
                "beauty parlours in Johar Town Lahore",
                "spas in Lahore",
                "hair salons in Model Town Lahore",
            ],
        ),
        PackSpec(
            "lahore-wedding-venues",
            "Lahore Wedding Venues & Planners",
            "Lahore",
            "wedding",
            500,
            2999,
            [
                "wedding venues in DHA Lahore",
                "marquees in Lahore",
                "banquet halls in Gulberg Lahore",
                "wedding planners in Lahore",
            ],
        ),
        PackSpec(
            "lahore-gyms-fitness",
            "Lahore Gyms & Fitness Centers",
            "Lahore",
            "gyms",
            400,
            2399,
            [
                "gyms in DHA Lahore",
                "gyms in Gulberg Lahore",
                "fitness centers in Johar Town Lahore",
                "gyms in Model Town Lahore",
            ],
        ),
        PackSpec(
            "islamabad-real-estate",
            "Islamabad Real Estate Agencies",
            "Islamabad",
            "real_estate",
            400,
            2399,
            [
                "real estate agencies in F-7 Islamabad",
                "real estate agencies in F-10 Islamabad",
                "property dealers in Bahria Town Islamabad",
                "estate agents in DHA Islamabad",
            ],
        ),
        PackSpec(
            "islamabad-medical-clinics",
            "Islamabad Medical Clinics",
            "Islamabad",
            "medical_clinics",
            500,
            2999,
            [
                "medical clinics in F-8 Islamabad",
                "clinics in Blue Area Islamabad",
                "doctors in G-11 Islamabad",
                "medical centers in F-10 Islamabad",
            ],
        ),
        PackSpec(
            "faisalabad-garment-mfg",
            "Faisalabad Garment Manufacturers",
            "Faisalabad",
            "garment_mfg",
            300,
            1999,
            [
                "garment manufacturers in Faisalabad",
                "textile manufacturers in Faisalabad",
                "clothing factories in Faisalabad",
                "apparel exporters in Faisalabad",
            ],
        ),
    ]
}
