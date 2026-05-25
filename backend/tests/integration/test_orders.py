"""Phase 4 catalog order flow — against the real DB with PayPro stubbed."""

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy import delete, select

from app.api.deps import get_paypro_client
from app.db import SessionLocal
from app.main import app
from app.models.customer import Customer
from app.models.order import Order
from app.models.pack import Pack
from app.schemas.paypro import PayProInvoice

_SLUG = "phase4-test-pack"
_EMAIL = "phase4test@leadkar.pk"


class FakePayPro:
    async def create_invoice(self, **kwargs) -> PayProInvoice:
        return PayProInvoice(
            invoice_id="PP_TEST_1", payment_url="https://pay.test/PP_TEST_1", raw={}
        )


async def _cleanup(pack_id):
    async with SessionLocal() as s:
        cust = await s.scalar(select(Customer).where(Customer.email == _EMAIL))
        if cust:
            await s.execute(delete(Order).where(Order.customer_id == cust.id))
        await s.execute(delete(Pack).where(Pack.id == pack_id))
        await s.execute(delete(Customer).where(Customer.email == _EMAIL))
        await s.commit()


@pytest_asyncio.fixture
async def client():
    async with SessionLocal() as s:
        pack = Pack(
            slug=_SLUG, title="Phase4 Test Pack", city="Karachi",
            vertical="restaurants", lead_count=10, price_pkr=3999, is_active=True,
        )
        s.add(pack)
        await s.commit()
        await s.refresh(pack)
        pack_id = pack.id

    app.dependency_overrides[get_paypro_client] = lambda: FakePayPro()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    await _cleanup(pack_id)


async def test_list_and_detail(client):
    r = await client.get("/api/packs")
    assert r.status_code == 200
    assert any(p["slug"] == _SLUG for p in r.json())

    r = await client.get(f"/api/packs/{_SLUG}")
    assert r.status_code == 200 and r.json()["price_pkr"] == 3999

    assert (await client.get("/api/packs/does-not-exist")).status_code == 404


async def test_create_catalog_order_returns_payment_url(client):
    body = {
        "pack_slug": _SLUG,
        "customer": {"email": _EMAIL, "name": "Phase Four", "phone": "03001234567"},
    }
    r = await client.post("/api/orders/catalog", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["payment_url"] == "https://pay.test/PP_TEST_1"
    assert data["status"] == "pending"


async def test_create_catalog_order_is_idempotent(client):
    body = {
        "pack_slug": _SLUG,
        "customer": {"email": _EMAIL, "name": "Phase Four"},
        "idempotency_key": "fixed-key-abc",
    }
    r1 = await client.post("/api/orders/catalog", json=body)
    r2 = await client.post("/api/orders/catalog", json=body)
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["order_id"] == r2.json()["order_id"]


async def test_unknown_pack_404(client):
    body = {"pack_slug": "nope", "customer": {"email": _EMAIL, "name": "X"}}
    assert (await client.post("/api/orders/catalog", json=body)).status_code == 404
