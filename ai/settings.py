from __future__ import annotations  # 타입 표시를 최신 문법으로 쓰기 위한 코드입니다

import os  # 환경변수(.env 값)를 읽기 위한 모듈입니다
from pathlib import Path  # 폴더·파일 경로를 다루기 위한 모듈입니다

from dotenv import load_dotenv  # .env 파일을 읽어 주는 함수입니다

ROOT_DIR = Path(__file__).resolve().parent.parent  # 레포 맨 위 폴더(p-project-0725) 경로입니다
load_dotenv(ROOT_DIR / ".env")  # 맨 위 폴더의 .env 파일을 읽어 오는 코드입니다

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()  # Gemini 키를 가져오는 코드입니다 (없으면 빈 문자열)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")  # 답변·판단에 쓸 Gemini 모델 이름입니다 (테스트해 보니 lite가 빠르고 품질도 비슷함, .env에서 바꿀 수 있음)
GEMINI_FALLBACK_MODELS = [m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.5-flash").split(",") if m.strip()]  # 기본 모델이 바쁠 때(503) 대신 쓸 모델들입니다 (쉼표로 여러 개)
GEMINI_THINKING_LEVEL = os.getenv("GEMINI_THINKING_LEVEL", "low")  # 답하기 전에 얼마나 오래 생각할지입니다 (low=빠름, high=느리지만 신중)
GEMINI_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT", "20"))  # Gemini 응답을 최대 몇 초까지 기다릴지입니다 (넘으면 대체 모델로 넘어감)
JUDGE_BATCH_SIZE = int(os.getenv("JUDGE_BATCH_SIZE", "5"))  # 자격 판단 때 정책 몇 개를 한 번에 묶어 물어볼지입니다 (작을수록 빠르지만 요청 수가 늘어 무료 한도를 빨리 씀)
EMBED_MODEL = os.getenv("EMBED_MODEL", "models/gemini-embedding-001")  # 문장을 숫자(벡터)로 바꿀 임베딩 모델 이름입니다

CHROMA_DIR = str(ROOT_DIR / "chroma_db")  # 벡터 DB 파일을 저장할 폴더입니다 (깃허브에는 안 올라감)
COLLECTION = "policies"  # 벡터 DB 안에서 정책을 모아 둘 이름(테이블 같은 것)입니다

DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{(ROOT_DIR / 'backend' / 'local.db').as_posix()}"  # 백엔드 DB 주소입니다 (없으면 backend/local.db)
