"""Phase 5 custom order flow + scrape orchestration (live DB, externals stubbed)."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy import delete, select

from app.api.deps import get_paypro_client
from app.api.orders import compute_custom_amount
from app.config import settings
from app.db import SessionLocal
from app.integrations.apify import ApifyRunResult
from app.main import app
from app.models.apify_run import ApifyRun
from app.models.customer import Customer
from app.models.order import Order, OrderStatus, OrderType
from app.schemas.paypro import PayProInvoice
from app.tasks.scrape import _scrape

_EMAIL = "custom-test@leadkar.pk"


class FakePayPro:
    async def create_invoice(self, **kwargs) -> PayProInvoice:
        return PayProInvoice(invoice_id="PP_C1", payment_url="https://pay.test/PP_C1", raw={})


# ---- endpoint ----------------------------------------------------------------


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
            await s.commit()


def test_compute_custom_amount():
    assert compute_custom_amount(300) == (
        settings.CUSTOM_ORDER_BASE_PKR + settings.CUSTOM_ORDER_PER_LEAD_PKR * 300
    )


async def test_create_custom_order(client):
    body = {
        "customer": {"email": _EMAIL, "name": "C"},
        "custom_spec": {"city": "Lahore", "vertical": "salons", "target_count": 300},
    }
    r = await client.post("/api/orders/custom", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["payment_url"] == "https://pay.test/PP_C1"


async def test_custom_order_rejects_over_max(client):
    body = {
        "customer": {"email": _EMAIL, "name": "C"},
        "custom_spec": {
            "city": "Lahore", "vertical": "salons",
            "target_count": settings.MAX_LEADS_PER_CUSTOM_ORDER + 1,
        },
    }
    assert (await client.post("/api/orders/custom", json=body)).status_code == 400


# ---- scrape orchestration ----------------------------------------------------


class FakeApify:
    """Stand-in for ApifyClient; records an apify_runs row like the real one."""

    def __init__(self, session):
        self.session = session

    async def trigger_run(self, actor_id, payload, order_id=None, pack_id=None):
        run = ApifyRun(
            order_id=order_id, actor_id=actor_id, input_payload=payload,
            status="RUNNING", apify_run_id="FAKE_RUN", started_at=datetime.now(timezone.utc),
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def poll_until_complete(self, run_id, timeout):
        return ApifyRunResult(
            apify_run_id=run_id, status="SUCCEEDED", cost_usd=Decimal("1.5000"),
            dataset_id="ds1", results_count=2,
        )

    async def fetch_dataset(self, dataset_id):
        return [{"title": "Salon One"}, {"title": "Salon Two"}]


class FakeStorage:
    def __init__(self):
        self.puts = []

    def put_bytes(self, key, data, content_type):
        self.puts.append((key, content_type, len(data)))


@pytest_asyncio.fixture
async def paid_custom_order():
    async with SessionLocal() as s:
        cust = Customer(email=_EMAIL, name="C")
        s.add(cust)
        await s.flush()
        order = Order(
            customer_id=cust.id, order_type=OrderType.custom, status=OrderStatus.paid,
            amount_pkr=7399, idempotency_key=str(uuid.uuid4()),
            custom_spec={"city": "Lahore", "vertical": "salons", "target_count": 300},
        )
        s.add(order)
        await s.commit()
        ids = (order.id, cust.id)
    yield ids
    async with SessionLocal() as s:
        oid, cid = ids
        await s.execute(delete(ApifyRun).where(ApifyRun.order_id == oid))
        await s.execute(delete(Order).where(Order.id == oid))
        await s.execute(delete(Customer).where(Customer.id == cid))
        await s.commit()


async def test_scrape_writes_files_and_enqueues_deliver(paid_custom_order, monkeypatch):
    order_id, _ = paid_custom_order
    storage = FakeStorage()
    sent = []
    monkeypatch.setattr(
        "app.tasks.scrape.celery_app.send_task",
        lambda name, args=None, **kw: sent.append((name, args)),
    )

    result = await _scrape(order_id, make_apify=lambda s: FakeApify(s), storage=storage)
    assert result == "scraped"
    # CSV + XLSX written to the order's S3 prefix.
    keys = {k for k, _, _ in storage.puts}
    assert keys == {f"orders/{order_id}/leads.csv", f"orders/{order_id}/leads.xlsx"}
    # deliver_order enqueued.
    assert sent == [("deliver_order", [str(order_id)])]

    async with SessionLocal() as s:
        order = await s.get(Order, order_id)
        assert order.delivery_s3_csv == f"orders/{order_id}/leads.csv"
        run = await s.scalar(select(ApifyRun).where(ApifyRun.order_id == order_id))
        assert run.cost_usd == Decimal("1.5000")
        assert run.results_count == 2
