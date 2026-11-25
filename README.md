# 청년 지원금·복지 혜택 AI 가이드

공공 정책 API(온통청년)로 청년정책 약 4,000개를 모으고, 사용자 조건에 맞는 정책과 자격 판단 근거, 제출 서류를 알려주는 반응형 웹 서비스다.

## 폴더 구조

```
backend/   Flask API 서버 + DB + 온통청년 수집      (백엔드)
ai/        AI 모듈: 지금은 가짜(stub) 구현          (AI)
frontend/  React(Vite): 지금은 연결 확인용 임시 화면 (프론트)
.env.example  환경변수 양식 (.env는 절대 커밋하지 않는다)
```

## 실행하기

준비물: Python 3.10 이상 권장, Node 18 이상

**처음 한 번만**
1. `.env.example`을 복사해서 `.env`로 이름을 바꾸고, `YOUTHCENTER_API_KEY=` 뒤에 키를 붙여 넣는다. 키는 [온통청년](https://www.youthcenter.go.kr) Open API에서 발급받는다.
2. 패키지를 설치한다.
   ```bash
   cd backend
   pip install -r requirements.txt
   cd ../frontend
   npm install
   ```

**매번 실행할 때**
```bash
# 터미널 1: 백엔드  → http://localhost:5000/api/health
cd backend
python run.py

# 터미널 2: 프론트  → http://localhost:5173
cd frontend
npm run dev
```

첫 `python run.py` 실행 때 DB 파일(`backend/local.db`)을 만들고 정책 데이터를 자동으로 받아온다. 약 30초에서 1분 걸리고, 그다음부터는 바로 켜진다.
DB는 SQLite라서 따로 설치할 것이 없다. 배포할 때만 `.env`의 `DATABASE_URL`에 MySQL 주소를 넣는다.

## 처리 흐름

```
[React] ──POST /api/recommend──▶ [Flask]
                                   ├─ 1) DB 필터: 나이 · 지역 · 관심 분야 · 마감 제외
                                   ├─ 2) 조건 비교: 결혼/취업/학력/소득 → 불충족이면 제외
                                   ├─ 3) ai.rank_policies(): 사용자 상황과 비슷한 순서로 정렬
                                   └─ 4) ai.judge_policies(): 현재 페이지만 10개씩 자격 판단
```

- API 명세: [backend/README.md](backend/README.md)
- AI 모듈 입출력: [ai/README.md](ai/README.md)

## 협업 규칙

- `main`에 직접 push하지 않고 브랜치를 만든 뒤 PR로 합친다. 예: `feat/recommend-ui`
- API 키는 `.env`에만 넣는다. 코드나 커밋에 넣지 않는다.
- JSON 입출력 형식을 바꿀 때는 먼저 팀에 공유한다.
