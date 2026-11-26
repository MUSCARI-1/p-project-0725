from __future__ import annotations  # 타입 표시를 최신 문법으로 쓰기 위한 코드입니다

from . import vector_store  # 정렬(의미 검색) 기능을 가져옵니다
from .chat import answer_question as _answer  # 챗봇 함수를 가져옵니다
from .judge import judge_policies as _judge  # 자격 판단 함수를 가져옵니다


def rank_policies(profile: dict, candidate_ids: list[str]) -> list[str]:  # [백엔드가 부르는 함수 1] 후보 정책을 상황에 맞는 순서로 정렬합니다
    query = (profile.get("message") or "").strip()  # 사용자가 쓴 상황 문장을 꺼냅니다
    if not query:  # 상황 문장이 없으면
        return list(candidate_ids)  # 백엔드 순서(마감 임박 순) 그대로 돌려줍니다
    return vector_store.rank_ids(query, list(candidate_ids))  # 상황 문장과 비슷한 순서로 정렬해서 돌려줍니다


def judge_policies(profile: dict, policies: list[dict]) -> list[dict]:  # [백엔드가 부르는 함수 2] 한 페이지 정책의 자격을 판단합니다
    return _judge(profile, policies)  # judge.py의 함수에 그대로 넘깁니다


def answer_question(question: str, policy: dict | None, history: list[dict]) -> dict:  # [백엔드가 부르는 함수 3] 챗봇 질문에 답합니다
    return _answer(question, policy, history)  # chat.py의 함수에 그대로 넘깁니다
