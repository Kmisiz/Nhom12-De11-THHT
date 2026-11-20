import os
from pathlib import Path
from flask import Flask, jsonify, request
from finance.db import init_db, insert_charge, list_charges

REQUIRED_FIELDS = (
    "message_id",
    "student_id",
    "course_code",
    "course_name",
    "semester",
    "credits",
    "unit_price",
    "amount",
    "currency",
)


def create_app(db_path: str = "runtime/finance.db") -> Flask:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    init_db(db_path)

    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/api/tuition-charges")
    def create_charge():
        payload = request.get_json(silent=True) or {}
        missing = [f for f in REQUIRED_FIELDS if f not in payload]
        if missing:
            return jsonify({"error": "INVALID_PAYLOAD", "missing": missing}), 400

        created, charge_id = insert_charge(db_path, payload)
        if created:
            return jsonify({
                "status": "CREATED",
                "charge_id": charge_id,
                "payment_status": "UNPAID",
            }), 201
        return jsonify({
            "status": "DUPLICATE_IGNORED",
            "charge_id": charge_id,
        }), 200

    @app.get("/api/tuition-charges")
    def get_charges():
        return jsonify(list_charges(db_path)), 200

    return app


if __name__ == "__main__":
    db = os.environ.get("FINANCE_DB", "runtime/finance.db")
    application = create_app(db)
    application.run(host="127.0.0.1", port=5001)