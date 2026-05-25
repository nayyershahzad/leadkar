import json

from app.integrations.normalize import (
    CANONICAL_FIELDS,
    normalize_phone_pk,
    normalize_place,
)


def test_phone_local_mobile_to_e164_with_carrier():
    assert normalize_phone_pk("0300-1234567") == ("+923001234567", "Jazz")
    assert normalize_phone_pk("0311 1234567") == ("+923111234567", "Zong")
    assert normalize_phone_pk("0331234567 8".replace(" ", "")) == ("+923312345678", "Ufone")
    assert normalize_phone_pk("03412345678") == ("+923412345678", "Telenor")
    assert normalize_phone_pk("03512345678") == ("+923512345678", "SCOM")
    assert normalize_phone_pk("03212345678") == ("+923212345678", "Warid (now Jazz)")


def test_phone_already_e164_and_passthrough():
    assert normalize_phone_pk("+923001234567") == ("+923001234567", "Jazz")
    # Landline / non-mobile is left as-is with no carrier.
    assert normalize_phone_pk("021-35840000") == ("021-35840000", None)
    assert normalize_phone_pk(None) == (None, None)
    assert normalize_phone_pk("") == (None, None)


def test_normalize_place_maps_canonical_fields():
    raw = {
        "title": "Kolachi",
        "categoryName": "Restaurant",
        "address": "Do Darya, Karachi",
        "city": "Karachi",
        "phone": "0300-1234567",
        "website": "https://kolachi.com",
        "totalScore": 4.5,
        "reviewsCount": 1200,
        "location": {"lat": 24.79, "lng": 67.05},
        "placeId": "ChIJabc",
        "instagrams": ["https://instagram.com/kolachi"],
        "facebooks": ["https://facebook.com/kolachi"],
        "openingHours": [{"day": "Monday", "hours": "12-12"}],
    }
    out = normalize_place(raw, "2026-05-25T00:00:00+00:00")

    assert set(out) == set(CANONICAL_FIELDS)
    assert out["name"] == "Kolachi"
    assert out["category"] == "Restaurant"
    assert out["phone"] == "+923001234567"
    assert out["carrier"] == "Jazz"
    assert out["lat"] == 24.79 and out["lng"] == 67.05
    assert out["google_place_id"] == "ChIJabc"
    assert out["instagram"] == "https://instagram.com/kolachi"
    assert out["facebook"] == "https://facebook.com/kolachi"
    assert out["email"] is None  # enrichment is a later phase
    assert out["source"] == "google_maps"
    assert json.loads(out["opening_hours"])[0]["day"] == "Monday"


def test_normalize_place_handles_missing_fields():
    out = normalize_place({"title": "X"}, "2026-05-25T00:00:00+00:00")
    assert out["name"] == "X"
    assert out["city"] == ""
    assert out["phone"] is None and out["carrier"] is None
    assert out["lat"] is None and out["lng"] is None
    assert out["instagram"] is None
    assert out["opening_hours"] is None
