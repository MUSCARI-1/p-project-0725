MARITAL_ANY = "0055003"
MARITAL_LABELS = {"0055001": "기혼", "0055002": "미혼", "0055003": "제한없음"}
MARITAL_MAP = {"single": "0055002", "married": "0055001"}

JOB_ANY = "0013010"
JOB_ETC = "0013009"
JOB_LABELS = {
    "0013001": "재직자",
    "0013002": "자영업자",
    "0013003": "미취업자",
    "0013004": "프리랜서",
    "0013005": "일용근로자",
    "0013006": "(예비)창업자",
    "0013007": "단기근로자",
    "0013008": "영농종사자",
    "0013009": "기타",
    "0013010": "제한없음",
}
JOB_MAP = {
    "employed": {"0013001"},
    "unemployed": {"0013003"},
    "self_employed": {"0013002"},
    "startup": {"0013006"},
    "etc": set(),
}

SCHOOL_ANY = "0049010"
SCHOOL_ETC = "0049009"
SCHOOL_LABELS = {
    "0049001": "고졸 미만",
    "0049002": "고교 재학",
    "0049003": "고졸 예정",
    "0049004": "고교 졸업",
    "0049005": "대학 재학",
    "0049006": "대졸 예정",
    "0049007": "대학 졸업",
    "0049008": "석·박사",
    "0049009": "기타",
    "0049010": "제한없음",
}
# TODO: high_school은 고교 재학과 졸업을 구분하지 못한다
SCHOOL_MAP = {
    "high_school": {"0049002", "0049003", "0049004"},
    "university_enrolled": {"0049005", "0049006"},
    "university_graduated": {"0049007"},
    "etc": set(),
}

INCOME_ANY = "0043001"
INCOME_ANNUAL = "0043002"
INCOME_ETC = "0043003"

APPLY_PERIOD = "0057001"
APPLY_ALWAYS = "0057002"
APPLY_CLOSED = "0057003"

# 온통청년 데이터에 옛 분류명과 새 분류명이 섞여 있고 가운뎃점도 '･'(U+FF65)라서 5개로 통일한다
CATEGORIES = ["일자리", "주거", "교육", "금융·복지·문화", "참여·기반"]
_CATEGORY_ALIASES = {
    "일자리": "일자리",
    "주거": "주거",
    "교육": "교육",
    "교육·직업훈련": "교육",
    "금융·복지·문화": "금융·복지·문화",
    "복지문화": "금융·복지·문화",
    "참여·기반": "참여·기반",
    "참여권리": "참여·기반",
}


def normalize_category(name: str) -> str:
    s = (name or "").strip()
    for dot in ("･", "‧", "ㆍ", "・", "."):
        s = s.replace(dot, "·")
    return _CATEGORY_ALIASES.get(s, s)


REQUEST_ENUMS = {
    "marital_status": ["single", "married"],
    "job_status": ["employed", "unemployed", "self_employed", "startup", "etc"],
    "education": ["high_school", "university_enrolled", "university_graduated", "etc"],
    "categories": CATEGORIES,
}
