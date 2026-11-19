from adapter.content_filter import filter_for_finance, FINANCE_FIELDS
from tests.helpers import ENRICHED_SV001, EXPECTED_FINANCE_PAYLOAD


def test_output_matches_finance_contract():
    out = filter_for_finance(dict(ENRICHED_SV001))
    assert out == EXPECTED_FINANCE_PAYLOAD and tuple(out) == FINANCE_FIELDS


def test_removes_personal_and_internal_data():
    out = filter_for_finance(dict(ENRICHED_SV001))
    for k in ("student_name", "email", "phone", "note", "source_system", "registered_at"):
        assert k not in out


def test_whitelist_blocks_unknown_fields():
    assert "password" not in filter_for_finance({**ENRICHED_SV001, "password": "x"})