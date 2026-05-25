"""Pydantic models for the PayPro wrapper's public surface (CLAUDE.md §7)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PayProInvoice(BaseModel):
    """Result of create_invoice."""

    invoice_id: str
    payment_url: str
    raw: dict[str, Any] = {}


class PayProInvoiceStatus(BaseModel):
    """Result of get_invoice_status, with PayPro's vocabulary classified."""

    invoice_id: str
    status: str
    is_paid: bool
    is_failed: bool
    raw: dict[str, Any] = {}


class WebhookFields(BaseModel):
    """Fields extracted from a PayPro webhook payload (names per PayPro docs)."""

    event_id: str | None = None
    event_type: str | None = None
    invoice_id: str | None = None
    status: str | None = None
