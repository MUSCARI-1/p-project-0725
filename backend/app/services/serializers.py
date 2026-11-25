from __future__ import annotations

from datetime import date

from sqlalchemy import and_, not_, or_

from ..models import Policy
from . import codes, transform


def apply_status(p: Policy, today: date) -> str:
    if p.apply_period_code == codes.APPLY_ALWAYS:
        return "always"
    if p.apply_period_code == codes.APPLY_CLOSED:
        return "closed"
    if p.apply_end and p.apply_end < today:
        return "closed"
    # TODO: 신청 시작 전 정책도 지금은 open으로 표시한다
    return "open"


def not_closed_clause(today: date):
    return and_(
        Policy.apply_period_code != codes.APPLY_CLOSED,
        not_(and_(Policy.apply_end.is_not(None), Policy.apply_end < today)),
    )


def closed_clause(today: date):
    return or_(
        Policy.apply_period_code == codes.APPLY_CLOSED,
        and_(Policy.apply_end.is_not(None), Policy.apply_end < today),
    )


def apply_period(p: Policy) -> str:
    if p.apply_period_code == codes.APPLY_ALWAYS:
        return "상시"
    if p.apply_start or p.apply_end:
        start = p.apply_start.isoformat() if p.apply_start else ""
        end = p.apply_end.isoformat() if p.apply_end else ""
        return f"{start} ~ {end}"
    return ""


def policy_summary(p: Policy, today: date) -> dict:
    return {
        "policy_id": p.policy_id,
        "name": p.name,
        "category": p.category,
        "sub_category": p.sub_category,
        "summary": p.summary,
        "support": p.support,
        "apply_status": apply_status(p, today),
        "apply_period": apply_period(p),
        "apply_url": p.apply_url,
        "ref_url": p.ref_url,
    }


def policy_detail(p: Policy, today: date, region_codes: list[str], categories: list[str]) -> dict:
    return {
        **policy_summary(p, today),
        "categories": categories,
        "keywords": [k.strip() for k in p.keywords.split(",") if k.strip()],
        "documents": transform.split_documents(p.documents_text),
        "documents_text": p.documents_text,
        "apply_method": p.apply_method,
        "screening_method": p.screening_method,
        "ref_url2": p.ref_url2,
        "conditions": {
            "min_age": p.min_age,
            "max_age": p.max_age,
            "region_codes": region_codes,
            "marital": codes.MARITAL_LABELS.get(p.marital_code, ""),
            "job": [codes.JOB_LABELS.get(c, c) for c in transform.split_codes(p.job_codes)],
            "education": [codes.SCHOOL_LABELS.get(c, c) for c in transform.split_codes(p.school_codes)],
            "income_min": p.income_min,
            "income_max": p.income_max,
            "income_text": p.income_text,
            "extra_qualification": p.extra_qualification,
            "excluded_targets": p.excluded_targets,
        },
        "etc": p.etc,
        "supervising_org": p.supervising_org,
        "operating_org": p.operating_org,
        "updated_at": p.source_updated_at.isoformat() if p.source_updated_at else None,
    }


def policy_for_ai(p: Policy) -> dict:
    return {
        "policy_id": p.policy_id,
        "name": p.name,
        "category": p.category,
        "sub_category": p.sub_category,
        "summary": p.summary,
        "support": p.support,
        "min_age": p.min_age,
        "max_age": p.max_age,
        "income_text": p.income_text,
        "extra_qualification": p.extra_qualification,
        "excluded_targets": p.excluded_targets,
        "documents_text": p.documents_text,
        "documents": transform.split_documents(p.documents_text),
        "apply_method": p.apply_method,
        "screening_method": p.screening_method,
        "etc": p.etc,
        "ref_url": p.ref_url,
    }
