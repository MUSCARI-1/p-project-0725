# AI 모듈 (LangChain + Chroma + Gemini)

백엔드(Flask)는 이 패키지를 `import ai`로 불러서 아래 함수 3개만 호출한다.
루트 `.env`에 `GEMINI_API_KEY`가 있으면 실제 구현([service.py](service.py))을, 없으면 가짜 구현([stub.py](stub.py))을 쓴다. 그래서 키가 없는 팀원도 백엔드·프론트를 그대로 돌릴 수 있다.

## 실행 방법 (AI 담당)

1. 백엔드와 같은 가상환경에서 설치한다.
   ```bash
   pip install -r ai/requirements.txt
   ```
2. 루트 `.env`에 Gemini 키를 넣는다. 모델 이름은 필요하면 바꾼다.
   ```
   GEMINI_API_KEY=...
   # 아래는 선택. 적지 않으면 괄호 안 기본값을 쓴다.
   # GEMINI_MODEL=gemini-3.5-flash-lite       (테스트 결과 flash보다 빠르고 품질도 비슷함)
   # GEMINI_FALLBACK_MODELS=gemini-3.5-flash  (기본 모델 실패 시 대체, 쉼표로 여러 개)
   # GEMINI_THINKING_LEVEL=low                 (low=빠름, high=신중하지만 느림)
   # GEMINI_TIMEOUT=20                         (이 초를 넘으면 대체 모델로 넘어감)
   # JUDGE_BATCH_SIZE=5                        (자격 판단 때 한 번에 묶어 보낼 정책 수)
   # EMBED_MODEL=models/gemini-embedding-001
   ```
3. 백엔드를 한 번 실행해서 `backend/local.db`가 있는 상태에서 벡터 DB를 만든다. 끊겨도 다시 실행하면 이어서 한다.
   ```bash
   python -m ai.build_index --limit 50   # 테스트
   python -m ai.build_index              # 전체
   ```
4. 백엔드 없이 함수만 확인: `python -m ai.try_it`

## 파일 구성

| 파일 | 역할 |
|---|---|
| service.py | 백엔드가 부르는 함수 3개 |
| vector_store.py / build_index.py | 정책 임베딩 → Chroma 저장, 의미 순 정렬 |
| judge.py | 글로 된 조건(추가 자격·소득·참여 제한) 판단, 제출 서류 정리 |
| chat.py | 정책 원문 기반 챗봇 |
| texts.py / profile.py | 프롬프트용 문장 만들기 |
| settings.py / llm.py | 설정, Gemini 모델 |

`judge_policies`는 백엔드 `rule_checks`(나이·지역·결혼·취업·학력·소득 코드) 결과를 그대로 믿고, AI가 판단한 글 조건을 합친 뒤 eligibility를 다시 계산한다.

AI 함수에서 예외가 나도 백엔드가 규칙 기반 결과로 대신 응답하기 때문에 서비스는 멈추지 않는다 (`backend/app/services/ai_adapter.py`).

## 1. `rank_policies(profile, candidate_ids) -> list[str]`

DB 필터와 규칙 체크를 통과한 후보 `policy_id` 목록을 사용자 상황(`profile["message"]`)과 의미가 비슷한 순서로 정렬해서 돌려준다.
후보는 수백 개일 수 있다. 목록에 없는 id는 무시하고, 빠뜨린 id는 뒤에 붙인다.

## 2. `judge_policies(profile, policies) -> list[dict]`

현재 페이지 정책만 **최대 10개씩** 들어온다.

`profile` 예시:
```python
{"birth_date": "1999-05-12", "age": 27, "region_code": "11380", "region_name": "서울특별시 은평구",
 "marital_status": "single", "job_status": "unemployed", "education": "university_enrolled",
 "annual_income": None, "household_size": None, "categories": ["주거"], "message": "...", "page": 1, "size": 10}
```

`policies[i]` 예시. 백엔드가 코드값으로 미리 판단한 `rule_checks`가 같이 들어간다.
```python
{"policy_id": "...", "name": "...", "category": "주거", "sub_category": "...", "summary": "...", "support": "...",
 "min_age": 19, "max_age": 39, "income_text": "청년 5천만원 이하", "extra_qualification": "...",
 "excluded_targets": "...", "documents_text": "원문", "documents": ["백엔드가 단순 분리한 목록"],
 "apply_method": "...", "screening_method": "...", "etc": "...", "ref_url": "...",
 "rule_checks": [{"condition": "나이", "result": "met", "detail": "만 27세, 대상 19세~39세"}, ...]}
```

반환값 (정책마다 1개):
```python
{"policy_id": "...", "eligibility": "eligible" | "check_needed" | "ineligible",
 "reasons": [{"condition": "소득", "result": "met" | "unmet" | "unknown", "detail": "..."}],
 "documents": ["신청서", "주민등록등본"],   # '공고문 참조'만 있으면 []
 "source_text": "판단에 사용한 원문"}
```

## 3. `answer_question(question, policy, history) -> dict`

`policy`는 위 `policies[i]`와 같은 형식이고(`rule_checks` 제외), 정책을 고르지 않았으면 `None`이 들어온다.

```python
{"answer": "...", "sources": [{"policy_id": "...", "text": "참고한 원문"}]}
```

## 참고

- Gemini 키는 루트 `.env`의 `GEMINI_API_KEY`를 사용한다.
- 벡터 DB 파일(`chroma_db/`)은 `.gitignore`에 들어 있다.
- 최신 LangChain(1.x)은 Python 3.10 이상이 필요하다.
- 정책 원문은 DB `policies` 테이블에 있다 (개발 중에는 `backend/local.db`, SQLite). 원본 응답 전체는 `raw` 컬럼(JSON)에 있다.
