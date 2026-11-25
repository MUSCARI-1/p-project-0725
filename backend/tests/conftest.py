import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.services.sync import upsert_policies


def make_item(no, **kw):
    base = {
        "plcyNo": no,
        "plcyNm": f"테스트 정책 {no}",
        "plcyKywdNm": "보조금",
        "plcyExplnCn": "설명",
        "lclsfNm": "주거",
        "mclsfNm": "전월세 및 주거급여 지원",
        "plcySprtCn": "월 20만원 지원",
        "aplyPrdSeCd": "0057002",
        "aplyYmd": "",
        "plcyAplyMthdCn": "온라인 신청",
        "srngMthdCn": "",
        "aplyUrlAddr": "https://example.com/apply",
        "sbmsnDcmntCn": "신청서, 주민등록등본(최근 1개월, 원본)",
        "refUrlAddr1": "https://example.com/ref",
        "refUrlAddr2": "",
        "sprtTrgtMinAge": "19",
        "sprtTrgtMaxAge": "39",
        "sprtTrgtAgeLmtYn": "N",
        "mrgSttsCd": "0055003",
        "earnCndSeCd": "0043001",
        "earnMinAmt": "0",
        "earnMaxAmt": "0",
        "earnEtcCn": "",
        "addAplyQlfcCndCn": "해당 없음",
        "ptcpPrpTrgtCn": "",
        "etcMttrCn": "",
        "zipCd": "11380",
        "jobCd": "0013010",
        "schoolCd": "0049010",
        "plcyMajorCd": "0011009",
        "sbizCd": "0014010",
        "sprvsnInstCdNm": "은평구청",
        "operInstCdNm": "은평구청",
        "lastMdfcnDt": "2026-11-23 18:01:02",
    }
    base.update(kw)
    return base


ITEMS = [
    make_item("P1"),  # 은평, 주거, 상시
    make_item("P2", zipCd="44790", aplyPrdSeCd="0057001", aplyYmd="20260101 ~ 20991231",
              earnCndSeCd="0043003", earnEtcCn="청년 5천만원 이하"),  # 청양군
    make_item("P3", aplyPrdSeCd="0057003"),  # 마감
    make_item("P4", lclsfNm="일자리", mclsfNm="취업", jobCd="0013001"),  # 재직자만
    make_item("P5", lclsfNm="교육･직업훈련", sprtTrgtMinAge="40", sprtTrgtMaxAge="49", zipCd="11380,41590"),  # 나이 초과, 화성시 전체
    make_item("P6", aplyPrdSeCd="0057001", aplyYmd="20200101 ~ 20200201"),  # 기간 지남
    make_item("P7", mrgSttsCd="0055001"),  # 기혼만
    make_item("P8", lclsfNm="일자리,교육", aplyPrdSeCd="0057001", aplyYmd="20260101 ~ 20991231",
              addAplyQlfcCndCn="은평구 6개월 이상 거주자", sbmsnDcmntCn="공고문 참조"),
]


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        upsert_policies(ITEMS)
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user():
    return {
        "birth_date": "1999-05-12",
        "region_code": "11380",
        "region_name": "서울특별시 은평구",
        "marital_status": "single",
        "job_status": "unemployed",
        "education": "university_enrolled",
        "annual_income": None,
        "household_size": None,
        "categories": [],
        "message": "휴학 중이고 알바하는데 월세가 부담돼요",
        "page": 1,
        "size": 10,
    }
