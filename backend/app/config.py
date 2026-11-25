import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def _database_url() -> str:
    # DATABASE_URL이 없으면 SQLite를 쓴다. 배포 때만 MySQL 주소를 넣는다.
    return os.getenv("DATABASE_URL") or f"sqlite:///{(BACKEND_DIR / 'local.db').as_posix()}"


class Config:
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 3600}

    YOUTHCENTER_API_URL = "https://www.youthcenter.go.kr/go/ythip/getPlcy"
    YOUTHCENTER_API_KEY = os.getenv("YOUTHCENTER_API_KEY", "")

    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

    AI_BATCH_SIZE = 10
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 30


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    YOUTHCENTER_API_KEY = "test-key"
