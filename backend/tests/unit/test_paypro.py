import httpx
import pytest

from app.config import settings
from app.integrations.paypro import (
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
    http = httpx.AsyncClient(transport=transport, base_url="https://demoapi.paypro.com.pk")
    return PayProClient(redis_client=FakeRedis(), http_client=http)


@pytest.fixture(autouse=True)
def _paypro_env(monkeypatch):
    monkeypatch.setattr(settings, "PAYPRO_API_BASE_URL", "https://demoapi.paypro.com.pk")
    monkeypatch.setattr(settings, "PAYPRO_USERNAME", "Engs_Tech")
    monkeypatch.setattr(settings, "PAYPRO_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "PAYPRO_CLIENT_SECRET", "csecret")


# ---- token: returned in a response header, then cached ---------------------


async def test_token_from_header_is_cached():
    calls = {"auth": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/ppro/auth":
            calls["auth"] += 1
            return httpx.Response(200, headers={"token": "TKN"}, json=[{"Status": "00"}])
        return httpx.Response(404)

    client = _client(handler)
    assert await client.get_access_token() == "TKN"
    assert await client.get_access_token() == "TKN"
    assert calls["auth"] == 1  # second call served from cache


async def test_auth_missing_token_header_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"Status": "00"}])  # no token header

    with pytest.raises(PayProError):
        await _client(handler).get_access_token()


# ---- create_invoice: array body -> Click2Pay / PayProId --------------------


async def test_create_invoice_success():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/ppro/auth":
            return httpx.Response(200, headers={"token": "TKN"}, json=[{"Status": "00"}])
        if request.url.path == "/v2/ppro/co":
            assert request.headers["token"] == "TKN"
            return httpx.Response(
                200,
                json=[
                    {"Status": "00"},
                    {"PayProId": "01102205600001", "Click2Pay": "https://pay.pk/x"},
                ],
            )
        return httpx.Response(404)

    inv = await _client(handler).create_invoice(
        order_id="o-1",
        amount_pkr=3999,
        customer_email="a@b.com",
        customer_name="A",
        customer_phone="03001234567",
        description="pack",
    )
    assert inv.invoice_id == "01102205600001"
    assert inv.payment_url == "https://pay.pk/x"


async def test_create_invoice_nonzero_envelope_status_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/ppro/auth":
            return httpx.Response(200, headers={"token": "TKN"}, json=[{"Status": "00"}])
        return httpx.Response(200, json=[{"Status": "01"}])  # invalid data

    with pytest.raises(PayProError):
        await _client(handler).create_invoice(
            order_id="o-1",
            amount_pkr=3999,
            customer_email="a@b.com",
            customer_name="A",
            customer_phone=None,
            description="pack",
        )


async def test_auth_refresh_then_retry_on_401():
    state = {"auth": 0, "co_401_done": False}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/ppro/auth":
            state["auth"] += 1
            return httpx.Response(200, headers={"token": f"TKN{state['auth']}"}, json=[{"Status": "00"}])
        if request.url.path == "/v2/ppro/co":
            if not state["co_401_done"]:
                state["co_401_done"] = True
                return httpx.Response(401)
            return httpx.Response(
                200, json=[{"Status": "00"}, {"PayProId": "P1", "Click2Pay": "https://pay/x"}]
            )
        return httpx.Response(404)

    inv = await _client(handler).create_invoice(
        order_id="o-1", amount_pkr=100, customer_email="a@b.com",
        customer_name="A", customer_phone=None, description="d",
    )
    assert inv.invoice_id == "P1"
    assert state["auth"] == 2  # token refreshed after the 401


# ---- status via ggosboi ----------------------------------------------------


async def test_get_invoice_status_paid():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/ppro/auth":
            return httpx.Response(200, headers={"token": "TKN"}, json=[{"Status": "00"}])
        if request.url.path == "/v2/ppro/ggosboi":
            return httpx.Response(200, json=[{"Status": "00"}, {"OrderStatus": "PAID"}])
        return httpx.Response(404)

    st = await _client(handler).get_invoice_status("o-1")
    assert st.is_paid is True and st.is_failed is False


async def test_timeout_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    with pytest.raises(PayProTimeout):
        await _client(handler).get_access_token()


# ---- status classification -------------------------------------------------


def test_classify_status():
    assert classify_status("PAID") == (True, False)
    assert classify_status("blocked") == (False, True)
    assert classify_status("expired") == (False, True)
    assert classify_status("UNPAID") == (False, False)
    assert classify_status(None) == (False, False)
