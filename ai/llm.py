from __future__ import annotations  # 타입 표시를 최신 문법으로 쓰기 위한 코드입니다

from functools import lru_cache  # 같은 객체를 한 번만 만들고 재사용하게 해 주는 도구입니다

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings  # Gemini 대화 모델과 임베딩 모델입니다

from . import settings  # 위에서 만든 설정값(키, 모델 이름)을 가져옵니다


def _chat_model(name: str) -> ChatGoogleGenerativeAI:  # 모델 이름으로 Gemini 대화 모델 하나를 만드는 함수입니다
    return ChatGoogleGenerativeAI(  # Gemini 대화 모델을 만드는 코드입니다
        model=name,  # 사용할 모델 이름입니다
        google_api_key=settings.GEMINI_API_KEY,  # Gemini 키입니다
        temperature=0,  # 매번 같은 질문에 최대한 같은 답을 하도록(무작위성 0) 하는 설정입니다
        max_retries=0,  # 실패하면 같은 모델로 다시 기다리지 않고 바로 대체 모델로 넘어가게 하는 설정입니다
        thinking_level=settings.GEMINI_THINKING_LEVEL,  # 생각 단계를 짧게(low) 해서 답을 빨리 받는 설정입니다
        timeout=settings.GEMINI_TIMEOUT,  # 응답이 이 시간(초)을 넘으면 기다리지 않고 실패 처리하는 설정입니다
    )


@lru_cache(maxsize=1)  # 이 함수 결과를 한 번만 만들고 계속 재사용하게 하는 코드입니다
def get_llm():  # 기본 Gemini 대화 모델을 돌려주는 함수입니다
    return _chat_model(settings.GEMINI_MODEL)  # .env의 GEMINI_MODEL(기본 gemini-3.5-flash)로 만듭니다


def structured(schema):  # Gemini 답을 정해진 모양(schema)으로 받고, 바쁘면 대체 모델로 다시 시도하는 실행기를 만드는 함수입니다
    primary = _chat_model(settings.GEMINI_MODEL).with_structured_output(schema)  # 기본 모델로 정해진 모양의 답을 받는 실행기입니다
    backups = [_chat_model(m).with_structured_output(schema) for m in settings.GEMINI_FALLBACK_MODELS]  # 대체 모델들로 만든 실행기 목록입니다
    return primary.with_fallbacks(backups) if backups else primary  # 기본 모델이 실패하면 대체 모델을 순서대로 시도하게 묶어서 돌려줍니다


@lru_cache(maxsize=1)  # 임베딩 모델도 한 번만 만들고 재사용합니다
def get_embeddings():  # 문장을 숫자(벡터)로 바꾸는 임베딩 모델을 돌려주는 함수입니다
    return GoogleGenerativeAIEmbeddings(model=settings.EMBED_MODEL, google_api_key=settings.GEMINI_API_KEY)  # 임베딩 모델을 만드는 코드입니다
