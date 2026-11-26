from __future__ import annotations  # 타입 표시를 최신 문법으로 쓰기 위한 코드입니다

import hashlib  # 캐시 열쇠(같은 질문인지 구분하는 지문)를 만들기 위한 모듈입니다
import logging  # 실패 이유를 화면(로그)에 남기기 위한 모듈입니다
import re  # 조건 단어를 찾기 위한 정규식 모듈입니다
import threading  # 여러 요청이 동시에 캐시를 건드려도 안전하게 하기 위한 모듈입니다
import time  # 캐시 유효 시간을 재기 위한 모듈입니다
from collections import OrderedDict  # 오래된 캐시부터 지우기 위해 순서를 기억하는 dict입니다
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


CACHE_TTL = 60 * 60  # 판단 결과를 1시간 동안 재사용합니다 (정책은 하루 한 번 바뀌므로 충분히 짧음)
CACHE_MAX = 5000  # 캐시에 최대 5000개까지만 저장하고, 넘으면 가장 오래된 것부터 지웁니다
_cache: OrderedDict[str, tuple[float, Judgment]] = OrderedDict()  # {지문: (저장 시각, 판단 결과)} 형태의 캐시입니다
_lock = threading.Lock()  # 캐시를 한 번에 한 요청만 고치게 하는 자물쇠입니다


def _cache_key(text: str) -> str:  # AI에게 보낼 글로 캐시 열쇠를 만드는 함수입니다
    return hashlib.sha1(text.encode("utf-8")).hexdigest()  # 사용자 조건·정책 내용·백엔드 판정이 하나라도 다르면 열쇠도 달라집니다


def _cache_get(key: str) -> Judgment | None:  # 캐시에서 판단 결과를 꺼내는 함수입니다
    with _lock:  # 다른 요청과 겹치지 않게 잠그고
        hit = _cache.get(key)  # 열쇠로 찾아봅니다
        if not hit:  # 없으면
            return None  # 없다고 알려 줍니다
        saved_at, judgment = hit  # 저장 시각과 결과를 꺼냅니다
        if time.time() - saved_at > CACHE_TTL:  # 1시간이 지났으면
            del _cache[key]  # 오래된 결과라서 지우고
            return None  # 없다고 알려 줍니다 (다시 AI에게 물어봄)
        _cache.move_to_end(key)  # 최근에 쓴 것으로 표시해서 늦게 지워지게 합니다
        return judgment  # 저장해 둔 판단 결과를 돌려줍니다


def _cache_put(key: str, judgment: Judgment) -> None:  # 판단 결과를 캐시에 넣는 함수입니다
    with _lock:  # 다른 요청과 겹치지 않게 잠그고
        _cache[key] = (time.time(), judgment)  # 지금 시각과 함께 저장합니다
        _cache.move_to_end(key)  # 가장 최근 것으로 표시합니다
        while len(_cache) > CACHE_MAX:  # 최대 개수를 넘으면
            _cache.popitem(last=False)  # 가장 오래된 것부터 지웁니다


NARRATIVE = ("income_text", "extra_qualification", "excluded_targets")  # AI가 읽어야 하는 '글로 적힌 조건' 칸들입니다 (소득 설명, 추가 자격, 참여 제한)


CONDITION_WORDS = re.compile(  # 정책 설명·지원 내용 안에 자격 조건이 숨어 있는지 찾는 단어 목록입니다
    r"소득|중위|무주택|주택\s*소유|세대주|별도\s*거주|거주\s*(하는|중인|자)|전입|제외|불가|미취업|구직|재학|휴학|졸업"
    r"|기혼|미혼|신혼|가구원|자산|재산|사업자"
)  # 예: 지원 내용에 '부모님과 별도 거주 무주택 청년, 중위소득 60% 이하'처럼 조건이 적힌 정책이 많아서 함께 확인합니다


def needs_ai(p: dict) -> bool:  # 이 정책에 AI 판단이 필요한지 확인하는 함수입니다
    if any(clean(p.get(k)) for k in NARRATIVE):  # 소득 설명·추가 자격·참여 제한 칸에 글이 있으면
        return True  # AI가 읽어야 합니다
    body = " ".join(clean(p.get(k)) for k in ("summary", "support", "etc"))  # 정책 설명·지원 내용·기타 안내를 합쳐서
    return bool(CONDITION_WORDS.search(body))  # 조건으로 보이는 단어가 있으면 AI가 읽고, 없으면 백엔드 규칙 판정만으로 충분합니다


