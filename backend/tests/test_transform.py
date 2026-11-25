from datetime import date

from app.services import codes, transform
from app.services.validators import calc_age


def test_split_documents():
    assert transform.split_documents("공고문 참조") == []
    assert transform.split_documents("") == []
    assert transform.split_documents("-") == []
    assert transform.split_documents("신청서, 주민등록등본(최근 1개월, 원본)\n- 통장사본") == [
        "신청서",
        "주민등록등본(최근 1개월, 원본)",
        "통장사본",
    ]
    assert transform.split_documents("ㅇ 제출서류: 지원서 1부, 자기소개서 1부") == ["지원서 1부", "자기소개서 1부"]


def test_normalize_category():
    assert codes.normalize_category("금융･복지･문화") == "금융·복지·문화"
    assert codes.normalize_category("복지문화") == "금융·복지·문화"
    assert codes.normalize_category("교육･직업훈련") == "교육"
    assert codes.normalize_category("참여권리") == "참여·기반"


def test_parse_fields():
    assert transform.parse_age({"sprtTrgtMinAge": "0", "sprtTrgtMaxAge": "0"}) == (None, None)
    assert transform.parse_age({"sprtTrgtMinAge": "19", "sprtTrgtMaxAge": "39"}) == (19, 39)
    assert transform.parse_apply_period("20260201 ~ 20261231") == (date(2026, 2, 1), date(2026, 12, 31))
    assert transform.parse_apply_period("") == (None, None)
    assert transform.parse_categories({"lclsfNm": "일자리,일자리,교육･직업훈련"}) == ["일자리", "교육"]
    assert transform.parse_income({"earnCndSeCd": "0043002", "earnMinAmt": "0", "earnMaxAmt": "5000"}) == (None, 5000)


def test_calc_age():
    assert calc_age(date(1999, 5, 12), date(2026, 5, 11)) == 26
    assert calc_age(date(1999, 5, 12), date(2026, 5, 12)) == 27
