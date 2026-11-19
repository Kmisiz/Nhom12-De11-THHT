import pytest
from adapter.errors import AdapterError
from adapter.enricher import PriceCatalog, enrich
from tests.helpers import CANONICAL_SV001, ENRICHED_SV001, PRICE_FILE

CATALOG = PriceCatalog(PRICE_FILE)


def test_enrich_adds_price_and_amount():
    assert enrich(dict(CANONICAL_SV001), CATALOG) == ENRICHED_SV001


def test_enrich_does_not_mutate_input():
    m = dict(CANONICAL_SV001)
    enrich(m, CATALOG)
    assert m == CANONICAL_SV001


def test_amount_uses_credits():
    out = enrich({**CANONICAL_SV001, "course_code": "MAT1041", "credits": 4}, CATALOG)
    assert (out["unit_price"], out["amount"]) == (400000, 1600000)


def test_unknown_course():
    with pytest.raises(AdapterError) as e:
        enrich({**CANONICAL_SV001, "course_code": "XYZ9999"}, CATALOG)
    assert (e.value.code, e.value.field, e.value.http_status) == ("PRICE_NOT_FOUND", "course_code", 422)


def test_missing_catalog_file(tmp_path):
    with pytest.raises(AdapterError) as e:
        PriceCatalog(tmp_path / "nope.csv").get("INT3306")
    assert (e.value.code, e.value.http_status) == ("LOOKUP_UNAVAILABLE", 503)


def test_catalog_with_excel_bom(tmp_path):
    p = tmp_path / "prices.csv"
    p.write_text("course_code,course_name,price_per_credit\nINT3306,Web,500000\n", encoding="utf-8-sig")
    assert PriceCatalog(p).get("INT3306") == {"course_name": "Web", "price_per_credit": 500000}