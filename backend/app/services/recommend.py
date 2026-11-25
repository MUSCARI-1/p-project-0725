from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select

from ..extensions import db
from ..models import Policy, PolicyCategory, PolicyRegion
from . import ai_adapter, regions, rules, serializers


def _candidate_rows(profile: dict, today: date):
    age = profile["age"]
    q = select(
        Policy.policy_id,
        Policy.min_age,
        Policy.max_age,
        Policy.marital_code,
        Policy.job_codes,
        Policy.school_codes,
        Policy.income_cond_code,
        Policy.income_min,
        Policy.income_max,
        Policy.income_text,
    ).where(
        serializers.not_closed_clause(today),
        or_(Policy.min_age.is_(None), Policy.min_age <= age),
        or_(Policy.max_age.is_(None), Policy.max_age >= age),
    )
    if profile.get("region_code"):
        q = q.where(
            Policy.policy_id.in_(
                select(PolicyRegion.policy_id).where(
                    PolicyRegion.region_code.in_(regions.match_codes(profile["region_code"]))
                )
            )
        )
    if profile.get("categories"):
        q = q.where(
            Policy.policy_id.in_(
                select(PolicyCategory.policy_id).where(PolicyCategory.category.in_(profile["categories"]))
            )
        )
    q = q.order_by(Policy.apply_end.is_(None), Policy.apply_end, Policy.policy_id.desc())
    return db.session.execute(q).all()


def recommend(profile: dict, today: date, batch_size: int) -> dict:
    region_matched = True if profile.get("region_code") else None

    candidate_ids: list[str] = []
    rule_checks: dict[str, list[dict]] = {}
    for row in _candidate_rows(profile, today):
        reasons = rules.check_conditions(profile, row, region_matched)
        if rules.has_unmet(reasons):
            continue
        candidate_ids.append(row.policy_id)
        rule_checks[row.policy_id] = reasons

    page, size = profile["page"], profile["size"]
    ranked = ai_adapter.rank_policies(profile, candidate_ids)
    page_ids = ranked[(page - 1) * size : page * size]

    policies = {p.policy_id: p for p in db.session.scalars(select(Policy).where(Policy.policy_id.in_(page_ids)))}

    results = []
    for i in range(0, len(page_ids), batch_size):
        chunk = [pid for pid in page_ids[i : i + batch_size] if pid in policies]
        ai_input = [{**serializers.policy_for_ai(policies[pid]), "rule_checks": rule_checks[pid]} for pid in chunk]
        judged = ai_adapter.judge_policies(profile, ai_input)
        for pid in chunk:
            j = judged[pid]
            if j["eligibility"] == "ineligible":
                continue
            p = policies[pid]
            results.append(
                {
                    "policy_id": p.policy_id,
                    "name": p.name,
                    "category": p.category,
                    "sub_category": p.sub_category,
                    "summary": p.summary,
                    "support": p.support,
                    "eligibility": j["eligibility"],
                    "reasons": j["reasons"],
                    "documents": j["documents"],
                    "apply_method": p.apply_method,
                    "apply_status": serializers.apply_status(p, today),
                    "apply_period": serializers.apply_period(p),
                    "apply_url": p.apply_url,
                    "ref_url": p.ref_url,
                    "source_text": j["source_text"],
                }
            )

    # total은 AI 판단 전 후보 수라서 AI가 뺀 정책은 반영되지 않는다
    return {"total": len(candidate_ids), "page": page, "size": size, "results": results}
