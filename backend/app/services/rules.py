# 코드값으로 판단할 수 있는 조건만 확인한다. 자유 텍스트 조건은 AI가 판단한다.
# 결혼/취업/학력은 정책에 제한이 있을 때만 reason을 만든다.
from __future__ import annotations

from typing import Optional

from . import codes


def _reason(condition: str, result: str, detail: str) -> dict:
    return {"condition": condition, "result": result, "detail": detail}


def _labels(code_list, labels: dict) -> str:
    return ", ".join(labels.get(c, c) for c in code_list)


def check_age(age: int, min_age, max_age) -> dict:
    if min_age is None and max_age is None:
        return _reason("나이", "met", "나이 제한 없음")
    lo = f"{min_age}세" if min_age is not None else ""
    hi = f"{max_age}세" if max_age is not None else ""
    ok = (min_age is None or age >= min_age) and (max_age is None or age <= max_age)
    return _reason("나이", "met" if ok else "unmet", f"만 {age}세, 대상 {lo}~{hi}")


def check_region(region_code: Optional[str], matched: Optional[bool]) -> dict:
    if not region_code:
        return _reason("지역", "unknown", "거주 지역 정보 없음")
    if matched:
        return _reason("지역", "met", "사용자 지역이 대상 지역에 포함됨")
    return _reason("지역", "unmet", "사용자 지역이 대상 지역에 포함되지 않음")


def _check_code_set(condition, user_value, user_codes, policy_codes_csv, any_code, etc_code, labels):
    policy_codes = [c.strip() for c in (policy_codes_csv or "").split(",") if c.strip()]
    if not policy_codes or any_code in policy_codes:
        return None
    target = f"대상: {_labels(policy_codes, labels)}"
    if user_value is None:
        return _reason(condition, "unknown", f"{condition} 정보 없음, {target}")
    if user_codes & set(policy_codes):
        return _reason(condition, "met", target)
    if user_value == "etc" or etc_code in policy_codes:
        return _reason(condition, "unknown", f"{target} (확인 필요)")
    return _reason(condition, "unmet", target)


def check_marital(marital_status, policy_code) -> Optional[dict]:
    if not policy_code or policy_code == codes.MARITAL_ANY:
        return None
    target = f"대상: {codes.MARITAL_LABELS.get(policy_code, policy_code)}"
    if marital_status is None:
        return _reason("결혼", "unknown", f"결혼 여부 정보 없음, {target}")
    ok = codes.MARITAL_MAP.get(marital_status) == policy_code
    return _reason("결혼", "met" if ok else "unmet", target)


def check_income(annual_income, cond_code, income_min, income_max, income_text) -> dict:
    if cond_code == codes.INCOME_ANNUAL and (income_min is not None or income_max is not None):
        lo = f"{income_min:,}만원" if income_min is not None else ""
        hi = f"{income_max:,}만원" if income_max is not None else ""
        target = f"연소득 {lo}~{hi} 조건"
        if annual_income is None:
            return _reason("소득", "unknown", f"{target}, 소득 정보 없음")
        ok = (income_min is None or annual_income >= income_min) and (income_max is None or annual_income <= income_max)
        return _reason("소득", "met" if ok else "unmet", f"{target}, 입력 연소득 {annual_income:,}만원")
    if cond_code == codes.INCOME_ETC:
        text = (income_text or "").strip()
        if text and text != "-":
            return _reason("소득", "unknown", text[:200])
        return _reason("소득", "unknown", "별도 소득 기준 있음, 공고문 확인 필요")
    return _reason("소득", "met", "소득 조건 없음")


def check_conditions(profile: dict, policy, region_matched: Optional[bool]) -> list[dict]:
    reasons = [
        check_age(profile["age"], policy.min_age, policy.max_age),
        check_region(profile.get("region_code"), region_matched),
        check_marital(profile.get("marital_status"), policy.marital_code),
        _check_code_set(
            "취업 상태",
            profile.get("job_status"),
            codes.JOB_MAP.get(profile.get("job_status"), set()),
            policy.job_codes,
            codes.JOB_ANY,
            codes.JOB_ETC,
            codes.JOB_LABELS,
        ),
        _check_code_set(
            "학력",
            profile.get("education"),
            codes.SCHOOL_MAP.get(profile.get("education"), set()),
            policy.school_codes,
            codes.SCHOOL_ANY,
            codes.SCHOOL_ETC,
            codes.SCHOOL_LABELS,
        ),
        check_income(
            profile.get("annual_income"),
            policy.income_cond_code,
            policy.income_min,
            policy.income_max,
            policy.income_text,
        ),
    ]
    return [r for r in reasons if r is not None]


def has_unmet(reasons: list[dict]) -> bool:
    return any(r["result"] == "unmet" for r in reasons)
