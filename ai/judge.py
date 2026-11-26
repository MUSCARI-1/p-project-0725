from __future__ import annotations  # 타입 표시를 최신 문법으로 쓰기 위한 코드입니다

import logging  # 실패 이유를 화면(로그)에 남기기 위한 모듈입니다
from concurrent.futures import ThreadPoolExecutor  # 여러 정책을 동시에 판단하기 위한 도구입니다
from typing import Literal  # 정해진 값만 허용하는 타입을 만들기 위한 도구입니다

from pydantic import BaseModel, Field  # Gemini 답을 정해진 JSON 모양으로 받기 위한 도구입니다

from . import settings  # 묶음 크기 같은 설정값을 가져옵니다
from .llm import structured  # 대체 모델까지 포함한 Gemini 실행기를 만드는 함수를 가져옵니다
from .profile import describe  # 사용자 조건을 문장으로 바꾸는 함수를 가져옵니다
from .texts import clean, prompt_text  # 빈 글 정리 함수, 정책 본문 만드는 함수를 가져옵니다

log = logging.getLogger(__name__)  # 이 파일에서 쓸 로그 기록기입니다

Result = Literal["met", "unmet", "unknown"]  # 조건 판단 결과는 이 세 가지만 허용합니다


class Reason(BaseModel):  # 조건 하나에 대한 판단 결과의 모양입니다
    condition: str = Field(description="조건 이름. 예: 추가 자격, 소득, 참여 제한, 거주 기간")  # 조건 이름
    result: Result = Field(description="met=충족, unmet=불충족, unknown=사용자 정보로 알 수 없음")  # 판단 결과
    detail: str = Field(description="판단 근거를 한 문장으로. 사용자에게 그대로 보여준다")  # 판단 이유


class Judgment(BaseModel):  # 정책 하나에 대한 Gemini 답의 모양입니다
    policy_id: str  # 정책 번호
    reasons: list[Reason] = Field(description="글로 적힌 조건에 대한 판단만. 조건이 없으면 빈 목록")  # 조건별 판단 목록
    documents: list[str] = Field(description="제출 서류를 하나씩 나눈 목록. 공고문 참조뿐이면 빈 목록")  # 제출 서류 목록
    source_text: str = Field(description="판단에 가장 중요했던 공고문 원문 일부(200자 이내, 원문 그대로)")  # 근거 원문


class Batch(BaseModel):  # 정책 여러 개(한 페이지)에 대한 Gemini 답 전체의 모양입니다
    results: list[Judgment]  # 정책별 판단 목록


SYSTEM = """너는 청년정책 신청 자격을 판단하는 도우미다.
규칙:
1. 정책 원문에 적힌 내용만 근거로 판단한다. 원문에 없는 조건을 지어내지 않는다.
2. '이미 판단된 조건'(나이, 지역, 결혼, 취업, 학력 등)은 다시 판단하지 않는다.
3. 원문의 '추가 신청 자격', '소득 조건', '참여 제한 대상'에 실제 조건이 있을 때만 reasons에 넣는다.
4. 사용자 정보가 없어서 확인할 수 없으면 반드시 unknown으로 한다. 추측해서 met이나 unmet으로 하지 않는다.
5. 사용자 정보와 원문이 명확히 어긋날 때만 unmet으로 한다.
6. detail은 '~이 필요해요', '~라서 충족해요'처럼 짧고 쉬운 한국어로 쓴다.
7. documents는 제출 서류 원문을 서류 단위로 나눈다. '공고문 참조'처럼 실제 서류가 없으면 빈 목록.
8. 입력받은 모든 정책에 대해 policy_id를 그대로 써서 결과를 하나씩 돌려준다."""  # Gemini에게 주는 규칙(프롬프트)입니다


def _policy_block(p: dict) -> str:  # 정책 하나를 프롬프트에 넣을 글로 만드는 함수입니다
    done = "\n".join(f"  · {r['condition']}: {r['result']} ({r.get('detail', '')})" for r in p.get("rule_checks", []))  # 백엔드가 이미 판단한 조건들을 한 줄씩 적습니다
    return f"[정책]\n{prompt_text(p)}\n- 이미 판단된 조건:\n{done or '  · 없음'}"  # 정책 본문 + 이미 판단된 조건을 합칩니다


