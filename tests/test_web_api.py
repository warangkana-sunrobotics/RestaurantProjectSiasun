"""
Test the customer web API( /api/* ) and the static page without the real database.
Run:  pytest tests
"""
import os
import sys
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

import pytest

os.environ["API_KEY"] = "test-key"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dags" / "api"))

from fastapi.testclient import TestClient  # noqa: E402

import API_write_data as api  # noqa: E402

KEY = {"X-API-Key": "test-key"}

MENU = {1: ("ข้าวมันไก่กุ๊กๆ", Decimal("50.00")), 5: ("ชาไทยเย็น", Decimal("35.00"))}


class ScriptedCursor:
    """Cursor which answers the menu lookup and records every INSERT / UPDATE."""

    def __init__(self):
        self.inserts = []      # params of INSERT
        self.updates = []      # params of UPDATE
        self.paid_rows = []    # rows which UPDATE ... RETURNING gives back
        self._last = None
        self._next_id = 100
        self.rowcount = 0

    def execute(self, query, params=None):
        text = repr(query)
        if "INSERT" in text:
            self.inserts.append(params)
            self._last = "insert"
            self._next_id += 1
        elif "UPDATE" in text:
            self.updates.append(params)
            self._last = "update"
        elif "FROM" in text and "menu_id = ANY" in text:
            self._last = ("menu", params[0])
        else:
            self._last = "other"

    def fetchall(self):
        if isinstance(self._last, tuple):
            return [(mid, *MENU[mid]) for mid in self._last[1] if mid in MENU]
        if self._last == "update":
            return self.paid_rows
        return []

    def fetchone(self):
        return (self._next_id,)


@pytest.fixture
def cur(monkeypatch):
    fake = ScriptedCursor()

    @contextmanager
    def fake_db():
        yield fake

    monkeypatch.setattr(api, "get_db", fake_db)
    api._rate_hits.clear()
    return fake


@pytest.fixture
def client():
    return TestClient(api.app)


# ---------- ordering ----------

def test_order_uses_server_price_not_client_price(client, cur):
    body = {"tableNo": "01", "roundTotal": 0,
            "items": [{"menuId": 1, "quantity": 2, "price": 0, "name": "free food"}]}
    r = client.post("/api/orders", json=body)
    assert r.status_code == 201
    assert r.json()["roundTotal"] == 100.0
    table_id, name, cost, menu_id, qty = cur.inserts[0]
    assert (table_id, name, cost, menu_id, qty) == (1, "ข้าวมันไก่กุ๊กๆ", Decimal("50.00"), 1, 2)


def test_duplicate_menu_lines_are_merged(client, cur):
    body = {"tableNo": "2", "items": [{"menuId": 5, "quantity": 1}, {"menuId": 5, "quantity": 3}]}
    r = client.post("/api/orders", json=body)
    assert r.status_code == 201
    assert len(cur.inserts) == 1 and cur.inserts[0][4] == 4
    assert r.json()["roundTotal"] == 140.0


def test_merged_quantity_over_99_is_rejected(client, cur):
    body = {"tableNo": "1", "items": [{"menuId": 5, "quantity": 99}, {"menuId": 5, "quantity": 1}]}
    assert client.post("/api/orders", json=body).status_code == 422
    assert cur.inserts == []


def test_unknown_menu_is_400_and_nothing_inserted(client, cur):
    body = {"tableNo": "1", "items": [{"menuId": 1, "quantity": 1}, {"menuId": 999, "quantity": 1}]}
    r = client.post("/api/orders", json=body)
    assert r.status_code == 400
    assert cur.inserts == []


@pytest.mark.parametrize("table", ["0", "00", "6", "999", "abc", "1; DROP", "-1", ""])
def test_invalid_table_is_rejected(client, cur, table):
    r = client.post("/api/orders", json={"tableNo": table, "items": [{"menuId": 1, "quantity": 1}]})
    assert r.status_code == 422
    assert cur.inserts == []


@pytest.mark.parametrize("items", [
    [], [{"menuId": 1, "quantity": 0}], [{"menuId": 1, "quantity": 100}],
    [{"menuId": 0, "quantity": 1}], [{"menuId": "x", "quantity": 1}],
    [{"menuId": 1, "quantity": 1}] * 51,
])
def test_invalid_items_are_rejected(client, cur, items):
    assert client.post("/api/orders", json={"tableNo": "1", "items": items}).status_code == 422


