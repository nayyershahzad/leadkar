"""Shared API dependencies."""

from __future__ import annotations

from app.integrations.llm import GroqClient
from app.integrations.paypro import PayProClient


def get_paypro_client() -> PayProClient:
    """Injectable PayPro client (overridable in tests)."""
    return PayProClient()


def get_groq_client() -> GroqClient:
    """Injectable Groq client (overridable in tests)."""
    return GroqClient()
