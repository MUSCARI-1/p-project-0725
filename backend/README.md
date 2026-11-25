# Backend (Flask)

실행 방법은 [루트 README](../README.md)를 참고한다.

- DB: 개발할 때는 SQLite(`backend/local.db`, 자동 생성)를 쓰고, 배포할 때는 `.env`의 `DATABASE_URL`로 MySQL을 쓴다. 코드는 그대로다.
- 정책 데이터 최신화: `flask --app run sync-policies --prune`
- DB 초기화: `local.db` 파일을 지우고 `python run.py`를 실행하면 다시 받아온다.
- 지역 목록 갱신: 공공데이터포털에서 「국토교통부_전국 법정동」 CSV를 받아 `flask --app run import-regions <CSV 경로>`를 실행한다.
- 테스트: `python -m pytest`

## 구조

```
app/
  __init__.py        create_app()
  config.py          환경변수 (.env는 레포 루트에 둔다)
  models.py          policies / policy_regions / policy_categories
  cli.py             첫 실행 자동 준비, flask sync-policies, import-regions
  data/regions.json  시도·시군구 코드 목록 (2026-06-30 법정동 기준)
  errors.py          에러 응답 형식
  api/               라우트 (meta, policies, recommend, chat)
  services/
    youthcenter.py   온통청년 API 클라이언트
    transform.py     원본 → DB 컬럼 변환 (날짜, 나이, 서류 목록 분리 등)
    sync.py          DB 저장 (upsert)
    codes.py         프론트 입력값 ↔ 온통청년 코드 매핑
    regions.py       지역 목록 읽기, 지역 코드 검증, 상위 지역까지 포함한 검색 코드 계산
    rules.py         코드값 기반 자격 체크 (나이/지역/결혼/취업/학력/소득)
    recommend.py     추천 흐름
    ai_adapter.py    ai/ 패키지 호출. AI 오류가 나면 규칙 기반 결과로 대신 응답한다
tests/
```

## API

모든 에러는 `{ "error": "INVALID_REQUEST" | "NOT_FOUND" | "INTERNAL_ERROR", "message": "..." }` 형식으로 응답한다.

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/health` | 서버와 DB 상태 |
| GET | `/api/meta` | 입력 화면용 선택지(enum, 분야), 정책 수, 마지막 수집 시각 |
| GET | `/api/regions` | 지역 선택용 시도·시군구 코드 목록 |
| POST | `/api/recommend` | 맞춤 정책 추천 (기능 1) |
| GET | `/api/policies` | 정책 목록과 검색 |
| GET | `/api/policies/<policy_id>` | 정책 상세 가이드 (기능 2) |
| POST | `/api/chat` | 정책 상담 챗봇 (기능 3) |

### POST /api/recommend

```json
{
  "birth_date": "1999-05-12",          // 필수
  "region_code": "11380",              // GET /api/regions의 시군구 코드, 없으면 지역 필터를 하지 않음
  "region_name": "서울특별시 은평구",
  "marital_status": "single",          // single | married | null
  "job_status": "unemployed",          // employed | unemployed | self_employed | startup | etc | null
  "education": "university_enrolled",  // high_school | university_enrolled | university_graduated | etc | null
  "annual_income": null,               // 만 원
  "household_size": null,
  "categories": ["주거", "일자리"],     // 일자리, 주거, 교육, 금융·복지·문화, 참여·기반 (빈 배열이면 전체)
  "message": "휴학 중이고 알바하는데 월세가 부담돼요",
  "page": 1,
  "size": 10                           // 최대 30
}
```

응답의 `results[]` 필드는 `policy_id, name, category, sub_category, summary, support, eligibility, reasons, documents, apply_method, apply_status, apply_period, apply_url, ref_url, source_text`다.

- `total`은 AI 판단 **전** 후보 수다. AI가 `ineligible`로 뺀 정책은 반영되지 않아서, 한 페이지 결과가 `size`보다 적을 수 있다.
- 마감 정책(`aplyPrdSeCd=0057003`이거나 신청 종료일이 지난 정책)은 DB 조회 단계에서 제외한다.

### GET /api/regions

```json
{
  "regions": [
    { "code": "11", "name": "서울특별시", "sigungu": [{ "code": "11380", "name": "은평구" }] },
    { "code": "41", "name": "경기도", "sigungu": [{ "code": "41597", "name": "화성시 동탄구", "parent": "41590" }] }
  ]
}
```

- 구가 있는 시(수원시, 화성시 등)는 선택지에서 빼고 구만 넣었다. `parent`는 상위 시 코드다.
- 목록에 없는 `region_code`를 보내면 `INVALID_REQUEST`로 응답한다.

### GET /api/policies

쿼리: `page`, `size`(최대 100), `category`, `region_code`, `q`(정책명·키워드 검색), `include_closed=true`

### GET /api/policies/<policy_id>

목록 필드에 더해 `documents`(체크리스트), `documents_text`(원문), `apply_method`, `screening_method`, `conditions{min_age, max_age, region_codes, marital, job, education, income_*, extra_qualification, excluded_targets}`, 기관 정보를 돌려준다.

### POST /api/chat

```json
{
  "question": "알바 소득도 포함돼요?",
  "policy_id": "20261123005400214892",
  "history": [{ "role": "user", "content": "..." }, { "role": "assistant", "content": "..." }]
}
```

응답은 `{ "answer": "...", "sources": [{ "policy_id": "...", "text": "참고한 원문" }] }` 형식이다. `policy_id`는 선택이고, `history`는 최대 20개까지 받는다.

## 데이터 메모 (온통청년 실제 데이터 확인 결과)

- `zipCd`에는 시군구 코드가 1개에서 최대 256개까지 들어 있어서 `policy_regions` 테이블로 분리했다. 전체 약 21만 행이다.
- 정책이 상위 시(예: 화성시 41590)나 시도 전체(예: 대전 30000)로 등록된 경우가 있어서, 지역으로 찾을 때는 선택한 시군구와 상위 시, 시도 코드를 같이 찾는다. 화성시 동탄구는 정확히 일치하는 정책만 찾으면 471건이고, 상위 시까지 포함하면 816건이다.
- 2026년 행정구역 개편(전남광주통합특별시, 인천 제물포·영종·서해·검단구, 화성시 4개 구)이 코드에 반영돼 있다. 개편 전 인천 코드(28110, 28140, 28260)로만 등록된 정책 5건은 지역 검색에 잡히지 않는다.
- `lclsfNm`은 옛 분류명(복지문화, 참여권리, 교육)과 새 분류명이 섞여 있고, 가운뎃점도 `･`(U+FF65)라서 5개 분류로 통일했다.
- `sprtTrgtAgeLmtYn`은 값의 의미가 일관되지 않아서 무시하고, 최소·최대 나이 숫자만 사용한다. 0은 제한 없음으로 본다.
- 제출 서류는 약 70%가 비어 있거나 "공고문 참조" 같은 문구다. 이런 경우 `documents: []`로 보낸다.
