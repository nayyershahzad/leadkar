"""PayPro v2 integration wrapper (CLAUDE.md §7).

ALL PayPro-specific details live in this module so the rest of the app never
touches PayPro's vocabulary. The exact endpoint paths, request/response field
names, signature header, and signing scheme are NOT given in CLAUDE.md (§14 open
questions) — they are isolated in the clearly-marked block below and must be
confirmed against the official PayPro v2 docs before going live.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
from typing import Any

import httpx
from loguru import logger
from redis.asyncio import Redis

from app.config import settings
from app.schemas.paypro import PayProInvoice, PayProInvoiceStatus, WebhookFields

# ============================================================================
# >>> PAYPRO API SPECIFICS — CONFIRM AGAINST PAYPRO v2 DOCS (CLAUDE.md §14) <<<
# These are best-guess placeholders. When Nayyer provides the PayPro v2 docs,
# update *only* this block; the rest of the app is insulated from it.
# ----------------------------------------------------------------------------
TOKEN_PATH = "/auth/token"  # TODO(§14): confirm OAuth token endpoint
CREATE_INVOICE_PATH = "/invoices"  # TODO(§14): confirm invoice-create endpoint
INVOICE_STATUS_PATH = "/invoices/{invoice_id}"  # TODO(§14): confirm status endpoint

# Response field names.
F_ACCESS_TOKEN = "access_token"  # TODO(§14)
F_EXPIRES_IN = "expires_in"  # TODO(§14)
F_INVOICE_ID = "id"  # TODO(§14)
F_PAYMENT_URL = "payment_url"  # TODO(§14)
F_STATUS = "status"  # TODO(§14)

# Webhook payload field names + signature header.
WH_EVENT_ID = "event_id"  # TODO(§14)
WH_EVENT_TYPE = "event_type"  # TODO(§14)
WH_INVOICE_ID = "invoice_id"  # TODO(§14)
WH_STATUS = "status"  # TODO(§14)
SIGNATURE_HEADER = "x-paypro-signature"  # TODO(§14): confirm header name

# Status vocabulary. TODO(§14): confirm PayPro's exact terminal status strings.
PAID_STATUSES = {"paid", "success", "completed", "successful"}
FAILED_STATUSES = {"failed", "cancelled", "canceled", "expired", "declined"}
# ============================================================================

_TOKEN_KEY = "paypro:access_token"
_LOCK_KEY = "paypro:access_token:lock"


class PayProError(RuntimeError):
    """Generic PayPro failure (non-2xx, malformed response, etc.)."""


class PayProAuthError(PayProError):
    """PayPro returned 401/403."""


class PayProTimeout(PayProError):
    """PayPro request timed out."""


def classify_status(status: str | None) -> tuple[bool, bool]:
    """Map a PayPro status string to (is_paid, is_failed)."""
    s = (status or "").strip().lower()
    return (s in PAID_STATUSES, s in FAILED_STATUSES)


def extract_webhook_fields(payload: dict[str, Any]) -> WebhookFields:
    """Pull the fields we care about out of a PayPro webhook body."""
    return WebhookFields(
        event_id=payload.get(WH_EVENT_ID),
        event_type=payload.get(WH_EVENT_TYPE),
        invoice_id=payload.get(WH_INVOICE_ID),
        status=payload.get(WH_STATUS),
    )


class PayProClient:
    """Async PayPro v2 client with Redis-cached OAuth token (CLAUDE.md §7)."""

    def __init__(
        self,
        *,
        redis_client: Redis | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._redis = redis_client or Redis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
        self._http = http_client

    # ---- HTTP plumbing -----------------------------------------------------

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        timeout = settings.PAYPRO_TIMEOUT_SECONDS
        try:
            if self._http is not None:
                resp = await self._http.request(method, url, timeout=timeout, **kwargs)
            else:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            raise PayProTimeout(f"PayPro request timed out: {method} {url}") from exc

        if resp.status_code in (401, 403):
            raise PayProAuthError(f"PayPro auth failed ({resp.status_code})")
        if resp.status_code >= 400:
            raise PayProError(
                f"PayPro error {resp.status_code}: {resp.text[:300]}"
            )
        return resp

    def _url(self, path: str) -> str:
        return settings.PAYPRO_API_BASE_URL.rstrip("/") + path

    # ---- Token caching (CLAUDE.md §7) --------------------------------------

    async def _fetch_token(self) -> tuple[str, int]:
        resp = await self._request(
            "POST",
            self._url(TOKEN_PATH),
            json={
                "client_id": settings.PAYPRO_CLIENT_ID,
                "client_secret": settings.PAYPRO_CLIENT_SECRET,
                "grant_type": "client_credentials",
            },
        )
        data = resp.json()
        token = data.get(F_ACCESS_TOKEN)
        if not token:
            raise PayProError("PayPro token response missing access token")
        return token, int(data.get(F_EXPIRES_IN, 3600))

    async def get_access_token(self) -> str:
        """Return a cached or freshly-minted token. Redis TTL = expires_in - 60s.

        Uses SET NX EX as a refresh lock to avoid a thundering herd of token
        requests when the cache is cold.
        """
        cached = await self._redis.get(_TOKEN_KEY)
        if cached:
            return cached

        got_lock = await self._redis.set(_LOCK_KEY, "1", nx=True, ex=30)
        if not got_lock:
            # Another worker is refreshing — wait briefly for it to populate.
            for _ in range(20):
                await asyncio.sleep(0.25)
                cached = await self._redis.get(_TOKEN_KEY)
                if cached:
                    return cached

        try:
            token, expires_in = await self._fetch_token()
            ttl = max(expires_in - 60, 30)
            await self._redis.set(_TOKEN_KEY, token, ex=ttl)
            return token
        finally:
            await self._redis.delete(_LOCK_KEY)

    async def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {await self.get_access_token()}"}

    # ---- Invoices (CLAUDE.md §7) -------------------------------------------

    async def create_invoice(
        self,
        *,
        order_id: Any,
        amount_pkr: int,
        customer_email: str,
        customer_name: str,
        customer_phone: str | None,
        description: str,
        return_url: str,
        cancel_url: str,
    ) -> PayProInvoice:
        """Create a PayPro invoice and return its id + hosted payment URL."""
        payload = {
            # TODO(§14): map to PayPro's exact request schema.
            "order_id": str(order_id),
            "amount": amount_pkr,
            "currency": "PKR",
            "customer_email": customer_email,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "description": description,
            "return_url": return_url,
            "cancel_url": cancel_url,
        }
        resp = await self._request(
            "POST",
            self._url(CREATE_INVOICE_PATH),
            json=payload,
            headers=await self._auth_headers(),
        )
        data = resp.json()
        invoice_id = data.get(F_INVOICE_ID)
        payment_url = data.get(F_PAYMENT_URL)
        if not invoice_id or not payment_url:
            raise PayProError("PayPro invoice response missing id/payment_url")
        return PayProInvoice(invoice_id=str(invoice_id), payment_url=payment_url, raw=data)

    async def get_invoice_status(self, invoice_id: str) -> PayProInvoiceStatus:
        """Fetch an invoice's status — the reconciliation backup path."""
        resp = await self._request(
            "GET",
            self._url(INVOICE_STATUS_PATH.format(invoice_id=invoice_id)),
            headers=await self._auth_headers(),
        )
        data = resp.json()
        status = data.get(F_STATUS)
        is_paid, is_failed = classify_status(status)
        return PayProInvoiceStatus(
            invoice_id=invoice_id,
            status=str(status),
            is_paid=is_paid,
            is_failed=is_failed,
            raw=data,
        )

    # ---- Webhook signature (CLAUDE.md §7) ----------------------------------

    def verify_webhook_signature(
        self, raw_body: bytes, headers: dict[str, str]
    ) -> bool:
        """HMAC-SHA256 verification of the raw request body.

        TODO(§14): confirm the signing scheme. If PayPro uses RSA or a different
        digest, replace this body — callers only depend on the bool return.
        Fails closed: no secret or missing/invalid signature -> False.
        """
        secret = settings.PAYPRO_WEBHOOK_SECRET
        if not secret:
            logger.warning("PAYPRO_WEBHOOK_SECRET not set; rejecting webhook")
            return False

        # Header lookup is case-insensitive.
        provided = ""
        for key, value in headers.items():
            if key.lower() == SIGNATURE_HEADER:
                provided = value.strip()
                break
        if not provided:
            return False

        expected = hmac.new(
            secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        # Tolerate "sha256=" prefixes some providers use.
        provided_norm = provided.split("=", 1)[-1] if "=" in provided else provided
        return hmac.compare_digest(expected, provided_norm.lower())
