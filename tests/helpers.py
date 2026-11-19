from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"
PRICE_FILE = ROOT / "data" / "course_prices.csv"
TRIO = ("valid/a_portal_01_sv001.json", "valid/b_mobile_01_sv001.json", "valid/c_legacy_01_sv001.xml")

def load_sample(rel: str) -> str:
    return (SAMPLES / rel).read_text(encoding="utf-8")

CANONICAL_SV001 = {
    "message_id": "PORTAL-P-1001", "source_system": "PORTAL",
    "student_id": "SV001", "student_name": "Nguyễn Văn A",
    "email": "sv001@student.example.com", "phone": "0900000001",
    "course_code": "INT3306", "credits": 3, "semester": "2026-1",
    "registered_at": "2026-11-02T08:30:00+07:00", "note": "Đã duyệt",
}
ENRICHED_SV001 = {**CANONICAL_SV001, "course_name": "Phát triển ứng dụng Web",
                  "unit_price": 500000, "amount": 1500000, "currency": "VND"}
EXPECTED_FINANCE_PAYLOAD = {
    "message_id": "PORTAL-P-1001", "student_id": "SV001", "course_code": "INT3306",
    "course_name": "Phát triển ứng dụng Web", "semester": "2026-1", "credits": 3,
    "unit_price": 500000, "amount": 1500000, "currency": "VND",
}
