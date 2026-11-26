from __future__ import annotations  # 타입 표시를 최신 문법으로 쓰기 위한 코드입니다

import sys  # 걸린 시간을 터미널에 출력하기 위한 모듈입니다
import time  # 걸린 시간을 재기 위한 모듈입니다

from . import vector_store  # 정렬(의미 검색) 기능을 가져옵니다
from .chat import answer_question as _answer  # 챗봇 함수를 가져옵니다
from .judge import judge_policies as _judge  # 자격 판단 함수를 가져옵니다
from .judge import needs_ai  # 정책에 AI 판단이 필요한지 확인하는 함수를 가져옵니다


def _log(msg: str) -> None:  # 백엔드 터미널에 [AI] 로 시작하는 한 줄을 출력하는 함수입니다 (속도 확인용)
    print(f"[AI] {msg}", file=sys.stderr, flush=True)  # 바로 보이도록 출력합니다


def rank_policies(profile: dict, candidate_ids: list[str]) -> list[str]:  # [백엔드가 부르는 함수 1] 후보 정책을 상황에 맞는 순서로 정렬합니다
    query = (profile.get("message") or "").strip()  # 사용자가 쓴 상황 문장을 꺼냅니다
    if not query:  # 상황 문장이 없으면
        return list(candidate_ids)  # 백엔드 순서(마감 임박 순) 그대로 돌려줍니다
    t = time.time()  # 시작 시각
    ranked = vector_store.rank_ids(query, list(candidate_ids))  # 상황 문장과 비슷한 순서로 정렬합니다
    _log(f"정렬 {len(candidate_ids)}개: {time.time() - t:.1f}초")  # 몇 개를 몇 초에 정렬했는지 출력합니다
    return ranked  # 정렬 결과를 돌려줍니다


def judge_policies(profile: dict, policies: list[dict]) -> list[dict]:  # [백엔드가 부르는 함수 2] 한 페이지 정책의 자격을 판단합니다
    t = time.time()  # 시작 시각
    result = _judge(profile, policies)  # judge.py의 함수로 판단합니다
    asked = sum(1 for p in policies if needs_ai(p))  # 그중 AI가 필요했던 정책 수
    _log(f"판단 {len(policies)}개 (AI 필요 {asked}개): {time.time() - t:.1f}초")  # 몇 개를 몇 초에 판단했는지 출력합니다
    return result  # 판단 결과를 돌려줍니다


def answer_question(question: str, policy: dict | None, history: list[dict]) -> dict:  # [백엔드가 부르는 함수 3] 챗봇 질문에 답합니다
    t = time.time()  # 시작 시각
    result = _answer(question, policy, history)  # chat.py의 함수로 답합니다
    _log(f"챗봇 답변: {time.time() - t:.1f}초")  # 몇 초 걸렸는지 출력합니다
    return result  # 답변을 돌려줍니다
