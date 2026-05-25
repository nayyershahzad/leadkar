"""Manual PayPro smoke test (CLAUDE.md §9 Phase 2 acceptance).

Creates a throwaway customer + pending order, calls PayPro create_invoice, and
prints the payment URL. Requires real/sandbox PayPro credentials in .env
(PAYPRO_CLIENT_ID/SECRET/API_BASE_URL) — it will refuse to run without them.

    python scripts/smoke_paypro.py --amount 3999 --email you@example.com
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.db import SessionLocal
from app.integrations.paypro import PayProClient
from app.models.customer import Customer
from app.models.order import Order, OrderType
from sqlalchemy import select


async def run(amount: int, email: str) -> int:
    missing = [
        name
        for name in ("PAYPRO_CLIENT_ID", "PAYPRO_CLIENT_SECRET", "PAYPRO_API_BASE_URL")
        if not getattr(settings, name)
    ]
    if missing:
        print(f"ERROR: missing PayPro config: {', '.join(missing)} (see §14).")
        return 1

    async with SessionLocal() as session:
        customer = await session.scalar(select(Customer).where(Customer.email == email))
        if customer is None:
            customer = Customer(email=email, name="Smoke Test")
            session.add(customer)
            await session.flush()

        order = Order(
            customer_id=customer.id,
            order_type=OrderType.catalog,
            amount_pkr=amount,
            idempotency_key=str(uuid.uuid4()),
        )
        session.add(order)
        await session.flush()

        invoice = await PayProClient().create_invoice(
            order_id=order.id,
            amount_pkr=amount,
            customer_email=email,
            customer_name=customer.name or "Customer",
            customer_phone=None,
            description="LeadKar smoke test",
            return_url=settings.PAYPRO_RETURN_URL,
            cancel_url=settings.PAYPRO_CANCEL_URL,
        )
        order.paypro_invoice_id = invoice.invoice_id
        order.paypro_invoice_url = invoice.payment_url
        await session.commit()

    print(f"Order:       {order.id}")
    print(f"Invoice ID:  {invoice.invoice_id}")
    print(f"Payment URL: {invoice.payment_url}")
    print("Open the payment URL, pay in sandbox, then confirm the webhook flips")
    print("the order to 'paid'.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="PayPro create_invoice smoke test.")
    parser.add_argument("--amount", type=int, default=3999)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.amount, args.email)))


if __name__ == "__main__":
    main()
