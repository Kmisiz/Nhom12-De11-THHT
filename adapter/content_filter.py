FINANCE_FIELDS = (
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


def filter_for_finance(msg: dict) -> dict:
    return {k: msg[k] for k in FINANCE_FIELDS if k in msg}