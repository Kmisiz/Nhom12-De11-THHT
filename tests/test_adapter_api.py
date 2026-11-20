import json, pytest
from adapter.app import create_app
from adapter.enricher import PriceCatalog
from adapter.errors import AdapterError
from adapter.finance_client import send_charge
from tests.helpers import load_sample, TRIO, PRICE_FILE, EXPECTED_FINANCE_PAYLOAD

class FakeFinance:
    def __init__(self, result=(201, {"status": "CREATED", "charge_id": 1, "payment_status": "UNPAID"}), error=None):
        self.result, self.error, self.calls = result, error, []
    def __call__(self, payload):
        self.calls.append(payload)
        if self.error: raise self.error
        return self.result

def make(tmp_path, fake):
    return create_app(PriceCatalog(PRICE_FILE), fake, tmp_path).test_client()

def post(client, rel):
    ctype = "application/xml" if rel.endswith(".xml") else "application/json"
    return client.post("/api/registrations", data=load_sample(rel).encode("utf-8"), content_type=ctype)

def test_valid_message_forwarded(tmp_path):
    fake = FakeFinance(); r = post(make(tmp_path, fake), TRIO[2])
    assert r.status_code == 201 and r.get_json()["status"] == "FORWARDED"
    assert fake.calls[0]["course_code"] == "INT3306" and fake.calls[0]["amount"] == 1500000

def test_duplicate_passthrough(tmp_path):
    fake = FakeFinance(result=(200, {"status": "DUPLICATE_IGNORED", "charge_id": 1}))
    r = post(make(tmp_path, fake), TRIO[0])
    assert r.status_code == 200 and r.get_json()["status"] == "DUPLICATE_IGNORED"

def test_finance_unavailable(tmp_path):
    fake = FakeFinance(error=AdapterError("FINANCE_UNAVAILABLE", "Finance không phản hồi", 503))
    r = post(make(tmp_path, fake), TRIO[0])
    assert r.status_code == 503 and r.get_json()["error_code"] == "FINANCE_UNAVAILABLE"

def test_rejected_message_never_forwarded(tmp_path):
    fake = FakeFinance(); client = make(tmp_path, fake)
    r = client.post("/api/registrations", data='{"foo": "bar"}', content_type="application/json")
    assert r.status_code == 400 and r.get_json()["status"] == "REJECTED"
    assert fake.calls == []

def test_trace_written_utf8(tmp_path):
    post(make(tmp_path, FakeFinance()), TRIO[0])
    [f] = (tmp_path / "traces").glob("*_PORTAL-P-1001.json")
    trace = json.loads(f.read_text(encoding="utf-8"))
    assert "Đã duyệt" in f.read_text(encoding="utf-8")
    assert list(trace["stages"]) == ["input", "normalized", "enriched", "filtered"]
    assert trace["stages"]["filtered"] == EXPECTED_FINANCE_PAYLOAD

def test_log_line_per_request(tmp_path):
    client = make(tmp_path, FakeFinance())
    post(client, TRIO[0]); post(client, TRIO[1])
    lines = (tmp_path / "logs" / "adapter.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(l)["status"] for l in lines] == ["FORWARDED", "FORWARDED"]

def test_invalid_message_channel(tmp_path):
    client = make(tmp_path, FakeFinance())
    rel = "invalid/x_01_missing_course.json"
    post(client, rel)
    [f] = (tmp_path / "invalid").glob("*.json")
    rec = json.loads(f.read_text(encoding="utf-8"))
    assert (rec["http_status"], rec["error_code"], rec["stage"]) == (422, "MISSING_FIELD", "validator")
    assert rec["input"] == load_sample(rel)

def test_system_error_not_in_invalid_channel(tmp_path):
    fake = FakeFinance(error=AdapterError("FINANCE_UNAVAILABLE", "Finance không phản hồi", 503))
    post(make(tmp_path, fake), TRIO[0])
    post(make(tmp_path, FakeFinance()), TRIO[1])
    assert list((tmp_path / "invalid").glob("*.json")) == []

def test_send_charge_unreachable():
    with pytest.raises(AdapterError) as e:
        send_charge(EXPECTED_FINANCE_PAYLOAD, "http://127.0.0.1:9", timeout=1)
    assert e.value.code == "FINANCE_UNAVAILABLE"
