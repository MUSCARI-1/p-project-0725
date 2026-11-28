# 페르소나 테스트에 쓰는 가상 사용자와 정답입니다 (정답은 공고문 원문을 사람이 읽고 정함)

MET = [  # 나이·지역처럼 백엔드가 코드로 판정하는 조건은 '충족'으로 두고, AI가 맡는 글로 적힌 조건만 시험합니다
    {"condition": "나이", "result": "met", "detail": "테스트용: 나이 조건 충족으로 가정"},  # 나이 충족 가정
    {"condition": "지역", "result": "met", "detail": "테스트용: 지역 조건 충족으로 가정"},  # 지역 충족 가정
]


def person(age, region, edu, job, message, income=None, marital="single"):  # 가상 사용자 한 명을 만드는 함수입니다
    return {  # 백엔드가 AI에 넘기는 사용자 정보와 같은 모양입니다
        "age": age, "region_name": region, "marital_status": marital, "job_status": job,  # 나이, 지역, 결혼, 취업 상태
        "education": edu, "annual_income": income, "household_size": 1, "message": message,  # 학력, 연소득(만 원), 가구원 수, 상황 문장
    }


# 자격 판단 시험: (번호, 가상 사용자, 정책 번호, 허용되는 정답들, 왜 그게 정답인지)
JUDGE_CASES = [
    ("J01", person(23, "서울특별시 마포구", "university_enrolled", "etc", "대학 다니면서 그림 그리는 작가로 활동해요"),
     "20261025005400214388", {"ineligible"}, "K-Art 창작자 지원은 대학교 재학생·휴학생 제외"),
    ("J02", person(28, "서울특별시 마포구", "university_graduated", "unemployed", "졸업하고 일러스트 작가로 활동하고 있어요"),
     "20261025005400214388", {"eligible", "check_needed"}, "졸업생 예술가라 제외 대상 아님"),
    ("J03", person(22, "부산광역시 해운대구", "university_enrolled", "unemployed", "대학 3학년이고 요즘 의욕이 없어요"),
     "20261020005400214067", {"ineligible"}, "청년도전 지원사업은 재학생 참여 불가"),
    ("J04", person(27, "부산광역시 해운대구", "university_graduated", "unemployed", "졸업하고 1년 넘게 구직활동 안 하고 쉬고 있어요"),
     "20261020005400214067", {"eligible", "check_needed"}, "졸업생, 6개월 이상 구직활동 없음 → 대상에 가까움"),
    ("J05", person(30, "대구광역시 수성구", "university_graduated", "employed", "제 명의 아파트에 살고 있는데 대출 이자 지원 받을 수 있나요", income=4000),
     "20261103005400214711", {"ineligible"}, "무주택 청년만 대상인데 본인 명의 주택 보유"),
    ("J06", person(26, "대구광역시 수성구", "university_graduated", "employed", "집 없이 혼자 전세로 살고 있어요", income=3000),
     "20261103005400214711", {"eligible", "check_needed"}, "무주택·소득 6천 이하 충족, 보증금 2.5억 이하 여부는 모름"),
    ("J07", person(31, "대구광역시 수성구", "university_graduated", "employed", "집 없이 전세 살고 있어요", income=7000),
     "20261103005400214711", {"ineligible"}, "연소득 7천만 원으로 6천만 원 기준 초과"),
    ("J08", person(36, "인천광역시 서구", "university_graduated", "employed", "아직 부모님 집에서 같이 살고 있어요"),
     "20260724005400213302", {"ineligible"}, "부모와 함께 거주하면 제외"),
    ("J09", person(36, "인천광역시 서구", "university_graduated", "employed", "혼자 원룸 월세로 살고 있어요"),
     "20260724005400213302", {"check_needed"}, "독립 거주는 맞지만 소득·재산 기준은 모름"),
    ("J10", person(29, "서울특별시 송파구", "university_graduated", "employed", "작년에 결혼했어요", marital="married"),
     "20261025005400214394", {"eligible", "check_needed"}, "혼인 1년 차로 혼인신고 3년 이내 충족"),
    ("J11", person(29, "서울특별시 송파구", "university_graduated", "employed", "결혼할 계획은 없어요"),
     "20261025005400214394", {"ineligible"}, "예비부부·신혼부부가 아님"),
    ("J12", person(24, "전라남도 곡성군", "university_enrolled", "etc", "휴학 중이고 알바하면서 월세 살아요"),
     "20250106005400210052", {"ineligible"}, "곡성 월세 지원은 대학생(휴학생 포함) 제외"),
    ("J13", person(33, "전라남도 곡성군", "university_graduated", "employed", "본가에서 나와 혼자 월세 살아요", income=2500),
     "20250106005400210052", {"eligible", "check_needed"}, "제외 대상 아님, 주거급여·주택 소유 여부 등은 모름"),
]

