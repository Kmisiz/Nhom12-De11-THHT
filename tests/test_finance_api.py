import pytest
from finance.app import create_app
from tests.helpers import EXPECTED_FINANCE_PAYLOAD as P


@pytest.fixture
def client(tmp_path):
    return create_app(str(tmp_path / "f.db")).test_client()


def test_create_charge(client):
    r = client.post("/api/tuition-charges", json=P)
    assert r.status_code == 201
    assert r.get_json() == {"status": "CREATED", "charge_id": 1, "payment_status": "UNPAID"}


def test_duplicate_business_key_is_ignored(client):
    client.post("/api/tuition-charges", json=P)
    r = client.post("/api/tuition-charges", json={**P, "message_id": "MOBILE-M-2001"})
    assert r.status_code == 200 and r.get_json() == {"status": "DUPLICATE_IGNORED", "charge_id": 1}
    assert len(client.get("/api/tuition-charges").get_json()) == 1


def test_missing_field(client):
    body = {k: v for k, v in P.items() if k != "amount"}
    r = client.post("/api/tuition-charges", json=body)
    assert r.status_code == 400 and r.get_json() == {"error": "INVALID_PAYLOAD", "missing": ["amount"]}


def test_list_contains_stored_fields(client):
    client.post("/api/tuition-charges", json=P)
    [row] = client.get("/api/tuition-charges").get_json()
    assert row["amount"] == 1500000 and row["payment_status"] == "UNPAID"