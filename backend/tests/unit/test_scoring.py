"""Wave 1 lead-scoring + signal-tag tests (leadgen_cheatsheet §3–§4)."""

from app.integrations.normalize import CANONICAL_FIELDS, normalize_place
from app.services.scoring import (
    build_sample_preview,
    compute_lead_score,
    score_and_rank,
    signal_tags,
)


def _lead(**over):
    base = {
        "name": "X",
        "phone": "+923001234567",
        "carrier": "Jazz",
        "whatsapp": True,
        "website": "https://x.com",
        "email": "owner@x.com",
        "rating": 4.6,
        "reviews_count": 40,
        "instagram": "https://instagram.com/x",
        "opening_hours": '[{"day": "Mon"}]',
        "google_place_id": "P1",
        "permanently_closed": False,
        "temporarily_closed": False,
        "claimed": True,
    }
    base.update(over)
    return base


def test_score_is_bounded_0_100():
    assert compute_lead_score(_lead()) <= 100
    assert compute_lead_score({}) == 0
    # A rich lead should score strongly.
    assert compute_lead_score(_lead()) >= 70


def test_contactability_points():
    # Phone(15)+non-generic email(15)+website(5)+social(5) = 40 contactability.
    only_contact = {
        "phone": "+923001234567",
        "email": "owner@x.com",
        "website": "https://x.com",
        "instagram": "ig",
    }
    # No rating/reviews/hours → score == contactability + maturity(website10+social10).
    assert compute_lead_score(only_contact) == 40 + 20


def test_generic_email_earns_no_email_point():
    generic = {"phone": "+923001234567", "email": "info@x.com"}
    personal = {"phone": "+923001234567", "email": "owner@x.com"}
    assert compute_lead_score(personal) - compute_lead_score(generic) == 15


def test_closed_and_no_contact_negatives():
    closed = _lead(permanently_closed=True)
    assert compute_lead_score(closed) < compute_lead_score(_lead())
    no_contact = {"rating": 5.0, "reviews_count": 10}
    # -20 for no phone AND no email pushes an otherwise-ok lead down.
    assert compute_lead_score(no_contact) == max(0, compute_lead_score({"rating": 5.0, "reviews_count": 10, "email": "a@b.com"}) - 20 - 15)


def test_duplicate_penalty():
    row = _lead()
    assert compute_lead_score(row, is_duplicate=True) == max(
        0, compute_lead_score(row) - 15
    )


def test_signal_tags_compound():
    gem = _lead(rating=4.8, reviews_count=12, website="https://x.com")
    assert "hidden_gem" in signal_tags(gem)
    assert "has_website" in signal_tags(gem)
    assert "whatsapp_reachable" in signal_tags(gem)

    chain = _lead(reviews_count=500)
    assert "major_chain" in signal_tags(chain)

    unclaimed = _lead(claimed=False)
    assert "unclaimed" in signal_tags(unclaimed)

    closed = _lead(permanently_closed=True)
    assert "closed" in signal_tags(closed)

    no_web = _lead(website=None, instagram=None, facebook=None)
    assert "no_website" in signal_tags(no_web)


def test_hidden_gem_needs_all_three_signals():
    # High rating + tiny review base but NO website → not a hidden gem.
    assert "hidden_gem" not in signal_tags(
        _lead(rating=4.9, reviews_count=8, website=None, instagram=None, facebook=None)
    )


def test_score_and_rank_sorts_and_stores_string_tags():
    rows = [
        _lead(name="weak", phone=None, email=None, website=None, whatsapp=False,
              rating=3.0, reviews_count=1, instagram=None, opening_hours=None,
              google_place_id="A"),
        _lead(name="strong", google_place_id="B"),
    ]
    ranked = score_and_rank(rows)
    assert ranked[0]["name"] == "strong"
    assert isinstance(ranked[0]["signal_tags"], str)
    assert ranked[0]["lead_score"] >= ranked[1]["lead_score"]


def test_duplicate_place_id_penalized_second():
    rows = [
        _lead(name="first", google_place_id="DUP"),
        _lead(name="second", google_place_id="DUP"),
    ]
    score_and_rank(rows)
    by_name = {r["name"]: r["lead_score"] for r in rows}
    assert by_name["first"] - by_name["second"] == 15


def test_build_sample_preview_stats():
    rows = [
        _lead(name="a", whatsapp=True, email="a@x.com"),
        _lead(name="b", whatsapp=False, email=None, rating=4.8, reviews_count=12),
        _lead(name="c", whatsapp=True, email="c@x.com", website=None, instagram=None, facebook=None),
    ]
    score_and_rank(rows)
    sp = build_sample_preview(rows)
    assert len(sp["rows"]) == 3
    stats = sp["stats"]
    assert stats["lead_count"] == 3
    assert stats["pct_whatsapp"] == 67
    assert 0 <= stats["avg_lead_score"] <= 100
    assert stats["hidden_gems"] >= 1


def test_normalize_place_emits_new_fields_including_inverted_claimed():
    raw = {
        "title": "Cafe",
        "phone": "0300-1234567",
        "claimThisBusiness": True,  # inverted → unclaimed
        "price": "$$",
        "imagesCount": 12,
        "permanentlyClosed": False,
        "twitters": ["https://twitter.com/cafe"],
    }
    out = normalize_place(raw, "2026-07-11T00:00:00+00:00")
    assert set(out) == set(CANONICAL_FIELDS)
    assert out["claimed"] is False  # claimThisBusiness True ⇒ UNCLAIMED
    assert out["whatsapp"] is True
    assert out["price_range"] == "$$"
    assert out["images_count"] == 12
    assert out["twitter"] == "https://twitter.com/cafe"
    assert out["lead_score"] is None  # set later by scoring