# 정렬(의미 검색) 시험: (번호, 상황 문장, 정답으로 인정할 '정책 이름' 패턴, 설명, 점수에 넣을지)
# 정답 패턴은 사람이 질문 의도를 보고 정한 것입니다. 이름에 이 패턴이 있어야만 맞은 것으로 셉니다 (설명에만 단어가 있는 건 인정 안 함)
RANK_CASES = [
    ("R01", "휴학 중이고 알바하는데 월세가 부담돼요", r"월세|주거비|임차료|임대료", "기본 월세 질문", True),
    ("R02", "집세 도와주는 거 있어요?", r"월세|주거비|임차료|임대료", "'월세'라는 단어 없이 의미로 찾는지", True),
    ("R03", "졸업하고 취업 준비 중인데 학원비가 부담돼요", r"응시료|자격|어학|취업\s*준비|취업준비|학원|교육비|훈련|역량", "취업 준비 비용 (학자금대출은 정답 아님)", True),
    ("R04", "마음이 너무 힘들어서 상담 받아 보고 싶어요", r"심리|상담|마음|정신건강", "심리 상담", True),
    ("R05", "창업 준비 중이라 사무실이 필요해요", r"공유\s*오피스|사무실|창업\s*공간|창업공간|입주|창업.*센터|보육", "창업 공간 (창업 자금만 주는 건 정답 아님)", True),
    ("R06", "곧 결혼하는데 전세 보증금이 걱정이에요", r"신혼|전세|보증금", "신혼 주거", True),
    ("R07", "빚이 많아서 너무 힘들어요", r"채무|신용회복|부채|회생|파산", "채무 지원 (우울증 치료비 등은 정답 아님)", True),
    ("R08", "문화생활 하고 싶은데 돈이 없어요", r"문화|예술|관람|공연", "문화 지원", True),
    ("R09", "알바하는데 생활비 지원 받을 수 있어요?", r"생활|생계|수당|지원금|월세|주거비", "알바 '일자리 모집'이 아니라 생활 지원을 찾는지", True),
    ("R10", "알바 돼요?", r"$^", "조교님 예시: 의도가 애매한 질문 → 점수 없이 결과만 보고 판단", False),
]

# 조건 뽑기(understood) 시험: (번호, 상황 문장, 정답 {칸: 값}, 설명)  — 정답에 적은 칸만 채점합니다
UNDERSTAND_CASES = [
    ("U01", "휴학 중이고 알바하는데 월세가 부담돼요", {"education": "university_enrolled", "job_status": "etc", "categories": "주거"}, "휴학생, 알바, 주거"),
    ("U02", "졸업하고 취업 준비 중인데 학원비가 부담돼요", {"education": None, "job_status": "unemployed", "categories": "교육"}, "구직, 교육비 ('졸업'만으로는 고졸인지 대졸인지 모르므로 학력은 비워야 정답)"),
    ("U03", "회사 다니는데 곧 결혼해서 전세집을 구해야 해요", {"job_status": "employed", "marital_status": "single", "categories": "주거"}, "재직, 예비 신혼(아직 미혼), 주거"),
    ("U04", "작년에 결혼했고 지금은 일을 쉬고 있어요", {"marital_status": "married", "job_status": "unemployed"}, "기혼, 미취업"),
    ("U05", "카페 창업을 준비하고 있어요", {"job_status": "startup", "categories": "일자리"}, "예비 창업"),
    ("U06", "고등학교 졸업하고 바로 공장에서 일하고 있어요", {"education": "high_school", "job_status": "employed"}, "고졸, 재직"),
    ("U07", "빚이 많아서 너무 힘들어요", {"categories": "금융·복지·문화"}, "채무 → 금융 분야"),
    ("U08", "월세 지원 알려줘", {"job_status": None, "education": None}, "문장에 없는 정보를 지어내지 않는지"),
]
