import json, pytest
from adapter.errors import AdapterError
from adapter.normalizer import normalize, CANONICAL_FIELDS
from tests.helpers import load_sample, TRIO, CANONICAL_SV001

def test_portal_to_canonical():
    assert normalize(load_sample(TRIO[0])) == CANONICAL_SV001

def test_mobile_converts_case_type_and_date():
    m = normalize(load_sample(TRIO[1]))
    assert m["message_id"] == "MOBILE-M-2001" and m["source_system"] == "MOBILE"
    assert (m["student_id"], m["course_code"]) == ("SV001", "INT3306")
    assert m["credits"] == 3 and type(m["credits"]) is int
    assert m["registered_at"] == "2026-11-02T08:30:00+07:00"
    assert m["note"] is None

def test_legacy_xml_converts_semester_and_date():
    m = normalize(load_sample(TRIO[2]))
    assert m["message_id"] == "LEGACY-L-3001"
    assert m["semester"] == "2026-1"
    assert m["registered_at"] == "2026-11-02T00:00:00+07:00"
    assert m["email"] is None and m["note"] == "Nhập từ hệ thống cũ"

def test_three_sources_same_core():
    msgs = [normalize(load_sample(f)) for f in TRIO]
    core = {(m["student_id"], m["course_code"], m["credits"], m["semester"]) for m in msgs}
    assert core == {("SV001", "INT3306", 3, "2026-1")}
    assert all(tuple(m) == CANONICAL_FIELDS for m in msgs)

def _portal(**override):
    d = {"requestId": "P-1", "studentId": "SV001", "courseCode": "INT3306", "credits": 3, "semester": "2026-1"}
    d.update(override)
    return json.dumps(d)

def test_strips_and_uppercases_codes():
    m = normalize(_portal(studentId=" sv001 ", courseCode=" int3306 "))
    assert (m["student_id"], m["course_code"]) == ("SV001", "INT3306")

def test_leading_bom_is_ignored():
    assert normalize("﻿" + _portal())["student_id"] == "SV001"

def test_bool_credits_not_converted():
    assert normalize(_portal(credits=True))["credits"] is True

def test_missing_field_becomes_none():
    d = json.loads(_portal()); del d["courseCode"]
    assert normalize(json.dumps(d))["course_code"] is None

@pytest.mark.parametrize("raw, code", [
    ('{"foo": "bar"}', "UNKNOWN_FORMAT"),
    ('[1, 2]', "UNKNOWN_FORMAT"),
    ('<Other/>', "UNKNOWN_FORMAT"),
    ('{"studentId": ', "MALFORMED"),
    ('<PhieuDangKy><SinhVien>', "MALFORMED"),
    ('   ', "MALFORMED"),
    ('<!DOCTYPE x [<!ENTITY a "aaa">]><PhieuDangKy>&a;</PhieuDangKy>', "MALFORMED"),
])
def test_rejects_bad_input(raw, code):
    with pytest.raises(AdapterError) as e:
        normalize(raw)
    assert e.value.code == code and e.value.http_status == 400
