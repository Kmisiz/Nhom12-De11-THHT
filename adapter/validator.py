
import re

from adapter.errors import AdapterError


# 5 truong bat buoc theo yeu cau Task 2
REQUIRED_FIELDS = (
    "message_id",
    "student_id",
    "course_code",
    "credits",
    "semester",
)


def validate(msg):
    """
    Kiem tra du lieu Canonical.

    Neu du lieu hop le:
        Tra ve chinh Dictionary ban dau.

    Neu du lieu khong hop le:
        Phat sinh AdapterError voi HTTP 422.
    """

    # LUOT 1: Kiem tra cac truong bat buoc
    for field in REQUIRED_FIELDS:
        value = msg.get(field)

        if value is None or value == "":
            raise AdapterError(
                "MISSING_FIELD",
                f"Thiếu trường bắt buộc: {field}",
                422,
                field=field
            )

    # LUOT 2: Kiem tra rang buoc gia tri

    # 1. Kiem tra ma sinh vien: SV + 3 chu so
    student_id = msg.get("student_id")

    if (
        not isinstance(student_id, str)
        or re.fullmatch(r"SV\d{3}", student_id) is None
    ):
        raise AdapterError(
            "INVALID_VALUE",
            "Mã sinh viên không đúng định dạng",
            422,
            field="student_id"
        )

    # 2. Kiem tra ma hoc phan: 3 chu hoa + 4 chu so
    course_code = msg.get("course_code")

    if (
        not isinstance(course_code, str)
        or re.fullmatch(r"[A-Z]{3}\d{4}", course_code) is None
    ):
        raise AdapterError(
            "INVALID_VALUE",
            "Mã học phần không đúng định dạng",
            422,
            field="course_code"
        )

    # 3. Kiem tra so tin chi: int that tu 1 den 10
    credits = msg.get("credits")

    if type(credits) is not int or not (1 <= credits <= 10):
        raise AdapterError(
            "INVALID_VALUE",
            "Số tín chỉ phải là số nguyên từ 1 đến 10",
            422,
            field="credits"
        )

    # 4. Kiem tra hoc ky: YYYY-1, YYYY-2 hoac YYYY-3
    semester = msg.get("semester")

    if (
        not isinstance(semester, str)
        or re.fullmatch(r"\d{4}-[1-3]", semester) is None
    ):
        raise AdapterError(
            "INVALID_VALUE",
            "Học kỳ không đúng định dạng",
            422,
            field="semester"
        )

    # Tat ca hop le: tra ve chinh msg ban dau
    return msg
