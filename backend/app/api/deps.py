"""Shared API dependencies."""

from __future__ import annotations

from app.integrations.paypro import PayProClient


def get_paypro_client() -> PayProClient:
    """Injectable PayPro client (overridable in tests)."""
    return PayProClient()