def _merge(p: dict, j: Judgment | None, skipped: bool = False) -> dict:  # 백엔드 판단과 Gemini 판단을 합쳐 최종 결과를 만드는 함수입니다 (skipped=AI에 물어볼 게 없어서 건너뜀)
    rule = [dict(r) for r in p.get("rule_checks", [])]  # 백엔드가 판단한 조건들을 복사합니다
    reasons = list(rule)  # 최종 판단 목록은 백엔드 판단으로 시작합니다
    if j:  # Gemini 판단 결과가 있으면
        for r in j.reasons:  # Gemini가 판단한 조건을 하나씩 보면서
            same = next((x for x in reasons if x["condition"] == r.condition), None)  # 같은 이름의 조건이 이미 있는지 찾습니다
            if same is None:  # 처음 나온 조건이면 (예: 추가 자격)
                reasons.append(r.model_dump())  # 그대로 추가합니다
            elif same["result"] == "unknown" and r.result != "unknown":  # 백엔드는 '모름'이었는데 Gemini가 판단했으면 (예: 소득)
                same.update(r.model_dump())  # Gemini 판단으로 바꿉니다 (백엔드가 확실히 판단한 건 안 바꿈)
    elif not skipped:  # 물어봤는데 Gemini 판단이 실패해서 없으면
        reasons.append({"condition": "추가 조건", "result": "unknown", "detail": "추가 조건을 자동으로 확인하지 못했어요. 공고문을 확인해 주세요."})  # '신청 가능'으로 잘못 나가지 않게 '확인 필요' 사유를 넣습니다
    if any(r["result"] == "unmet" for r in reasons):  # 하나라도 불충족이 있으면
        eligibility = "ineligible"  # 신청 불가
    elif any(r["result"] == "unknown" for r in reasons):  # 불충족은 없지만 모르는 조건이 있으면
        eligibility = "check_needed"  # 확인 필요
    else:  # 전부 충족이면
        eligibility = "eligible"  # 신청 가능

    documents = j.documents if j and j.documents else p.get("documents", [])  # 서류 목록은 Gemini가 정리한 걸 쓰고, 없으면 백엔드가 나눠 둔 목록을 씁니다
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

    by_id: dict[str, Judgment] = {}  # 정책 번호별 판단 결과를 모아 둘 곳입니다
    keys = {p["policy_id"]: _cache_key(head + _policy_block(p)) for p in policies if needs_ai(p)}  # AI가 필요한 정책마다 캐시 열쇠를 만듭니다
    for pid, key in keys.items():  # 정책마다
        cached = _cache_get(key)  # 예전에 같은 조건으로 판단한 결과가 있는지 보고
        if cached:  # 있으면
            by_id[pid] = cached  # AI에게 다시 묻지 않고 그 결과를 씁니다 (페이지를 다시 열 때 빨라짐)
    asked = [p for p in policies if p["policy_id"] in keys and p["policy_id"] not in by_id]  # 캐시에 없는 정책만 AI에게 물어봅니다
    size = max(1, settings.JUDGE_BATCH_SIZE)  # 한 번에 묶어 물어볼 정책 수입니다
    groups = [asked[i : i + size] for i in range(0, len(asked), size)]  # 물어볼 정책을 묶음 단위로 나눕니다

    def ask(group: list[dict]) -> dict[str, Judgment]:  # 정책 한 묶음을 Gemini에게 한 번에 물어보는 함수입니다
        try:  # 실패해도 전체가 멈추지 않게 감쌉니다
            batch: Batch = runner.invoke(head + "\n\n".join(_policy_block(p) for p in group))  # 규칙 + 사용자 + 정책 묶음을 보내고 답을 받습니다
            return {j.policy_id: j for j in batch.results}  # 답을 {정책 번호: 판단} 형태로 정리합니다
        except Exception as e:  # Gemini가 끝내 실패하면 (시간 초과, 무료 한도 초과 등)
            log.warning("judge 실패 %s: %s: %s", [p["policy_id"] for p in group], type(e).__name__, e)  # 어떤 정책들이 왜 실패했는지 화면에 남깁니다
            return {}  # 판단 없음으로 두고, 백엔드 판단만으로 결과를 만듭니다

    if groups:  # 물어볼 정책이 하나라도 있으면
        with ThreadPoolExecutor(max_workers=len(groups)) as pool:  # 묶음 수만큼 동시에 요청을 보낼 준비를 합니다
            for part in pool.map(ask, groups):  # 묶음마다 동시에 판단한 결과를
                for pid, judgment in part.items():  # 정책별로
                    if pid in keys:  # 우리가 물어본 정책이면 (AI가 지어낸 번호는 무시)
                        by_id[pid] = judgment  # 결과에 넣고
                        _cache_put(keys[pid], judgment)  # 다음을 위해 캐시에도 저장합니다 (실패한 건 저장 안 함)
    return [_merge(p, by_id.get(p["policy_id"]), skipped=not needs_ai(p)) for p in policies]  # 정책마다 백엔드 판단과 합쳐서 돌려줍니다
