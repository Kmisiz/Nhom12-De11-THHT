
import json
import os
import re

from pathlib import Path
from datetime import datetime, timezone, timedelta

from flask import Flask, jsonify, request

from adapter.pipeline import process
from adapter.errors import AdapterError
from adapter.finance_client import send_charge
from adapter.enricher import PriceCatalog


# Mui gio Viet Nam
VN_TZ = timezone(timedelta(hours=7))


# Xac dinh buoc phat sinh loi
ERROR_STAGE = {
    "UNKNOWN_FORMAT": "normalizer",
    "MALFORMED": "normalizer",
    "MISSING_FIELD": "validator",
    "INVALID_VALUE": "validator",
    "PRICE_NOT_FOUND": "enricher",
}


def write_json(path, data):
    """
    Ghi du lieu JSON bang UTF-8.
    Tao thu muc neu chua ton tai.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def create_app(catalog, send_fn, runtime_dir):
    """
    Tao Flask application.

    catalog:
        Doi tuong PriceCatalog.

    send_fn:
        Ham gui payload sang Finance.
        Duoc truyen vao de test khong can Finance that.

    runtime_dir:
        Thu muc luu traces, logs va invalid.
    """

    app = Flask(__name__)

    runtime_dir = Path(runtime_dir)

    # API kiem tra trang thai Adapter
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    # API nhan phieu dang ky
    @app.post("/api/registrations")
    def registrations():

        # Doc nguyen van request body
        raw = request.get_data(as_text=True)

        # Chay Pipeline
        result = process(raw, catalog)

        error = result.error

        # Mac dinh
        finance_data = None

        if error is not None:

            # Pipeline da phat hien loi
            # Khong duoc goi Finance

            http_status = error.http_status

            response_body = {
                "status": "REJECTED",
                **error.to_dict(),
                "trace_id": result.trace_id
            }

        else:

            try:
                # Gui payload sang Finance
                finance_status, finance_data = send_fn(
                    result.payload
                )

                if finance_status == 201:

                    # Finance tao khoan hoc phi moi
                    http_status = 201

                    response_body = {
                        "status": "FORWARDED",
                        "message_id": result.payload.get("message_id"),
                        "trace_id": result.trace_id,
                        "finance": finance_data
                    }

                elif finance_status == 200:

                    # Finance thong bao da ton tai khoan hoc phi
                    http_status = 200

                    response_body = {
                        "status": finance_data.get("status"),
                        "message_id": result.payload.get("message_id"),
                        "trace_id": result.trace_id,
                        "finance": finance_data
                    }

                else:

                    # Finance tra ma HTTP khong hop le
                    raise AdapterError(
                        "FINANCE_REJECTED",
                        f"Finance trả về HTTP {finance_status}",
                        502
                    )

            except AdapterError as exc:

                error = exc
                http_status = exc.http_status

                response_body = {
                    "status": "REJECTED",
                    **exc.to_dict(),
                    "trace_id": result.trace_id
                }

        # Lay thoi gian nhan request
        now = datetime.now(VN_TZ)

        received_at = now.isoformat()

        timestamp = now.strftime(
            "%Y%m%d-%H%M%S-%f"
        )

        # Lam sach trace_id de tao ten file an toan
        safe_trace_id = re.sub(
            r"[^A-Za-z0-9_.-]",
            "_",
            result.trace_id
        )

        filename = (
            f"{timestamp}_{safe_trace_id}.json"
        )

        # Tao noi dung trace
        trace_data = {
            "trace_id": result.trace_id,
            "received_at": received_at,
            "source_system": result.source_system,
            "http_status": http_status,
            "response": response_body,
            "stages": result.stages
        }

        # Ghi trace cho moi request
        trace_path = (
            runtime_dir / "traces" / filename
        )

        write_json(trace_path, trace_data)

        # Chi ghi Invalid neu loi du lieu HTTP 400 hoac 422
        if error is not None and http_status in (400, 422):

            invalid_data = {
                "trace_id": result.trace_id,
                "received_at": received_at,
                "source_system": result.source_system,
                "http_status": http_status,
                "error_code": error.code,
                "message": error.message,
                "field": error.field,
                "stage": ERROR_STAGE.get(error.code),
                "input": raw
            }

            invalid_path = (
                runtime_dir / "invalid" / filename
            )

            write_json(invalid_path, invalid_data)

        # Tao mot dong log cho moi request
        log_data = {
            "ts": received_at,
            "trace_id": result.trace_id,
            "source_system": result.source_system,
            "http_status": http_status,
            "status": response_body.get("status"),
            "error_code": (
                error.code if error is not None else None
            )
        }

        log_path = (
            runtime_dir / "logs" / "adapter.jsonl"
        )

        log_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with log_path.open(
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                json.dumps(
                    log_data,
                    ensure_ascii=False
                ) + "\n"
            )

        return jsonify(response_body), http_status

    return app


def main():

    # Lay cau hinh tu bien moi truong
    finance_url = os.getenv(
        "FINANCE_URL",
        "http://127.0.0.1:5001"
    )

    price_file = os.getenv(
        "PRICE_FILE",
        "data/course_prices.csv"
    )

    runtime_dir = os.getenv(
        "RUNTIME_DIR",
        "runtime"
    )

    # Khoi tao bang gia
    catalog = PriceCatalog(price_file)

    # Tao Adapter application
    app = create_app(
        catalog,
        lambda payload: send_charge(
            payload,
            finance_url
        ),
        runtime_dir
    )

    # Chay Adapter tren cong 5000
    app.run(
        host="127.0.0.1",
        port=5000
    )


if __name__ == "__main__":
    main()
