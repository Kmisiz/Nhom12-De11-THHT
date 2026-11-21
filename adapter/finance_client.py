
import requests

from adapter.errors import AdapterError


def send_charge(payload, base_url, timeout=3.0):
    """
    Gui du lieu hoc phi sang Finance API.

    Tra ve:
        (status_code, response_json)

    Loi:
        FINANCE_UNAVAILABLE: HTTP 503
        FINANCE_REJECTED: HTTP 502
    """

    url = f"{base_url.rstrip('/')}/api/tuition-charges"

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=timeout
        )

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout
    ) as exc:

        raise AdapterError(
            "FINANCE_UNAVAILABLE",
            "Finance không phản hồi",
            503
        ) from exc

    # Chi chap nhan HTTP 200 hoac 201
    if response.status_code not in (200, 201):
        raise AdapterError(
            "FINANCE_REJECTED",
            f"Finance trả về HTTP {response.status_code}",
            502
        )

    # Doc JSON phan hoi
    try:
        response_data = response.json()

    except ValueError as exc:
        raise AdapterError(
            "FINANCE_REJECTED",
            "Finance trả về JSON không hợp lệ",
            502
        ) from exc

    return response.status_code, response_data
