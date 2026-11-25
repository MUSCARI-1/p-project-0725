from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from . import codes


def _s(item: dict, key: str) -> str:
    v = item.get(key)
    return "" if v is None else str(v).strip()


def to_int(value) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def parse_ymd(value: str) -> Optional[date]:
    value = (value or "").strip()
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def parse_apply_period(text: str):
    if "~" not in (text or ""):
        return None, None
    start, end = (part.strip() for part in text.split("~", 1))
    return parse_ymd(start), parse_ymd(end)


def parse_datetime(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def split_codes(value: str) -> list[str]:
    return [c.strip() for c in (value or "").split(",") if c.strip()]


def parse_age(item: dict):
    # sprtTrgtAgeLmtYn은 데이터상 의미가 일관되지 않아서 숫자만 보고, 0은 제한 없음으로 본다
    lo, hi = to_int(item.get("sprtTrgtMinAge")), to_int(item.get("sprtTrgtMaxAge"))
    return (lo or None), (hi or None)


def parse_income(item: dict):
    if _s(item, "earnCndSeCd") != codes.INCOME_ANNUAL:
        return None, None
    lo, hi = to_int(item.get("earnMinAmt")), to_int(item.get("earnMaxAmt"))
    return (lo or None), (hi or None)


def parse_categories(item: dict) -> list[str]:
    seen: list[str] = []
    for part in _s(item, "lclsfNm").split(","):
        cat = codes.normalize_category(part)
        if cat and cat not in seen:
            seen.append(cat)
    return seen


def parse_regions(item: dict) -> list[str]:
    return list(dict.fromkeys(split_codes(_s(item, "zipCd"))))


_PLACEHOLDER_WORDS = ("공고", "참조", "참고", "문의", "해당", "없음", "홈페이지", "추후", "별도")
_BULLET = re.compile(r"^\s*(?:[-*•·○●□■◦▶►※ㅇ]+|\d+[.)]|[①-⑳]|[가-하][.)])\s*")
_LABEL = re.compile(r"^(?:제출\s*서류|구비\s*서류|필요\s*서류|서류)\s*[:：]\s*")


def _split_outside_parens(text: str) -> list[str]:
    parts, buf, depth = [], [], 0
    for ch in text:
        if ch in "([{（":
            depth += 1
        elif ch in ")]}）":
            depth = max(0, depth - 1)
        if ch in ",\n" and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


def split_documents(text: str) -> list[str]:
    # '공고문 참조'처럼 실제 서류명이 없으면 빈 목록을 반환한다
    text = (text or "").strip()
    if not text or text == "-":
        return []
    if len(text) <= 20 and any(w in text for w in _PLACEHOLDER_WORDS):
        return []
    docs = []
    for part in _split_outside_parens(text):
        part = _LABEL.sub("", _BULLET.sub("", part).strip()).strip()
        if part and part != "-" and part not in docs:
            docs.append(part)
    return docs


def to_policy_fields(item: dict, synced_at: datetime) -> dict:
    categories = parse_categories(item)
    min_age, max_age = parse_age(item)
    income_min, income_max = parse_income(item)
    apply_start, apply_end = parse_apply_period(_s(item, "aplyYmd"))
    return {
        "policy_id": _s(item, "plcyNo"),
        "name": _s(item, "plcyNm")[:255],
        "keywords": _s(item, "plcyKywdNm")[:500],
        "category": categories[0] if categories else "",
        "sub_category": _s(item, "mclsfNm")[:100],
        "summary": _s(item, "plcyExplnCn"),
        "support": _s(item, "plcySprtCn"),
        "apply_period_code": _s(item, "aplyPrdSeCd"),
        "apply_start": apply_start,
        "apply_end": apply_end,
        "apply_method": _s(item, "plcyAplyMthdCn"),
        "screening_method": _s(item, "srngMthdCn"),
        "documents_text": _s(item, "sbmsnDcmntCn"),
        "apply_url": _s(item, "aplyUrlAddr")[:1000],
        "ref_url": _s(item, "refUrlAddr1")[:1000],
        "ref_url2": _s(item, "refUrlAddr2")[:1000],
        "min_age": min_age,
        "max_age": max_age,
        "marital_code": _s(item, "mrgSttsCd"),
        "job_codes": _s(item, "jobCd")[:200],
        "school_codes": _s(item, "schoolCd")[:200],
        "major_codes": _s(item, "plcyMajorCd")[:200],
        "special_codes": _s(item, "sbizCd")[:200],
        "income_cond_code": _s(item, "earnCndSeCd"),
        "income_min": income_min,
        "income_max": income_max,
        "income_text": _s(item, "earnEtcCn"),
        "extra_qualification": _s(item, "addAplyQlfcCndCn"),
        "excluded_targets": _s(item, "ptcpPrpTrgtCn"),
        "etc": _s(item, "etcMttrCn"),
        "supervising_org": _s(item, "sprvsnInstCdNm")[:255],
        "operating_org": _s(item, "operInstCdNm")[:255],
        "raw": item,
        "source_updated_at": parse_datetime(_s(item, "lastMdfcnDt")),
        "synced_at": synced_at,
    }
