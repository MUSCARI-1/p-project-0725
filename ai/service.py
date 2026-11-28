from __future__ import annotations  # 타입 표시를 최신 문법으로 쓰기 위한 코드입니다

import sys  # 걸린 시간을 터미널에 출력하기 위한 모듈입니다
import time  # 걸린 시간을 재기 위한 모듈입니다

from . import settings, vector_store  # 설정값, 정렬(의미 검색) 기능을 가져옵니다
from .chat import answer_question as _answer  # 챗봇 함수를 가져옵니다
from .judge import judge_policies as _judge  # 자격 판단 함수를 가져옵니다
from .judge import needs_ai  # 정책에 AI 판단이 필요한지 확인하는 함수를 가져옵니다
from .understand import understand_message  # [백엔드가 부르는 함수 4] 문장에서 조건을 뽑는 함수를 가져옵니다 (그대로 내보냄)

BOOST_WINDOW = 30  # 키워드 보정은 의미 검색 상위 30개 안에서만 합니다 (너무 먼 정책을 끌어올리지 않게)


def _log(msg: str) -> None:  # 백엔드 터미널에 [AI] 로 시작하는 한 줄을 출력하는 함수입니다 (속도 확인용)
    print(f"[AI] {msg}", file=sys.stderr, flush=True)  # 바로 보이도록 출력합니다


def rank_policies(profile: dict, candidate_ids: list[str]) -> list[str]:  # [백엔드가 부르는 함수 1] 후보 정책을 상황에 맞는 순서로 정렬합니다
    query = (profile.get("message") or "").strip()  # 사용자가 쓴 상황 문장을 꺼냅니다
    if not query:  # 상황 문장이 없으면
        return list(candidate_ids)  # 백엔드 순서(마감 임박 순) 그대로 돌려줍니다
    t = time.time()  # 시작 시각
    keywords = understand_message(query).get("keywords", []) if settings.RANK_USE_KEYWORDS else []  # (켰을 때만) 문장에서 정책 용어로 바꾼 핵심 단어를 뽑습니다 (예: 집세→월세)
    search_query = f"{query}\n핵심: {', '.join(keywords)}" if keywords else query  # 원래 문장에 핵심 단어를 덧붙여 검색합니다
    ranked = vector_store.rank_ids(search_query, list(candidate_ids))  # 의미가 비슷한 순서로 정렬합니다
    if settings.RANK_KEYWORD_BOOST:  # 키워드 보정을 켰을 때만
        ranked = _boost(ranked, keywords)  # 상위권 안에서 이름에 핵심 단어가 있는 정책을 앞으로 올립니다
    _log(f"정렬 {len(candidate_ids)}개 (핵심 단어 {keywords}): {time.time() - t:.1f}초")  # 몇 개를 몇 초에 정렬했는지 출력합니다
    return ranked  # 정렬 결과를 돌려줍니다


def _boost(ranked: list[str], keywords: list[str]) -> list[str]:  # 상위 정책 중 이름에 핵심 단어가 있는 것을 앞으로 올리는 함수입니다
    if not keywords:  # 핵심 단어가 없으면
        return ranked  # 그대로 돌려줍니다
    head, tail = ranked[:BOOST_WINDOW], ranked[BOOST_WINDOW:]  # 상위 30개와 나머지로 나눕니다
    names = vector_store.names_by_ids(head)  # 상위 30개의 정책 이름을 가져옵니다
    hit = lambda pid: any(k in names.get(pid, "") for k in keywords)  # 이름에 핵심 단어가 하나라도 있는지 확인하는 작은 함수입니다
    head = sorted(head, key=lambda pid: not hit(pid))  # 단어가 있는 정책을 앞으로 (같은 그룹 안에서는 원래 순서 유지)
    return head + tail  # 다시 합쳐서 돌려줍니다


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