def _merge(p: dict, j: Judgment | None) -> dict:  # 백엔드 판단과 Gemini 판단을 합쳐 최종 결과를 만드는 함수입니다
    rule = [dict(r) for r in p.get("rule_checks", [])]  # 백엔드가 판단한 조건들을 복사합니다
    reasons = list(rule)  # 최종 판단 목록은 백엔드 판단으로 시작합니다
    if j:  # Gemini 판단 결과가 있으면
        for r in j.reasons:  # Gemini가 판단한 조건을 하나씩 보면서
            same = next((x for x in reasons if x["condition"] == r.condition), None)  # 같은 이름의 조건이 이미 있는지 찾습니다
            if same is None:  # 처음 나온 조건이면 (예: 추가 자격)
                reasons.append(r.model_dump())  # 그대로 추가합니다
            elif same["result"] == "unknown" and r.result != "unknown":  # 백엔드는 '모름'이었는데 Gemini가 판단했으면 (예: 소득)
                same.update(r.model_dump())  # Gemini 판단으로 바꿉니다 (백엔드가 확실히 판단한 건 안 바꿈)
    else:  # Gemini 판단이 실패해서 없으면
        reasons.append({"condition": "추가 조건", "result": "unknown", "detail": "추가 조건을 자동으로 확인하지 못했어요. 공고문을 확인해 주세요."})  # '신청 가능'으로 잘못 나가지 않게 '확인 필요' 사유를 넣습니다
    if any(r["result"] == "unmet" for r in reasons):  # 하나라도 불충족이 있으면
        eligibility = "ineligible"  # 신청 불가
    elif any(r["result"] == "unknown" for r in reasons):  # 불충족은 없지만 모르는 조건이 있으면
        eligibility = "check_needed"  # 확인 필요
    else:  # 전부 충족이면
        eligibility = "eligible"  # 신청 가능

    documents = j.documents if j else p.get("documents", [])  # 서류 목록은 Gemini가 정리한 걸 쓰고, 없으면 백엔드 목록을 씁니다
    if not clean(p.get("documents_text")):  # 원문이 '공고문 참조'처럼 실제 서류가 없으면
        documents = []  # 빈 목록으로 합니다
    return {  # 백엔드가 기대하는 모양으로 결과를 돌려줍니다
        "policy_id": p["policy_id"],  # 정책 번호
        "eligibility": eligibility,  # 최종 판단
        "reasons": reasons,  # 조건별 판단
        "documents": [d.strip() for d in documents if d and d.strip()],  # 빈 칸을 뺀 서류 목록
        "source_text": (j.source_text if j else "")[:300],  # 근거 원문 (300자까지)
    }


def judge_policies(profile: dict, policies: list[dict]) -> list[dict]:  # 한 페이지(최대 10개) 정책의 자격을 판단하는 함수입니다
    if not policies:  # 정책이 없으면
        return []  # 빈 목록을 돌려줍니다
    head = f"{SYSTEM}\n\n[사용자]\n{describe(profile)}\n\n"  # 모든 정책에 공통으로 붙는 규칙 + 사용자 정보입니다
    runner = structured(Batch)  # 정해진 JSON 모양(Batch)으로 답을 받는 Gemini 실행기를 한 번만 만듭니다 (바쁘면 대체 모델 사용)

    size = max(1, settings.JUDGE_BATCH_SIZE)  # 한 번에 묶어 물어볼 정책 수입니다 (기본 5개)
    groups = [policies[i : i + size] for i in range(0, len(policies), size)]  # 정책 목록을 묶음 단위로 나눕니다 (10개면 5개씩 2묶음)

    def ask(group: list[dict]) -> dict[str, Judgment]:  # 정책 한 묶음을 Gemini에게 한 번에 물어보는 함수입니다
        try:  # 실패해도 전체가 멈추지 않게 감쌉니다
            batch: Batch = runner.invoke(head + "\n\n".join(_policy_block(p) for p in group))  # 규칙 + 사용자 + 정책 묶음을 보내고 답을 받습니다
            return {j.policy_id: j for j in batch.results}  # 답을 {정책 번호: 판단} 형태로 정리합니다
        except Exception as e:  # Gemini가 끝내 실패하면 (시간 초과, 무료 한도 초과 등)
            log.warning("judge 실패 %s: %s: %s", [p["policy_id"] for p in group], type(e).__name__, e)  # 어떤 정책들이 왜 실패했는지 화면에 남깁니다
            return {}  # 판단 없음으로 두고, 백엔드 판단만으로 결과를 만듭니다

    with ThreadPoolExecutor(max_workers=len(groups)) as pool:  # 묶음 수만큼 동시에 요청을 보낼 준비를 합니다
        by_id: dict[str, Judgment] = {}  # 모든 묶음의 판단을 모아 둘 곳입니다
        for part in pool.map(ask, groups):  # 묶음마다 동시에 판단한 결과를
            by_id.update(part)  # 하나로 합칩니다
    return [_merge(p, by_id.get(p["policy_id"])) for p in policies]  # 정책마다 백엔드 판단과 합쳐서 돌려줍니다
