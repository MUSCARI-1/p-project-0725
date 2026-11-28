from .settings import GEMINI_API_KEY  # .env에 Gemini 키가 있는지 확인하려고 가져옵니다

if GEMINI_API_KEY:  # Gemini 키가 있으면
    from .service import answer_question, judge_policies, rank_policies, understand_message  # 진짜 AI 함수를 씁니다
else:  # 키가 없으면 (키 없는 팀원)
    from .stub import answer_question, judge_policies, rank_policies  # 백엔드 분이 만든 가짜 함수를 씁니다

    def understand_message(message: str) -> dict:  # 키가 없을 때 쓰는 가짜 '조건 뽑기' 함수입니다
        return {}  # 아무것도 이해하지 못한 것으로 둡니다 (화면에 '이렇게 이해했어요'가 안 나옴)

__all__ = ["rank_policies", "judge_policies", "answer_question", "understand_message"]  # 백엔드가 'import ai'로 쓸 수 있는 함수 4개입니다
