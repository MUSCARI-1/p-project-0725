from __future__ import annotations

from datetime import date, datetime

from ..errors import invalid
from ..utils import int_value
from . import codes, regions


def calc_age(birth: date, today: date) -> int:
    # 만 나이
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _optional_enum(body: dict, key: str):
    value = body.get(key)
    if value is None:
        return None
    allowed = codes.REQUEST_ENUMS[key]
    if value not in allowed:
        raise invalid(f"{key} 는 {', '.join(allowed)} 중 하나여야 합니다.")
    return value


def _optional_int(body: dict, key: str, minimum: int):
    value = body.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise invalid(f"{key} 는 {minimum} 이상의 정수 또는 null 이어야 합니다.")
    return value


def parse_recommend_request(body: dict, today: date, default_size: int, max_size: int) -> dict:
    birth_raw = body.get("birth_date")
    if not isinstance(birth_raw, str):
        raise invalid("birth_date 는 필수입니다. (YYYY-MM-DD)")
    try:
        birth = datetime.strptime(birth_raw, "%Y-%m-%d").date()
    except ValueError:
        raise invalid("birth_date 형식이 올바르지 않습니다.")
    if birth > today:
        raise invalid("birth_date 가 미래 날짜입니다.")

    region_code = body.get("region_code")
    if region_code in (None, ""):
        region_code = None
    elif not (isinstance(region_code, str) and region_code.isdigit() and len(region_code) == 5):
        raise invalid("region_code 는 5자리 숫자 문자열이어야 합니다.")
    elif not regions.is_valid(region_code):
        raise invalid(f"region_code '{region_code}' 는 지역 목록에 없습니다. (GET /api/regions 참고)")

    raw_categories = body.get("categories") or []
    if not isinstance(raw_categories, list) or not all(isinstance(c, str) for c in raw_categories):
        raise invalid("categories 는 문자열 배열이어야 합니다.")
    categories = []
    for c in raw_categories:
        norm = codes.normalize_category(c)
        if norm not in codes.CATEGORIES:
            raise invalid(f"categories 값 '{c}' 는 {', '.join(codes.CATEGORIES)} 중 하나여야 합니다.")
        if norm not in categories:
            categories.append(norm)

    message = body.get("message")
    if message is not None and not isinstance(message, str):
        raise invalid("message 는 문자열이어야 합니다.")
    message = (message or "").strip()
    if len(message) > 1000:
        raise invalid("message 는 1000자 이하로 입력해 주세요.")

    region_name = body.get("region_name")
    return {
        "birth_date": birth.isoformat(),
        "age": calc_age(birth, today),
        "region_code": region_code,
        "region_name": region_name if isinstance(region_name, str) else None,
        "marital_status": _optional_enum(body, "marital_status"),
        "job_status": _optional_enum(body, "job_status"),
        "education": _optional_enum(body, "education"),
        "annual_income": _optional_int(body, "annual_income", 0),
        "household_size": _optional_int(body, "household_size", 1),
        "categories": categories,
        "message": message,
        "page": int_value(body.get("page"), "page", 1, 1, 10_000),
        "size": int_value(body.get("size"), "size", default_size, 1, max_size),
    }


def parse_chat_request(body: dict) -> dict:
    question = body.get("question")
    if not isinstance(question, str) or not question.strip():
        raise invalid("question 은 필수입니다.")
    if len(question) > 500:
        raise invalid("question 은 500자 이하로 입력해 주세요.")

    policy_id = body.get("policy_id")
    if policy_id is not None and (not isinstance(policy_id, str) or not policy_id.strip()):
        raise invalid("policy_id 는 문자열이어야 합니다.")

    history = body.get("history") or []
    if not isinstance(history, list) or len(history) > 20:
        raise invalid("history 는 최대 20개의 배열이어야 합니다.")
    for h in history:
        if not (isinstance(h, dict) and h.get("role") in ("user", "assistant") and isinstance(h.get("content"), str)):
            raise invalid("history 항목은 { role: user|assistant, content: 문자열 } 형식이어야 합니다.")

    return {
        "question": question.strip(),
        "policy_id": policy_id.strip() if policy_id else None,
        "history": [{"role": h["role"], "content": h["content"]} for h in history],
    }
