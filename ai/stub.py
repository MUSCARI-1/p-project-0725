# LLM 없이 백엔드·프론트 연동을 테스트하기 위한 임시 구현이다
from __future__ import annotations

import re

_TRIVIAL = re.compile(r"^\s*(-|없음|해당\s*없음|해당사항\s*없음|제한\s*없음|공고문\s*(참조|참고|확인))?\s*$")


def rank_policies(profile: dict, candidate_ids: list[str]) -> list[str]:
    return list(candidate_ids)


def judge_policies(profile: dict, policies: list[dict]) -> list[dict]:
    results = []
    for p in policies:
        reasons = list(p.get("rule_checks", []))
        source_text = ""

        extra = (p.get("extra_qualification") or "").strip()
        if extra and not _TRIVIAL.match(extra):
            reasons.append({"condition": "추가 자격", "result": "unknown", "detail": extra[:150]})
            source_text = extra[:300]

        income_reason = next((r for r in reasons if r["condition"] == "소득" and r["result"] == "unknown"), None)
        if income_reason and p.get("income_text"):
            source_text = p["income_text"]

        if any(r["result"] == "unmet" for r in reasons):
            eligibility = "ineligible"
        elif any(r["result"] == "unknown" for r in reasons):
            eligibility = "check_needed"
        else:
            eligibility = "eligible"

        results.append(
            {
                "policy_id": p["policy_id"],
                "eligibility": eligibility,
                "reasons": reasons,
                "documents": p.get("documents", []),
                "source_text": source_text,
            }
        )
    return results


def answer_question(question: str, policy: dict | None, history: list[dict]) -> dict:
    if policy is None:
        return {"answer": "(AI 연결 전 임시 답변) 정책을 선택한 뒤 질문해 주세요.", "sources": []}

    fields = ["income_text", "extra_qualification", "excluded_targets", "support", "documents_text", "apply_method", "etc"]
    words = [w for w in re.split(r"\s+", question) if len(w) >= 2]
    best, best_score = "", -1
    for f in fields:
        text = (policy.get(f) or "").strip()
        if not text:
            continue
        score = sum(1 for w in words if w[:2] in text)
        if score > best_score:
            best, best_score = text, score

    if not best:
        return {"answer": "(AI 연결 전 임시 답변) 공고문에서 관련 내용을 찾지 못했어요.", "sources": []}
    return {
        "answer": "(AI 연결 전 임시 답변) 공고문에서 관련 있어 보이는 부분이에요. 정확한 내용은 담당 기관에 확인해 주세요.",
        "sources": [{"policy_id": policy["policy_id"], "text": best[:500]}],
    }
