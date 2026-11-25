# 백엔드는 아래 함수 3개만 호출한다. 실제 구현을 만들면 import만 바꾸면 된다. (입출력 형식은 README.md)
from .stub import answer_question, judge_policies, rank_policies

__all__ = ["rank_policies", "judge_policies", "answer_question"]
