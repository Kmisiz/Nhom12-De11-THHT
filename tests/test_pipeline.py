import json
from adapter.enricher import PriceCatalog
from adapter.pipeline import process
from tests.helpers import load_sample, TRIO, PRICE_FILE, EXPECTED_FINANCE_PAYLOAD

CATALOG = PriceCatalog(PRICE_FILE)

def test_success_records_all_stages():
    r = process(load_sample(TRIO[0]), CATALOG)
    assert r.error is None and r.payload == EXPECTED_FINANCE_PAYLOAD
    assert list(r.stages) == ["input", "normalized", "enriched", "filtered"]
    assert (r.trace_id, r.source_system) == ("PORTAL-P-1001", "PORTAL")

def test_three_formats_same_payload_except_id():
    payloads = [process(load_sample(f), CATALOG).payload for f in TRIO]
    stripped = [{k: v for k, v in p.items() if k != "message_id"} for p in payloads]
    assert stripped[0] == stripped[1] == stripped[2]

def test_validation_error_stops_before_enrich():
    d = json.loads(load_sample(TRIO[0])); del d["courseCode"]
    r = process(json.dumps(d), CATALOG)
    assert r.error.code == "MISSING_FIELD" and r.payload is None
    assert list(r.stages) == ["input", "normalized"]

def test_unknown_format_gets_generated_trace_id():
    r = process('{"foo": "bar"}', CATALOG)
    assert r.error.code == "UNKNOWN_FORMAT" and list(r.stages) == ["input"]
    assert len(r.trace_id) == 32
