"""Phase 9 conversational quoting (live DB, Groq + PayPro stubbed).

Critical guardrail under test: the LLM never originates money — the order amount
always equals the server-issued quote price, regardless of what the client sends.
"""

import uuid

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy import delete, select

from app.api.deps import get_groq_client, get_paypro_client
from app.config import settings
from app.db import SessionLocal
from app.integrations.llm import Intent
from app.main import app
from app.models.customer import Customer
from app.models.order import Order
from app.models.quote import Quote
from app.schemas.paypro import PayProInvoice
from app.services.quoting import (
    build_quote,
    catalog_price,
    custom_price,
    normalize_vertical,
    round_to_x99,
)

_EMAIL = "assistant-test@leadkar.pk"


class FakePayPro:
    async def create_invoice(self, **kwargs) -> PayProInvoice:
        # Echo the amount so tests can assert it came from the quote, not the client.
        return PayProInvoice(
            invoice_id="PP_A1",
            payment_url=f"https://pay.test/{kwargs['amount_pkr']}",
            raw={},
        )


class FakeGroq:
    """Stand-in Groq that is 'configured' and returns a fixed ready intent."""

    def __init__(self, intent: Intent):
        self._intent = intent

    @property
    def is_configured(self) -> bool:
        return True

    async def chat(self, messages):
        return self._intent


# ---- pure functions ----------------------------------------------------------


def test_normalize_vertical():
    assert normalize_vertical("nice coffee shop") == "restaurants"
    assert normalize_vertical("property dealers") == "real_estate"
    assert normalize_vertical("beauty parlour") == "salons"
    assert normalize_vertical("widget makers") == "widget_makers"  # slugified fallback


def test_round_and_prices():
    assert round_to_x99(2000) == 1999
    assert round_to_x99(2400) == 2399
    assert catalog_price(300) == settings.CATALOG_MIN_PRICE_PKR  # floor kicks in
    assert catalog_price(750) == 4499
    assert custom_price(120) == settings.CUSTOM_ORDER_BASE_PKR + settings.CUSTOM_ORDER_PER_LEAD_PKR * 120


# ---- build_quote (DB) --------------------------------------------------------


async def test_build_quote_catalog_match():
    async with SessionLocal() as s:
        q = await build_quote(s, city="Karachi", vertical_text="restaurants", count_wanted=300)
        assert q.kind == "catalog"
        assert q.price_pkr == 2999
        assert len((q.preview or {}).get("rows", [])) > 0
        await s.rollback()


async def test_build_quote_custom_guarantee():
    async with SessionLocal() as s:
        q = await build_quote(s, city="Multan", vertical_text="gyms", count_wanted=200)
        assert q.kind == "custom"
        assert q.guaranteed_min == int(200 * settings.CUSTOM_GUARANTEE_FRACTION)
        assert q.price_pkr == custom_price(q.guaranteed_min)
        await s.rollback()


# ---- endpoints ---------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_paypro_client] = lambda: FakePayPro()
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    async with SessionLocal() as s:
        cust = await s.scalar(select(Customer).where(Customer.email == _EMAIL))
        if cust:
            await s.execute(delete(Order).where(Order.customer_id == cust.id))
            await s.execute(delete(Customer).where(Customer.id == cust.id))
        await s.execute(delete(Quote).where(Quote.city == "Multan"))
        await s.commit()


async def test_chat_disabled_without_key(client):
    # Default get_groq_client → real client with no key → enabled:false.
    r = await client.post(
        "/api/assistant/chat", json={"messages": [{"role": "user", "content": "hi"}]}
    )
    assert r.status_code == 200
    assert r.json() == {"enabled": False, "reply": "", "quote": None}


async def test_chat_returns_quote_when_ready(client):
    intent = Intent(reply="Here's a quote!", city="Multan", vertical="gyms",
                    count_wanted=200, ready=True)
    app.dependency_overrides[get_groq_client] = lambda: FakeGroq(intent)
    r = await client.post(
        "/api/assistant/chat",
        json={"messages": [{"role": "user", "content": "200 gyms in Multan"}]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["quote"]["kind"] == "custom"
    assert body["quote"]["price_pkr"] == custom_price(int(200 * settings.CUSTOM_GUARANTEE_FRACTION))


async def test_accept_uses_quote_price_not_client(client):
    # Build a quote directly, then accept it; the order amount must equal the
    # quote price even though the client body carries no price at all.
    async with SessionLocal() as s:
        q = await build_quote(s, city="Multan", vertical_text="gyms", count_wanted=200)
        await s.commit()
        quote_id, quote_price = q.id, q.price_pkr

    r = await client.post(
        f"/api/assistant/quote/{quote_id}/accept",
        json={"customer": {"email": _EMAIL, "name": "A"}},
    )
    assert r.status_code == 200, r.text
    # FakePayPro encodes the amount it was called with into the URL.
    assert r.json()["payment_url"] == f"https://pay.test/{quote_price}"

    async with SessionLocal() as s:
        order = await s.scalar(select(Order).where(Order.quote_id == quote_id))
        assert order is not None
        assert order.amount_pkr == quote_price
        assert order.guaranteed_min_leads == int(200 * settings.CUSTOM_GUARANTEE_FRACTION)
        used = await s.get(Quote, quote_id)
        assert used.status == "accepted"


async def test_accept_rejects_reused_quote(client):
    async with SessionLocal() as s:
        q = await build_quote(s, city="Multan", vertical_text="gyms", count_wanted=200)
        q.status = "accepted"
        await s.commit()
        quote_id = q.id
    r = await client.post(
        f"/api/assistant/quote/{quote_id}/accept",
        json={"customer": {"email": _EMAIL, "name": "A"}},
    )
    assert r.status_code == 409


async def test_accept_unknown_quote_404(client):
    r = await client.post(
        f"/api/assistant/quote/{uuid.uuid4()}/accept",
        json={"customer": {"email": _EMAIL, "name": "A"}},
    )
    assert r.status_code == 404
