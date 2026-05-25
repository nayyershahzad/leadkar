import hashlib
import hmac

import httpx
import pytest

from app.config import settings
from app.integrations.paypro import (
    SIGNATURE_HEADER,
    PayProAuthError,
    PayProClient,
    PayProError,
    PayProTimeout,
    classify_status,
)


class FakeRedis:
    """Minimal async Redis stand-in for token-cache tests."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    async def delete(self, key):
        self.store.pop(key, None)
        return 1


def _client(handler) -> PayProClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport, base_url="https://paypro.test")
    return PayProClient(redis_client=FakeRedis(), http_client=http)


# ---- token caching ---------------------------------------------------------


async def test_token_is_cached_after_first_fetch():
    calls = {"token": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/token":
            calls["token"] += 1
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        return httpx.Response(404)

    client = _client(handler)
    assert await client.get_access_token() == "tok"
    assert await client.get_access_token() == "tok"
    assert calls["token"] == 1  # second call served from cache


# ---- create_invoice: success / failure / 401 / timeout ---------------------


async def test_create_invoice_success():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        if request.url.path == "/invoices":
            return httpx.Response(
                200, json={"id": "inv_42", "payment_url": "https://pay.test/inv_42"}
            )
        return httpx.Response(404)

    invoice = await _client(handler).create_invoice(
        order_id="o1",
        amount_pkr=3999,
        customer_email="a@b.com",
        customer_name="A",
        customer_phone="03001234567",
        description="Karachi Restaurants pack",
        return_url="https://leadkar.pk/order/success",
        cancel_url="https://leadkar.pk/order/pending",
    )
    assert invoice.invoice_id == "inv_42"
    assert invoice.payment_url == "https://pay.test/inv_42"


async def test_create_invoice_server_error_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        return httpx.Response(500, text="boom")

    with pytest.raises(PayProError):
        await _client(handler)._request("POST", "https://paypro.test/invoices")


async def test_auth_401_raises_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    with pytest.raises(PayProAuthError):
        await _client(handler).get_access_token()


async def test_timeout_raises_paypro_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    with pytest.raises(PayProTimeout):
        await _client(handler).get_access_token()


# ---- status classification -------------------------------------------------


def test_classify_status():
    assert classify_status("paid") == (True, False)
    assert classify_status("SUCCESS") == (True, False)
    assert classify_status("cancelled") == (False, True)
    assert classify_status("pending") == (False, False)
    assert classify_status(None) == (False, False)


# ---- webhook signature -----------------------------------------------------


def test_verify_webhook_signature_valid(monkeypatch):
    monkeypatch.setattr(settings, "PAYPRO_WEBHOOK_SECRET", "s3cret")
    body = b'{"event_id":"e1","status":"paid"}'
    sig = hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    client = PayProClient(redis_client=FakeRedis(), http_client=httpx.AsyncClient())
    assert client.verify_webhook_signature(body, {SIGNATURE_HEADER: sig}) is True
    # case-insensitive header + sha256= prefix tolerated
    assert client.verify_webhook_signature(body, {"X-PayPro-Signature": f"sha256={sig}"}) is True


def test_verify_webhook_signature_invalid(monkeypatch):
    monkeypatch.setattr(settings, "PAYPRO_WEBHOOK_SECRET", "s3cret")
    body = b'{"event_id":"e1","status":"paid"}'
    client = PayProClient(redis_client=FakeRedis(), http_client=httpx.AsyncClient())
    assert client.verify_webhook_signature(body, {SIGNATURE_HEADER: "deadbeef"}) is False
    assert client.verify_webhook_signature(body, {}) is False  # missing header


def test_verify_webhook_signature_no_secret_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "PAYPRO_WEBHOOK_SECRET", "")
    client = PayProClient(redis_client=FakeRedis(), http_client=httpx.AsyncClient())
    assert client.verify_webhook_signature(b"{}", {SIGNATURE_HEADER: "x"}) is False
