from google import genai  # Gemini 공식 라이브러리입니다 (langchain-google-genai 설치 때 같이 깔림)

from . import settings  # .env의 Gemini 키를 가져옵니다

if __name__ == "__main__":  # 'python -m ai.check_models'로 직접 실행했을 때만 아래가 돌아갑니다
    client = genai.Client(api_key=settings.GEMINI_API_KEY)  # 내 키로 Gemini에 접속하는 코드입니다
    names = []  # 답변 생성이 가능한 모델 이름을 모을 목록입니다
    for m in client.models.list():  # 내 키로 쓸 수 있는 모델 목록을 하나씩 보면서
        actions = getattr(m, "supported_actions", None) or []  # 그 모델이 할 수 있는 일 목록입니다
        if "generateContent" in actions and "flash" in m.name:  # 답변 생성이 되는 Flash 계열 모델만
            names.append(m.name.replace("models/", ""))  # 이름을 모읍니다
    print("사용 가능한 Flash 모델:", ", ".join(names) or "(없음)")  # 목록을 출력합니다

    for name in names[:8]:  # 앞에서 8개까지 실제로 짧게 호출해 봅니다
        try:  # 호출을 시도해 보고
            r = client.models.generate_content(model=name, contents="안녕이라고만 답해")  # '안녕'이라고 답하게 하는 테스트 호출입니다
            print(f"  ✅ {name}: {(r.text or '').strip()[:20]}")  # 성공하면 ✅와 답을 출력합니다
        except Exception as e:  # 실패하면
            print(f"  ❌ {name}: {str(e)[:80]}")  # ❌와 에러 앞부분을 출력합니다
