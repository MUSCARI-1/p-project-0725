from __future__ import annotations  # 타입 표시를 최신 문법으로 쓰기 위한 코드입니다

MARITAL = {"single": "미혼", "married": "기혼"}  # 결혼 여부 영어 값을 한글로 바꾸는 표입니다
JOB = {"employed": "재직자", "unemployed": "미취업자", "self_employed": "자영업자", "startup": "(예비)창업자", "etc": "기타"}  # 취업 상태 영어 값을 한글로 바꾸는 표입니다
EDU = {  # 학력 영어 값을 한글로 바꾸는 표입니다
    "high_school": "고졸",
    "university_enrolled": "대학 재학",
    "university_graduated": "대학 졸업",
    "etc": "기타",
}


def _labels(value, table: dict) -> str:  # 한 개(문자열)든 여러 개(배열)든 한글 이름으로 바꿔 주는 함수입니다
    items = value if isinstance(value, list) else [value]  # 문자열 하나면 목록으로 감쌉니다
    names = [table.get(x, x) for x in items if x]  # 표에 있으면 한글로, 없으면 그대로 씁니다
    return ", ".join(names) or "모름"  # 쉼표로 이어 붙이고, 하나도 없으면 '모름'


def describe(profile: dict) -> str:  # 사용자 조건을 Gemini가 읽을 문장으로 바꾸는 함수입니다
    def v(x):  # 값이 없으면 '모름'으로 바꿔 주는 작은 함수입니다
        return "모름" if x in (None, "") else x  # 비어 있으면 '모름', 아니면 그대로

    income = profile.get("annual_income")  # 연소득 값을 꺼냅니다 (없으면 None)
    lines = [  # 사용자 정보를 한 줄씩 만듭니다
        f"- 나이: 만 {v(profile.get('age'))}세 (생년월일 {v(profile.get('birth_date'))})",  # 나이와 생년월일
        f"- 거주지: {v(profile.get('region_name'))}",  # 사는 지역
        f"- 결혼: {_labels(profile.get('marital_status'), MARITAL)}",  # 결혼 여부 (한글로)
        f"- 취업 상태: {_labels(profile.get('job_status'), JOB)}",  # 취업 상태 (한글로, 여러 개 가능)
        f"- 학력: {_labels(profile.get('education'), EDU)}",  # 학력 (한글로, 여러 개 가능)
        f"- 본인 연소득: {f'{income}만 원' if income is not None else '모름'}",  # 연소득 (없으면 '모름')
        f"- 가구원 수: {v(profile.get('household_size'))}",  # 가구원 수
    ]
    if (profile.get("message") or "").strip():  # 사용자가 상황 설명을 썼으면
        lines.append(f"- 사용자가 직접 쓴 상황: {profile['message'].strip()}")  # 그 문장도 추가합니다
    return "\n".join(lines)  # 줄들을 하나의 글로 합쳐서 돌려줍니다
