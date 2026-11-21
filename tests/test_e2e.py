import pytest
from adapter.app import create_app as adapter_app
from adapter.enricher import PriceCatalog
from adapter.errors import AdapterError
from finance.app import create_app as finance_app
from tests.helpers import SAMPLES, PRICE_FILE


@pytest.fixture
def clients(tmp_path):
    fin = finance_app(str(tmp_path / "f.db")).test_client()

    def send(payload):
        r = fin.post("/api/tuition-charges", json=payload)
        if r.status_code not in (200, 201):
            raise AdapterError("FINANCE_REJECTED", r.get_data(as_text=True), 502)
        return r.status_code, r.get_json()

    return adapter_app(PriceCatalog(PRICE_FILE), send, tmp_path / "rt").test_client(), fin


def post_file(client, path):
    ctype = "application/xml" if path.suffix == ".xml" else "application/json"
    return client.post("/api/registrations", data=path.read_bytes(), content_type=ctype)


def test_all_valid_samples(clients):
    adapter, fin = clients
    files = sorted((SAMPLES / "valid").iterdir())
    statuses = [post_file(adapter, f).get_json()["status"] for f in files]
    assert len(files) == 12
    assert statuses.count("FORWARDED") == 10 and statuses.count("DUPLICATE_IGNORED") == 2
    charges = fin.get("/api/tuition-charges").get_json()
    assert len(charges) == 10 and sum(c["amount"] for c in charges) == 15_200_000


@pytest.mark.parametrize("name, http, code", [
    ("x_01_missing_course.json", 422, "MISSING_FIELD"),
    ("x_02_bad_credits.json", 422, "INVALID_VALUE"),
    ("x_03_unknown_course.xml", 422, "PRICE_NOT_FOUND"),
    ("x_04_unknown_format.json", 400, "UNKNOWN_FORMAT"),
    ("x_05_malformed.xml", 400, "MALFORMED"),
])
def test_invalid_samples_never_reach_finance(clients, name, http, code):
    adapter, fin = clients
    r = post_file(adapter, SAMPLES / "invalid" / name)
    assert r.status_code == http and r.get_json()["error_code"] == code
    assert fin.get("/api/tuition-charges").get_json() == []