"""Normalize Portal, Mobile and Legacy registration messages to Canonical Data Model."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from adapter.errors import AdapterError


# Thứ tự 11 trường được quy định tại Tài liệu thiết kế giải pháp, mục 5.2.
CANONICAL_FIELDS = (
    "message_id",
    "source_system",
    "student_id",
    "student_name",
    "email",
    "phone",
    "course_code",
    "credits",
    "semester",
    "registered_at",
    "note",
)

_VIETNAM_TZ = timezone(timedelta(hours=7))
_XML_PARSE_ERRORS = (ElementTree.ParseError, DefusedXmlException, ValueError, TypeError)


def _clean_raw(raw: str) -> str:
    """Remove a leading BOM and leading whitespace without altering the payload."""
    if not isinstance(raw, str):
        raise AdapterError("MALFORMED", "Thông điệp đầu vào phải là chuỗi", 400)
    return raw.lstrip("\ufeff \t\r\n\v\f")


def detect_format(raw: str) -> str:
    """Return PORTAL, MOBILE or LEGACY; raise AdapterError for invalid formats."""
    text = _clean_raw(raw)

    if not text:
        raise AdapterError("MALFORMED", "Thông điệp đầu vào rỗng", 400)

    if text.startswith("<"):
        try:
            root = ElementTree.fromstring(text)
        except _XML_PARSE_ERRORS as exc:
            raise AdapterError("MALFORMED", "Thông điệp XML không hợp lệ", 400) from exc

        if root.tag == "PhieuDangKy":
            return "LEGACY"
        raise AdapterError("UNKNOWN_FORMAT", "Không nhận diện được định dạng XML", 400)

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise AdapterError("MALFORMED", "Thông điệp JSON không hợp lệ", 400) from exc

    if isinstance(data, dict) and "studentId" in data:
        return "PORTAL"

    if isinstance(data, dict) and "student" in data and "enrollment" in data:
        return "MOBILE"

    raise AdapterError("UNKNOWN_FORMAT", "Không nhận diện được định dạng thông điệp", 400)


def _code(value: Any) -> Any:
    """Trim and uppercase student/course codes; preserve non-string values."""
    if isinstance(value, str):
        return value.strip().upper()
    return value


def _to_int(value: Any) -> Any:
    """Convert a string consisting only of digits to int; preserve all other values."""
    # bool is a subclass of int in Python, so it must be checked explicitly first.
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return value


def _semester(value: Any) -> Any:
    """Convert HKk-yyyy to yyyy-k; leave other values unchanged for Validator."""
    if not isinstance(value, str):
        return value

    value = value.strip()
    if len(value) == 8 and value.startswith("HK") and value[3] == "-":
        term = value[2]
        year = value[4:]
        if term in "123" and len(year) == 4 and year.isdigit():
            return f"{year}-{term}"
    return value


def _date(value: Any, fmt: str | None = None) -> str | None:
    """Convert a date/time to ISO 8601 with Vietnam's +07:00 offset.

    When fmt is supplied, parse using that source-specific format. With no fmt,
    parse an ISO 8601 value (the Portal format).
    """
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        if fmt:
            parsed = datetime.strptime(value.strip(), fmt)
        else:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=_VIETNAM_TZ)
        else:
            parsed = parsed.astimezone(_VIETNAM_TZ)

        return parsed.isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def _nested_get(data: dict, *keys: str) -> Any:
    """Safely get a value from nested dictionaries; absent paths become None."""
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _message_id(source: str, source_id: Any) -> str | None:
    """Prefix a source's message identifier; missing identifiers remain None."""
    if source_id is None or source_id == "":
        return None
    return f"{source}-{source_id}"


def _from_portal(data: dict) -> dict:
    """Translate Portal's flat JSON object to Canonical fields."""
    return {
        "message_id": _message_id("PORTAL", data.get("requestId")),
        "source_system": "PORTAL",
        "student_id": _code(data.get("studentId")),
        "student_name": data.get("fullName"),
        "email": data.get("email"),
        "phone": data.get("phone"),
        "course_code": _code(data.get("courseCode")),
        "credits": _to_int(data.get("credits")),
        "semester": _semester(data.get("semester")),
        "registered_at": _date(data.get("registeredAt")),
        "note": data.get("advisorNote"),
    }


def _from_mobile(data: dict) -> dict:
    """Translate Mobile's nested JSON object to Canonical fields."""
    return {
        "message_id": _message_id("MOBILE", _nested_get(data, "meta", "id")),
        "source_system": "MOBILE",
        "student_id": _code(_nested_get(data, "student", "code")),
        "student_name": _nested_get(data, "student", "name"),
        "email": _nested_get(data, "student", "contact", "email"),
        "phone": _nested_get(data, "student", "contact", "phone"),
        "course_code": _code(_nested_get(data, "enrollment", "course")),
        "credits": _to_int(_nested_get(data, "enrollment", "creditCount")),
        "semester": _semester(_nested_get(data, "enrollment", "term")),
        "registered_at": _date(_nested_get(data, "meta", "ts"), "%d/%m/%Y %H:%M"),
        "note": None,
    }


def _xml_child_text(parent: Any, path: str) -> str | None:
    """Return the text of an XML child; absent element/text becomes None."""
    if parent is None:
        return None
    element = parent.find(path)
    if element is None or element.text is None:
        return None
    return element.text


def _from_legacy(root: Any) -> dict:
    """Translate the Legacy XML document to Canonical fields."""
    student = root.find("SinhVien")
    course = root.find("HocPhan")

    return {
        "message_id": _message_id("LEGACY", root.attrib.get("soPhieu")),
        "source_system": "LEGACY",
        "student_id": _code(student.attrib.get("ma") if student is not None else None),
        "student_name": _xml_child_text(student, "HoTen"),
        "email": None,
        "phone": None,
        "course_code": _code(course.attrib.get("ma") if course is not None else None),
        "credits": _to_int(course.attrib.get("soTinChi") if course is not None else None),
        "semester": _semester(_xml_child_text(root, "HocKy")),
        "registered_at": _date(_xml_child_text(root, "NgayDangKy"), "%d/%m/%Y"),
        "note": _xml_child_text(root, "GhiChu"),
    }


def normalize(raw: str) -> dict:
    """Normalize a raw Portal/Mobile/Legacy message to the 11-field Canonical model."""
    text = _clean_raw(raw)
    source = detect_format(text)

    if source == "LEGACY":
        try:
            parsed = ElementTree.fromstring(text)
        except _XML_PARSE_ERRORS as exc:  # Defensive: detect_format already parsed it.
            raise AdapterError("MALFORMED", "Thông điệp XML không hợp lệ", 400) from exc
        mapped = _from_legacy(parsed)
    else:
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:  # Defensive.
            raise AdapterError("MALFORMED", "Thông điệp JSON không hợp lệ", 400) from exc

        if source == "PORTAL":
            mapped = _from_portal(parsed)
        else:
            mapped = _from_mobile(parsed)

    # Always return all 11 keys in the exact canonical order. Missing source
    # values remain None; Task 2 (Validator) is responsible for rejecting them.
    return {field: mapped.get(field) for field in CANONICAL_FIELDS}
