import csv
from pathlib import Path
from adapter.errors import AdapterError


class PriceCatalog:
    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)

    def get(self, course_code: str) -> dict | None:
        try:
            with self.csv_path.open(mode="r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                required_cols = {"course_code", "course_name", "price_per_credit"}
                if not reader.fieldnames or not required_cols.issubset(set(reader.fieldnames)):
                    raise AdapterError("LOOKUP_UNAVAILABLE", "Bảng giá thiếu cột bắt buộc", 503)

                for row in reader:
                    if row.get("course_code", "").strip() == course_code:
                        return {
                            "course_name": row["course_name"].strip(),
                            "price_per_credit": int(row["price_per_credit"]),
                        }
                return None
        except AdapterError:
            raise
        except Exception as e:
            raise AdapterError("LOOKUP_UNAVAILABLE", "Không đọc được bảng giá", 503) from e


def enrich(msg: dict, catalog: PriceCatalog) -> dict:
    course_code = msg.get("course_code")
    info = catalog.get(course_code)
    if info is None:
        raise AdapterError("PRICE_NOT_FOUND", f"Không tìm thấy đơn giá cho mã {course_code}", 422, field="course_code")

    enriched = dict(msg)
    unit_price = info["price_per_credit"]
    enriched["course_name"] = info["course_name"]
    enriched["unit_price"] = unit_price
    enriched["amount"] = enriched["credits"] * unit_price
    enriched["currency"] = "VND"
    return enriched