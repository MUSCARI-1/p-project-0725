import ai


def ids(resp):
    return {r["policy_id"] for r in resp.get_json()["results"]}


def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok", "db": True}


def test_meta(client):
    body = client.get("/api/meta").get_json()
    assert body["policy_count"] == 8
    assert "금융·복지·문화" in body["enums"]["categories"]


def test_recommend_filters(client, user):
    resp = client.post("/api/recommend", json=user)
    assert resp.status_code == 200
    body = resp.get_json()
    # P2 지역, P3/P6 마감, P4 재직자만, P5 나이, P7 기혼만 → 제외
    assert ids(resp) == {"P1", "P8"}
    assert body["total"] == 2

    p1 = next(r for r in body["results"] if r["policy_id"] == "P1")
    assert p1["eligibility"] == "eligible"
    assert p1["apply_status"] == "always"
    assert p1["documents"] == ["신청서", "주민등록등본(최근 1개월, 원본)"]
    assert [r["condition"] for r in p1["reasons"]] == ["나이", "지역", "소득"]
    assert list(p1) == [
        "policy_id", "name", "category", "sub_category", "summary", "support", "eligibility", "reasons",
        "documents", "apply_method", "apply_status", "apply_period", "apply_url", "ref_url", "source_text",
    ]

    p8 = next(r for r in body["results"] if r["policy_id"] == "P8")
    assert p8["eligibility"] == "check_needed"  # 추가 자격 원문 있음
    assert p8["documents"] == []  # '공고문 참조'
    assert p8["apply_period"] == "2026-01-01 ~ 2099-12-31"


def test_recommend_categories(client, user):
    user["categories"] = ["교육"]
    assert ids(client.post("/api/recommend", json=user)) == {"P8"}


def test_recommend_without_region(client, user):
    user["region_code"] = None
    resp = client.post("/api/recommend", json=user)
    assert ids(resp) == {"P1", "P2", "P8"}
    p2 = next(r for r in resp.get_json()["results"] if r["policy_id"] == "P2")
    assert p2["eligibility"] == "check_needed"
    assert p2["source_text"] == "청년 5천만원 이하"


def test_recommend_parent_region(client, user):
    # 화성시 동탄구 사용자에게 화성시 전체(41590)로 등록된 P5가 나와야 한다
    user.update(birth_date="1980-01-01", region_code="41597")
    assert ids(client.post("/api/recommend", json=user)) == {"P5"}

    user["region_code"] = "99999"
    assert client.post("/api/recommend", json=user).status_code == 400


def test_regions(client):
    regions = client.get("/api/regions").get_json()["regions"]
    seoul = next(r for r in regions if r["name"] == "서울특별시")
    assert {"code": "11380", "name": "은평구"} in seoul["sigungu"]
    gyeonggi = next(r for r in regions if r["code"] == "41")
    assert {"code": "41597", "name": "화성시 동탄구", "parent": "41590"} in gyeonggi["sigungu"]
    assert "41590" not in [s["code"] for s in gyeonggi["sigungu"]]


def test_recommend_paging(client, user):
    user["size"] = 1
    first = client.post("/api/recommend", json=user).get_json()
    user["page"] = 2
    second = client.post("/api/recommend", json=user).get_json()
    assert first["total"] == second["total"] == 2
    assert first["results"][0]["policy_id"] != second["results"][0]["policy_id"]


def test_recommend_invalid(client, user):
    user["birth_date"] = "1999/05/12"
    resp = client.post("/api/recommend", json=user)
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "INVALID_REQUEST", "message": "birth_date 형식이 올바르지 않습니다."}

    user["birth_date"] = "1999-05-12"
    user["job_status"] = "student"
    assert client.post("/api/recommend", json=user).status_code == 400

    assert client.post("/api/recommend", data="not json").status_code == 400


def test_recommend_survives_ai_error(client, user, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("Gemini 장애")

    monkeypatch.setattr(ai, "judge_policies", boom)
    resp = client.post("/api/recommend", json=user)
    assert resp.status_code == 200
    assert {r["eligibility"] for r in resp.get_json()["results"]} == {"check_needed"}


def test_policy_list(client):
    body = client.get("/api/policies").get_json()
    assert body["total"] == 6  # P3, P6 마감 제외
    assert client.get("/api/policies?include_closed=true").get_json()["total"] == 8
    assert client.get("/api/policies?category=교육").get_json()["total"] == 2  # P5, P8
    assert client.get("/api/policies?region_code=41591&include_closed=true").get_json()["total"] == 1
    assert client.get("/api/policies?region_code=99999").status_code == 400
    assert client.get("/api/policies?size=0").status_code == 400


def test_policy_detail(client):
    body = client.get("/api/policies/P5").get_json()
    assert body["categories"] == ["교육"]
    assert body["conditions"]["region_codes"] == ["11380", "41590"]
    assert body["conditions"]["min_age"] == 40

    resp = client.get("/api/policies/NOPE")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "NOT_FOUND"


def test_chat(client):
    resp = client.post("/api/chat", json={"question": "소득 기준이 어떻게 돼요?", "policy_id": "P2", "history": []})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["sources"] == [{"policy_id": "P2", "text": "청년 5천만원 이하"}]

    assert client.post("/api/chat", json={"question": "질문", "policy_id": "NOPE"}).status_code == 404
    assert client.post("/api/chat", json={"question": ""}).status_code == 400
