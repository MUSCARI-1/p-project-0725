import argparse  # 터미널에서 --limit 같은 옵션을 받기 위한 모듈입니다

from . import settings  # 설정값(Gemini 키 등)을 가져옵니다
from .vector_store import build_index  # 벡터 DB를 만드는 함수를 가져옵니다

if __name__ == "__main__":  # 'python -m ai.build_index'로 직접 실행했을 때만 아래가 돌아갑니다
    parser = argparse.ArgumentParser()  # 옵션을 읽을 준비를 합니다
    parser.add_argument("--limit", type=int, default=None, help="테스트용: 앞에서부터 이만큼만")  # --limit 50 처럼 개수를 정하는 옵션입니다
    args = parser.parse_args()  # 터미널에 입력한 옵션을 읽습니다
    if not settings.GEMINI_API_KEY:  # Gemini 키가 없으면
        raise SystemExit(".env 에 GEMINI_API_KEY 가 없습니다.")  # 안내하고 멈춥니다
    n = build_index(args.limit)  # 벡터 DB에 정책을 저장합니다
    print(f"완료: {n}개 새로 넣거나 갱신 → {settings.CHROMA_DIR}")  # 몇 개 넣었는지 출력합니다
