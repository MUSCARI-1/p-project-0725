# AI 모듈이 오류를 내거나 형식이 다른 값을 줘도 응답이 깨지지 않도록 여기서 정리한다
from __future__ import annotations

import logging
import sys

from ..config import ROOT_DIR

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import ai  # noqa: E402

log = logging.getLogger(__name__)

ELIGIBILITY = {"eligible", "check_needed", "ineligible"}
REASON_RESULTS = {"met", "unmet", "unknown"}


def rank_policies(profile: dict, candidate_ids: list[str]) -> list[str]:
    if not candidate_ids:
        return []
    try:
        ranked = list(ai.rank_policies(profile, list(candidate_ids)))
    except Exception:
        log.exception("ai.rank_policies 실패 → 기본 순서 사용")
        return list(candidate_ids)
    allowed = set(candidate_ids)
    ordered = [i for i in dict.fromkeys(ranked) if i in allowed]
    seen = set(ordered)
    return ordered + [i for i in candidate_ids if i not in seen]


def _clean_judgment(j: dict, fallback: dict) -> dict:
    eligibility = j.get("eligibility")
    if eligibility not in ELIGIBILITY:
        eligibility = "check_needed"
    reasons = []
    for r in j.get("reasons") or []:
        if isinstance(r, dict) and r.get("result") in REASON_RESULTS:
            reasons.append(
                {"condition": str(r.get("condition", "")), "result": r["result"], "detail": str(r.get("detail", ""))}
            )
    docs = j.get("documents")
    return {
        "eligibility": eligibility,
        "reasons": reasons or fallback["reasons"],
        "documents": [str(d) for d in docs] if isinstance(docs, list) else fallback["documents"],
        "source_text": str(j.get("source_text") or ""),
    }


def judge_policies(profile: dict, policies: list[dict]) -> dict[str, dict]:
    fallbacks = {
        p["policy_id"]: {
            "eligibility": "check_needed",
            "reasons": p.get("rule_checks", []),
            "documents": p.get("documents", []),
            "source_text": "",
        }
        for p in policies
    }
    try:
        judged = ai.judge_policies(profile, policies) or []
    except Exception:
        log.exception("ai.judge_policies 실패 → 규칙 기반 결과 사용")
        return fallbacks
    out = dict(fallbacks)
    for j in judged:
        pid = j.get("policy_id") if isinstance(j, dict) else None
        if pid in fallbacks:
            out[pid] = _clean_judgment(j, fallbacks[pid])
    return out


def answer_question(question: str, policy: dict | None, history: list[dict]) -> dict:
    result = ai.answer_question(question, policy, history) or {}
    # name(정책 이름), url(공고 링크)은 화면에서 근거를 하이퍼링크로 보여주기 위해 함께 넘긴다
    sources = [
        {
            "policy_id": str(s.get("policy_id", "")),
            "text": str(s.get("text", "")),
            "name": str(s.get("name") or ""),
            "url": str(s.get("url") or ""),
        }
        for s in result.get("sources") or []
        if isinstance(s, dict)
    ]
    return {"answer": str(result.get("answer", "")), "sources": sources}