# ---------- menu / bill ----------

def test_bill_rejects_bad_table(client, cur):
    assert client.get("/api/orders/table/abc").status_code == 422
    assert client.get("/api/orders/table/9999").status_code == 422
    assert client.get("/api/orders/table/7").status_code == 422


def test_bill_and_menu_are_public(client, cur, monkeypatch):
    monkeypatch.setattr(api, "_fetch", lambda q, p=None: [{"menuId": 1, "name": "x", "price": 50.0, "quantity": 2}])
    assert client.get("/api/orders/table/1").json()[0]["quantity"] == 2
    assert client.get("/api/menu").status_code == 200


# ---------- checkout( staff only ) ----------

def test_checkout_requires_staff_key(client, cur):
    assert client.post("/api/orders/checkout", json={"tableNo": "1"}).status_code == 401
    assert client.post("/api/orders/checkout", json={"tableNo": "1"}, headers={"X-API-Key": "x"}).status_code == 401
    assert cur.updates == []


def test_checkout_marks_paid_and_returns_total(client, cur):
    cur.paid_rows = [(Decimal("100.00"),), (Decimal("35.00"),)]
    r = client.post("/api/orders/checkout", json={"tableNo": "1"}, headers=KEY)
    assert r.status_code == 200
    assert r.json() == {"message": "paid", "lines": 2, "total": 135.0}
    assert cur.updates == [(1,)]


def test_checkout_without_open_orders_is_404(client, cur):
    assert client.post("/api/orders/checkout", json={"tableNo": "3"}, headers=KEY).status_code == 404


# ---------- rate limit / headers / static ----------

def test_rate_limit_returns_429(client, cur, monkeypatch):
    monkeypatch.setattr(api, "_fetch", lambda q, p=None: [])
    limited = TestClient(api.app)
    codes = [limited.get("/api/menu").status_code for _ in range(api.RATE_LIMIT_READ + 3)]
    assert codes[: api.RATE_LIMIT_READ] == [200] * api.RATE_LIMIT_READ
    assert codes[-1] == 429


def test_security_headers_present(client):
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"


def test_web_page_is_served_and_calls_same_origin_api(client):
    page = client.get("/")
    assert page.status_code == 200 and "text/html" in page.headers["content-type"]
    js = client.get("/script.js").text
    assert "localhost:3000" not in js
    assert "/api/orders" in js


def test_api_key_is_not_in_the_web_files():
    for name in ("index.html", "script.js", "style.css"):
        text = (ROOT / "web" / name).read_text(encoding="utf-8")
        assert "test-key" not in text
        key = os.getenv("API_KEY", "")
        assert not key or key not in text


# ---------- PromptPay QR ----------

def test_crc16_matches_standard_check_value():
    # CRC-16/CCITT-FALSE check value of "123456789"
    assert api._crc16("123456789") == "29B1"


def test_promptpay_payload_has_amount_and_valid_crc():
    p = api.promptpay_payload("0800000000", Decimal("185"))
    assert "0066800000000" in p                      # phone without the leading 0
    assert "5406185.00" in p                         # tag 54 = amount
    assert "010212" in p                             # dynamic QR
    assert p[-4:] == api._crc16(p[:-4])


def test_promptpay_rejects_bad_account():
    with pytest.raises(ValueError):
        api.promptpay_payload("123", Decimal("1"))


def test_qr_endpoint_sums_open_lines(client, cur, monkeypatch):
    monkeypatch.setattr(api, "_fetch", lambda q, p=None: [{"amount": 150.0}, {"amount": 35.0}])
    r = client.get("/api/orders/table/1/qr")
    assert r.status_code == 200
    assert r.json()["amount"] == 185.0
    assert "5406185.00" in r.json()["payload"]


def test_qr_endpoint_404_when_no_open_order(client, cur, monkeypatch):
    monkeypatch.setattr(api, "_fetch", lambda q, p=None: [])
    assert client.get("/api/orders/table/1/qr").status_code == 404


def test_qr_endpoint_rejects_bad_table(client, cur):
    assert client.get("/api/orders/table/abc/qr").status_code == 422
    assert client.get("/api/orders/table/9/qr").status_code == 422
