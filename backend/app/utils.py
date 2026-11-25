from datetime import date, datetime, timedelta, timezone

from flask import request

from .errors import invalid

KST = timezone(timedelta(hours=9))


def today_kst() -> date:
    return datetime.now(KST).date()


def json_body() -> dict:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise invalid("요청 본문은 JSON 객체여야 합니다. (Content-Type: application/json)")
    return body


def int_value(value, name: str, default: int, lo: int, hi: int) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise invalid(f"{name} 는 정수여야 합니다.")
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise invalid(f"{name} 는 정수여야 합니다.")
    if not lo <= n <= hi:
        raise invalid(f"{name} 는 {lo}~{hi} 사이여야 합니다.")
    return n
