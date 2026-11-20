import sqlite3
from datetime import datetime, timezone

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tuition_charges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  message_id TEXT NOT NULL,
  student_id TEXT NOT NULL,
  course_code TEXT NOT NULL,
  course_name TEXT NOT NULL,
  semester TEXT NOT NULL,
  credits INTEGER NOT NULL,
  unit_price INTEGER NOT NULL,
  amount INTEGER NOT NULL,
  currency TEXT NOT NULL,
  payment_status TEXT NOT NULL DEFAULT 'UNPAID',
  created_at TEXT NOT NULL,
  UNIQUE (student_id, course_code, semester)
);
"""


def init_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()


def insert_charge(db_path: str, payload: dict) -> tuple[bool, int]:
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO tuition_charges (
                    message_id, student_id, course_code, course_name,
                    semester, credits, unit_price, amount, currency,
                    payment_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'UNPAID', ?)
                """,
                (
                    payload["message_id"],
                    payload["student_id"],
                    payload["course_code"],
                    payload["course_name"],
                    payload["semester"],
                    payload["credits"],
                    payload["unit_price"],
                    payload["amount"],
                    payload["currency"],
                    created_at,
                ),
            )
            conn.commit()
            return True, cur.lastrowid
        except sqlite3.IntegrityError:
            row = conn.execute(
                """
                SELECT id FROM tuition_charges
                WHERE student_id = ? AND course_code = ? AND semester = ?
                """,
                (payload["student_id"], payload["course_code"], payload["semester"]),
            ).fetchone()
            return False, row[0]


def list_charges(db_path: str) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM tuition_charges ORDER BY id ASC").fetchall()
        return [dict(r) for r in rows]