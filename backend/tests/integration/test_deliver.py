"""Phase 4 deliver_order task — against the real DB with S3/mailer stubbed."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.db import SessionLocal
from app.models.customer import Customer
from app.models.order import Order, OrderStatus, OrderType
from app.models.pack import Pack
from app.tasks.deliver import _deliver

_EMAIL = "deliver-test@leadkar.pk"


class FakeStorage:
    def presign_get(self, key, expires_seconds=None):
        return f"https://s3.test/{key}?sig=abc"


class FakeMailer:
    def __init__(self):
        self.sent = []

    def send(self, *, to, subject, html, text):
        self.sent.append({"to": to, "subject": subject, "html": html})


@pytest_asyncio.fixture
async def paid_order():
    async with SessionLocal() as s:
        pack = Pack(
            slug=f"deliver-pack-{uuid.uuid4().hex[:8]}", title="Deliver Pack",
            city="Lahore", vertical="salons", lead_count=10, price_pkr=4999,
            is_active=True, s3_key_csv="packs/x.csv", s3_key_xlsx="packs/x.xlsx",
        )
        cust = Customer(email=_EMAIL, name="Deliver Tester")
        s.add_all([pack, cust])
        await s.flush()
        order = Order(
            customer_id=cust.id, pack_id=pack.id, order_type=OrderType.catalog,
            status=OrderStatus.paid, amount_pkr=4999, idempotency_key=str(uuid.uuid4()),
        )
        s.add(order)
        await s.commit()
        ids = (order.id, pack.id, cust.id)
    yield ids
    async with SessionLocal() as s:
        oid, pid, cid = ids
        await s.execute(delete(Order).where(Order.id == oid))
        await s.execute(delete(Pack).where(Pack.id == pid))
        await s.execute(delete(Customer).where(Customer.id == cid))
        await s.commit()


async def test_deliver_marks_delivered_and_emails(paid_order):
    order_id, _, _ = paid_order
    mailer = FakeMailer()
    result = await _deliver(order_id, storage=FakeStorage(), mailer=mailer)

    assert result == "delivered"
    assert len(mailer.sent) == 1
    assert mailer.sent[0]["to"] == _EMAIL
    assert "s3.test/packs/x.csv" in mailer.sent[0]["html"]

    async with SessionLocal() as s:
        order = await s.get(Order, order_id)
        assert order.status == OrderStatus.delivered
        assert order.delivered_at is not None
        assert order.delivery_s3_csv == "packs/x.csv"


async def test_deliver_is_idempotent(paid_order):
    order_id, _, _ = paid_order
    mailer = FakeMailer()
    assert await _deliver(order_id, storage=FakeStorage(), mailer=mailer) == "delivered"
    # Second run must not re-send or re-deliver.
    assert await _deliver(order_id, storage=FakeStorage(), mailer=mailer) == "already_delivered"
    assert len(mailer.sent) == 1
