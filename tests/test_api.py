"""
Test the API without the real database( psycopg2.connect is replaced by the fake ).
Run:  pip install -r requirements-dev.txt  &&  pytest tests
"""
import os
import sys
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

import pytest

os.environ["API_KEY"] = "test-key"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dags" / "api"))

from fastapi.testclient import TestClient  # noqa: E402

import API_write_data as api  # noqa: E402

HEADERS = {"X-API-Key": "test-key"}


class FakeCursor:
    def __init__(self):
        self.executed = []        # [(query_text, params)]
        self.rows = []
        self.description = [("order_id",), ("table_id",), ("menu",), ("cost",)]
        self.rowcount = 1

    def execute(self, query, params=None):
        self.executed.append((repr(query), params))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return (42,)


@pytest.fixture
def cur(monkeypatch):
    fake = FakeCursor()

    @contextmanager
    def fake_db():
        yield fake

    monkeypatch.setattr(api, "get_db", fake_db)
    return fake


@pytest.fixture
def client():
    return TestClient(api.app)


# ---------- authentication ----------

def test_missing_api_key_is_401(client, cur):
    assert client.get("/restaurant/getOrders").status_code == 401


def test_wrong_api_key_is_401(client, cur):
    assert client.get("/restaurant/getOrders", headers={"X-API-Key": "nope"}).status_code == 401


def test_not_configured_server_fails_closed(client, cur, monkeypatch):
    monkeypatch.setenv("API_KEY", "")
    assert client.get("/restaurant/getOrders", headers=HEADERS).status_code == 503


def test_health_needs_no_key(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_docs_are_disabled_by_default(client):
    assert client.get("/docs").status_code == 404


# ---------- read ----------

def test_get_all_converts_decimal_to_float(client, cur, monkeypatch):
    cur.rows = [(1, 1, "Icecream", Decimal("75.50"))]
    monkeypatch.setattr(api, "_fetch", lambda q, p=None: api.convertIntoJson(
        [d[0] for d in cur.description], cur.rows))
    r = client.get("/restaurant/getOrders", headers=HEADERS)
    assert r.status_code == 200
    assert r.json() == [{"order_id": 1, "table_id": 1, "menu": "Icecream", "cost": 75.5}]


def test_pagination_limit_is_validated(client, cur):
    assert client.get("/restaurant/getOrders?limit=100000", headers=HEADERS).status_code == 422


# ---------- insert ----------

def test_insert_returns_201_and_uses_parameters(client, cur):
    evil = "x'); DROP TABLE orders; --"
    r = client.post("/restaurant/insertOrder", headers=HEADERS,
                    json={"table_id": 1, "menu": evil, "cost": 10})
    assert r.status_code == 201
    assert r.json()["order_id"] == 42
    query, params = cur.executed[-1]
    assert "DROP TABLE" not in query           # never concatenated into the SQL
    assert params == (1, evil, 10)             # sent as the parameter


@pytest.mark.parametrize("body", [
    {"table_id": 0, "menu": "a", "cost": 1},
    {"table_id": 1, "menu": "   ", "cost": 1},
    {"table_id": 1, "menu": "a", "cost": -5},
    {"table_id": 1, "menu": "a" * 256, "cost": 1},
    {"table_id": 1, "menu": "a"},
])
def test_insert_rejects_invalid_body(client, cur, body):
    assert client.post("/restaurant/insertOrder", headers=HEADERS, json=body).status_code == 422


# ---------- delete ----------

def test_delete_missing_order_is_404(client, cur):
    cur.rowcount = 0
    assert client.delete("/restaurant/delOrders/orderId/999", headers=HEADERS).status_code == 404


def test_delete_existing_order_is_200(client, cur):
    assert client.delete("/restaurant/delOrders/orderId/1", headers=HEADERS).status_code == 200


def test_db_error_does_not_leak_detail(client, monkeypatch):
    @contextmanager
    def broken():
        raise RuntimeError("password=secret host=10.0.0.5")
        yield

    monkeypatch.setattr(api, "get_db", broken)
    r = client.delete("/restaurant/delOrders/tableId/1", headers=HEADERS)
    assert r.status_code == 500
    assert "secret" not in r.text
