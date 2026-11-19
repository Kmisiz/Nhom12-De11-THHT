import pytest
from adapter.errors import AdapterError
from adapter.validator import validate, REQUIRED_FIELDS
from tests.helpers import CANONICAL_SV001

def test_valid_message_passes():
    m = dict(CANONICAL_SV001)
    assert validate(m) is m

def test_optional_fields_may_be_none():
    m = {**CANONICAL_SV001, "student_name": None, "email": None, "phone": None, "registered_at": None, "note": None}
    validate(m)

@pytest.mark.parametrize("field", REQUIRED_FIELDS)
@pytest.mark.parametrize("empty", [None, ""])
def test_missing_required(field, empty):
    with pytest.raises(AdapterError) as e:
        validate({**CANONICAL_SV001, field: empty})
    assert (e.value.code, e.value.field, e.value.http_status) == ("MISSING_FIELD", field, 422)

@pytest.mark.parametrize("field, value", [
    ("student_id", "SV1"), ("student_id", "AB001"), ("course_code", "INT33"),
    ("credits", "ba"), ("credits", 0), ("credits", 11), ("credits", 3.0),
    ("credits", True),
    ("semester", "2026-4"), ("semester", "HK1-2026"),
])
def test_invalid_value(field, value):
    with pytest.raises(AdapterError) as e:
        validate({**CANONICAL_SV001, field: value})
    assert (e.value.code, e.value.field, e.value.http_status) == ("INVALID_VALUE", field, 422)
