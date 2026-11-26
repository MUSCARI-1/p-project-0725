from __future__ import annotations  # 타입 표시를 최신 문법으로 쓰기 위한 코드입니다

import logging  # 실패 이유를 화면(로그)에 남기기 위한 모듈입니다

from pydantic import BaseModel, Field  # Gemini 답을 정해진 JSON 모양으로 받기 위한 도구입니다

from .llm import structured  # 대체 모델까지 포함한 Gemini 실행기를 만드는 함수를 가져옵니다
from .texts import prompt_text  # 정책 본문 만드는 함수를 가져옵니다
from .vector_store import load_by_ids, search  # 비슷한 정책 찾기, 번호로 정책 읽기 함수를 가져옵니다


log = logging.getLogger(__name__)  # 이 파일에서 쓸 로그 기록기입니다

FALLBACK = "지금은 답변을 만들 수 없어요. 잠시 후 다시 질문해 주세요."  # Gemini가 실패했을 때 사용자에게 보여 줄 문장입니다


class Source(BaseModel):  # 답변 근거 하나의 모양입니다
    policy_id: str  # 참고한 정책 번호
    text: str = Field(description="답변 근거가 된 원문 일부(200자 이내, 원문 그대로)")  # 참고한 원문


class Answer(BaseModel):  # 챗봇 답 전체의 모양입니다
    answer: str  # 답변 글
    sources: list[Source]  # 근거 목록


SYSTEM = """너는 청년정책 상담 챗봇이다.
규칙:
1. 아래 [정책 원문]에 있는 내용만 근거로 답한다.
2. 원문에서 확인할 수 없는 내용은 '공고문에서 확인되지 않아요. 담당 기관에 문의해 보세요.'처럼 솔직하게 말한다.
3. 3~4문장 이내로 짧고 쉬운 한국어 존댓말로 답한다.
4. sources에는 실제로 참고한 정책의 policy_id와 원문 일부를 넣는다. 참고한 게 없으면 빈 목록."""  # 챗봇 규칙(프롬프트)입니다


def answer_question(question: str, policy: dict | None, history: list[dict]) -> dict:  # 챗봇 질문에 답하는 함수입니다
    policies = [policy] if policy else load_by_ids(search(question, k=3))  # 고른 정책이 있으면 그것만, 없으면 질문과 비슷한 정책 3개를 찾습니다
    context = "\n\n".join(f"[정책 원문]\n{prompt_text(p)}" for p in policies) or "(관련 정책을 찾지 못함)"  # 정책 원문을 프롬프트용 글로 합칩니다
    talk = "\n".join(  # 이전 대화를 글로 만듭니다
        f"{'사용자' if h.get('role') == 'user' else '챗봇'}: {h.get('content', '')}" for h in (history or [])[-6:]  # 최근 6개 대화만 씁니다
    )
    prompt = f"{SYSTEM}\n\n{context}\n\n[이전 대화]\n{talk or '(없음)'}\n\n[질문]\n{question}"  # 규칙 + 정책 원문 + 이전 대화 + 질문을 합칩니다
    try:  # 실패해도 서버가 멈추지 않게 감쌉니다
        result: Answer = structured(Answer).invoke(prompt)  # Gemini에게 보내고 정해진 모양(Answer)으로 답을 받는 코드입니다 (바쁘면 대체 모델 사용)
    except Exception as e:  # Gemini가 끝내 실패하면 (시간 초과, 무료 한도 초과 등)
        log.warning("chat 실패: %s: %s", type(e).__name__, e)  # 왜 실패했는지 화면에 남깁니다
        return {"answer": FALLBACK, "sources": []}  # 안내 문장만 돌려줍니다
    allowed = {p["policy_id"] for p in policies}  # 실제로 보여 준 정책 번호들입니다
    return {  # 백엔드가 기대하는 모양으로 돌려줍니다
        "answer": result.answer,  # 답변 글
        "sources": [s.model_dump() for s in result.sources if s.policy_id in allowed],  # 보여 준 정책의 근거만 남깁니다 (지어낸 번호 제거)
    }
