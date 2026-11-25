# Frontend (React + Vite)

지금 있는 `src/App.jsx`는 백엔드 연결 확인용 임시 화면이다. 실제 화면은 자유롭게 새로 만든다.

- API 호출은 [src/api.js](src/api.js)의 함수(`recommend`, `getPolicy`, `searchPolicies`, `chat`, `getMeta`)를 쓴다.
- 개발 중에는 `vite.config.js`의 proxy 설정으로 `/api/...` 요청이 Flask(5000번)로 바로 넘어간다. 백엔드를 먼저 실행해 둔다.
- 요청·응답 형식은 [backend/README.md](../backend/README.md)를 참고한다.
- 지역 선택 목록은 `getRegions()`(`GET /api/regions`)로 받는다. 시도를 고르면 그 아래 `sigungu` 목록을 보여주고, 고른 시군구의 `code`를 `region_code`로 보낸다.

```bash
npm install
npm run dev     # http://localhost:5173
```
