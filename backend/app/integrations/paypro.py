"""PayPro Pakistan v2 integration wrapper (CLAUDE.md §7).

Reconciled against the official PayPro v2 Postman collection. PayPro PK does NOT
sign webhooks, so per Nayyer's decision (2026-05-25) we never trust a callback
body: payment is confirmed only by a server-to-server status query (ggosboi).
All PayPro-specific details remain isolated in this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
from loguru import logger
from redis.asyncio import Redis

from app.config import settings
from app.schemas.paypro import PayProInvoice, PayProInvoiceStatus

# ============================================================================
# PAYPRO v2 API SPECIFICS (confirmed from the official Postman collection).
# demo base: https://demoapi.paypro.com.pk   live base: https://api.paypro.com.pk
# ----------------------------------------------------------------------------
AUTH_PATH = "/v2/ppro/auth"          # POST {clientid, clientsecret}; token in header
CREATE_ORDER_PATH = "/v2/ppro/co"    # POST [ {MerchantId}, {order...} ]; header token
ORDER_STATUS_PATH = "/v2/ppro/ggosboi"  # POST {userName, Order_Id}; header Token

TOKEN_HEADER = "token"               # response header carrying the auth token

# Create-order response fields (2nd element of the response array).
F_CLICK2PAY = "Click2Pay"            # hosted payment URL
F_PAYPRO_ID = "PayProId"             # PayPro's order id -> our paypro_invoice_id

# Status (ggosboi) response field + values.
F_ORDER_STATUS = "OrderStatus"
PAID_STATUSES = {"paid"}
FAILED_STATUSES = {"blocked", "expired", "cancelled", "canceled"}

# PayPro envelope status: element 0 is {"Status": "00"} on success.
F_ENVELOPE_STATUS = "Status"
OK_STATUS = "00"
# TODO(confirm on first sandbox order): no PKR example in the docs — we send
# Currency=PKR, IsConverted=false, amount in CurrencyAmount.
ORDER_TYPE = "Service"
# ============================================================================

_TOKEN_KEY = "paypro:access_token"
_LOCK_KEY = "paypro:access_token:lock"


class PayProError(RuntimeError):
    """Generic PayPro failure (non-2xx, non-'00' envelope, malformed response)."""


class PayProAuthError(PayProError):
    """PayPro returned 401/403 (token rejected/expired)."""


class PayProTimeout(PayProError):
    """PayPro request timed out."""


def classify_status(order_status: str | None) -> tuple[bool, bool]:
    """Map a PayPro OrderStatus to (is_paid, is_failed)."""
    s = (order_status or "").strip().lower()
    return (s in PAID_STATUSES, s in FAILED_STATUSES)


def _envelope(payload: Any) -> tuple[bool, dict[str, Any]]:
    """PayPro responses are arrays: [{"Status": "00"}, {data...}].

    Returns (ok, data_dict).
    """
    if isinstance(payload, list) and payload:
        status = str(payload[0].get(F_ENVELOPE_STATUS, "")) if isinstance(payload[0], dict) else ""
        data = payload[1] if len(payload) > 1 and isinstance(payload[1], dict) else {}
        return status == OK_STATUS, data
    if isinstance(payload, dict):
        return str(payload.get(F_ENVELOPE_STATUS, "")) == OK_STATUS, payload
    return False, {}


def _ddmmyyyy(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y")


class PayProClient:
    """Async PayPro v2 client with Redis-cached token (CLAUDE.md §7)."""

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

    def _url(self, path: str) -> str:
        return settings.PAYPRO_API_BASE_URL.rstrip("/") + path

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
            raise PayProError(f"PayPro error {resp.status_code}: {resp.text[:300]}")
        return resp

    # ---- Token caching (CLAUDE.md §7) --------------------------------------

    async def _fetch_token(self) -> str:
        resp = await self._request(
            "POST",
            self._url(AUTH_PATH),
            json={
                "clientid": settings.PAYPRO_CLIENT_ID,
                "clientsecret": settings.PAYPRO_CLIENT_SECRET,
            },
        )
        # Token is returned in a response header (case-insensitive lookup).
        token = resp.headers.get(TOKEN_HEADER) or resp.headers.get(TOKEN_HEADER.title())
        if not token:
            raise PayProError("PayPro auth response missing token header")
        return token

    async def get_access_token(self) -> str:
        """Return a cached or fresh token. PayPro documents no expiry, so we cache
        for PAYPRO_TOKEN_TTL_SECONDS and additionally refresh-on-401 (see _authed).
        SET NX EX is used as a refresh lock to avoid a thundering herd.
        """
        cached = await self._redis.get(_TOKEN_KEY)
        if cached:
            return cached

        got_lock = await self._redis.set(_LOCK_KEY, "1", nx=True, ex=30)
        if not got_lock:
            for _ in range(20):
                import asyncio

                await asyncio.sleep(0.25)
                cached = await self._redis.get(_TOKEN_KEY)
                if cached:
                    return cached
        try:
            token = await self._fetch_token()
            await self._redis.set(_TOKEN_KEY, token, ex=settings.PAYPRO_TOKEN_TTL_SECONDS)
            return token
        finally:
            await self._redis.delete(_LOCK_KEY)

    async def _authed(self, method: str, path: str, body: Any) -> Any:
        """Token-authenticated request that refreshes once on auth failure."""
        token = await self.get_access_token()
        try:
            resp = await self._request(
                method, self._url(path), json=body, headers={TOKEN_HEADER: token}
            )
        except PayProAuthError:
            await self._redis.delete(_TOKEN_KEY)
            token = await self.get_access_token()
            resp = await self._request(
                method, self._url(path), json=body, headers={TOKEN_HEADER: token}
            )
        return resp.json()

    # ---- Orders (CLAUDE.md §7) ---------------------------------------------

    async def create_invoice(
        self,
        *,
        order_id: UUID | str,
        amount_pkr: int,
        customer_email: str,
        customer_name: str,
        customer_phone: str | None,
        description: str,
        return_url: str | None = None,  # PayPro PK has no per-order return/cancel
        cancel_url: str | None = None,  # URLs; configured at the dashboard level.
    ) -> PayProInvoice:
        """Create a PayPro order (/v2/ppro/co). OrderNumber = our order_id."""
        now = datetime.now(timezone.utc)
        order_number = str(order_id)
        merchant_id = settings.PAYPRO_MERCHANT_ID or settings.PAYPRO_USERNAME
        body = [
            {"MerchantId": merchant_id},
            {
                "OrderNumber": order_number,
                "CurrencyAmount": str(amount_pkr),
                "Currency": "PKR",
                "IsConverted": "false",
                "OrderType": ORDER_TYPE,
                "IssueDate": _ddmmyyyy(now),
                "OrderDueDate": _ddmmyyyy(now + timedelta(days=settings.PAYPRO_ORDER_DUE_DAYS)),
                "OrderExpireAfterSeconds": "0",
                "CustomerName": customer_name,
                "CustomerMobile": customer_phone or "",
                "CustomerEmail": customer_email,
                "CustomerAddress": "",
            },
        ]
        data = await self._authed("POST", CREATE_ORDER_PATH, body)
        ok, fields = _envelope(data)
        if not ok:
            raise PayProError(f"PayPro create order failed: {data}")

        invoice_id = fields.get(F_PAYPRO_ID)
        payment_url = fields.get(F_CLICK2PAY)
        if not invoice_id or not payment_url:
            raise PayProError(f"PayPro response missing PayProId/Click2Pay: {fields}")
        return PayProInvoice(invoice_id=str(invoice_id), payment_url=payment_url, raw=fields)

    async def get_invoice_status(self, order_number: str) -> PayProInvoiceStatus:
        """Server-to-server payment verification via ggosboi.

        NOTE: PayPro keys this by the merchant OrderNumber (our order_id), not by
        PayProId. This is the authoritative paid-check (CLAUDE.md §7 / Rule #5).
        """
        body = {"userName": settings.PAYPRO_USERNAME, "Order_Id": order_number}
        data = await self._authed("POST", ORDER_STATUS_PATH, body)
        ok, fields = _envelope(data)
        status = fields.get(F_ORDER_STATUS) if ok else None
        is_paid, is_failed = classify_status(status)
        return PayProInvoiceStatus(
            invoice_id=order_number,
            status=str(status),
            is_paid=is_paid,
            is_failed=is_failed,
            raw=fields,
        )

    async def is_order_paid(self, order_number: str) -> bool:
        """Convenience wrapper used by the webhook + reconciliation paths."""
        try:
            return (await self.get_invoice_status(order_number)).is_paid
        except PayProError as exc:
            logger.warning("PayPro status check failed for {}: {}", order_number, exc)
            return False
