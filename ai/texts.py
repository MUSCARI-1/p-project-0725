from __future__ import annotations  # 타입 표시를 최신 문법으로 쓰기 위한 코드입니다

import re  # 정규식(글자 패턴 찾기)을 쓰기 위한 모듈입니다

TRIVIAL = re.compile(r"^\s*(-|없음|해당\s*없음|해당사항\s*없음|제한\s*없음|공고문\s*(참조|참고|확인))?\s*$")  # '없음', '공고문 참조'처럼 내용이 없는 글을 찾는 패턴입니다


def clean(text) -> str:  # 의미 없는 글이면 빈 문자열로 바꿔 주는 함수입니다
    text = (text or "").strip()  # None이면 빈 문자열로 바꾸고 앞뒤 공백을 지웁니다
    return "" if TRIVIAL.match(text) else text  # '없음' 같은 글이면 빈 문자열, 아니면 그대로 돌려줍니다


def search_text(p: dict) -> str:  # 정책 하나를 '검색용 본문'으로 만드는 함수입니다 (벡터 DB에 저장할 글)
    parts = [  # 검색에 쓸 항목들을 (이름, 값) 쌍으로 모읍니다
        ("정책명", p.get("name")),  # 정책 이름
        ("분야", " / ".join(x for x in [p.get("category"), p.get("sub_category")] if x)),  # 대분류 / 중분류
        ("키워드", p.get("keywords")),  # 정책 키워드
        ("설명", p.get("summary")),  # 정책 설명
        ("지원 내용", p.get("support")),  # 지원 내용
        ("추가 자격", p.get("extra_qualification")),  # 추가 신청 자격
        ("소득 조건", p.get("income_text")),  # 소득 조건 설명
    ]
    return "\n".join(f"{k}: {clean(v)}" for k, v in parts if clean(v))[:3000]  # 내용 있는 항목만 '이름: 값' 줄로 합치고 3000자까지만 씁니다


def prompt_text(p: dict) -> str:  # 정책 하나를 'Gemini에게 보여 줄 본문'으로 만드는 함수입니다
    age = "제한 없음"  # 나이 조건 기본값입니다
    if p.get("min_age") or p.get("max_age"):  # 최소·최대 나이 중 하나라도 있으면
        age = f"{p.get('min_age') or '?'}세 ~ {p.get('max_age') or '?'}세"  # '19세 ~ 39세' 형태로 만듭니다
    parts = [  # Gemini가 판단할 때 볼 항목들을 모읍니다
        ("정책 번호", p.get("policy_id")),  # 정책 번호 (결과를 돌려줄 때 그대로 쓰게 함)
        ("정책명", p.get("name")),  # 정책 이름
        ("분야", " / ".join(x for x in [p.get("category"), p.get("sub_category")] if x)),  # 대분류 / 중분류
        ("설명", p.get("summary")),  # 정책 설명
        ("지원 내용", p.get("support")),  # 지원 내용
        ("나이", age),  # 나이 조건
        ("소득 조건", p.get("income_text")),  # 소득 조건 설명
        ("추가 신청 자격", p.get("extra_qualification")),  # 추가 신청 자격
        ("참여 제한 대상", p.get("excluded_targets")),  # 신청할 수 없는 대상
        ("제출 서류", p.get("documents_text")),  # 제출 서류 원문
        ("신청 방법", p.get("apply_method")),  # 신청 방법
        ("심사 방법", p.get("screening_method")),  # 심사 방법
        ("기타", p.get("etc")),  # 기타 안내
    ]
    return "\n".join(f"- {k}: {clean(v)[:800]}" for k, v in parts if clean(v))  # 내용 있는 항목만 '- 이름: 값' 줄로 합칩니다 (항목당 800자까지)
