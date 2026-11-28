from __future__ import annotations  # 타입 표시를 최신 문법으로 쓰기 위한 코드입니다

import hashlib  # 정책 내용으로 지문(해시)을 만들기 위한 모듈입니다
import time  # 잠깐 기다리기(sleep)를 위한 모듈입니다
from functools import lru_cache  # 벡터 DB 연결을 한 번만 만들고 재사용하게 해 주는 도구입니다

from langchain_chroma import Chroma  # Chroma 벡터 DB를 LangChain에서 쓰게 해 주는 클래스입니다
from langchain_core.documents import Document  # 벡터 DB에 넣을 '문서' 한 개를 표현하는 클래스입니다
from sqlalchemy import create_engine, text  # 백엔드 DB에 SQL로 접속하기 위한 도구입니다

from . import settings  # 설정값(DB 주소, 벡터 DB 폴더 등)을 가져옵니다
from .llm import get_embeddings  # 문장을 벡터로 바꾸는 임베딩 모델을 가져옵니다
from .texts import search_text  # 정책을 검색용 본문으로 만드는 함수를 가져옵니다

POLICY_COLUMNS = [  # 백엔드 DB의 policies 테이블에서 읽어 올 칸(컬럼) 목록입니다
    "policy_id", "name", "keywords", "category", "sub_category", "summary", "support",
    "min_age", "max_age", "income_text", "extra_qualification", "excluded_targets",
]


@lru_cache(maxsize=1)  # 벡터 DB 연결을 한 번만 만들고 재사용합니다
def get_store() -> Chroma:  # Chroma 벡터 DB를 돌려주는 함수입니다
    return Chroma(  # 벡터 DB를 열거나(이미 있으면) 새로 만드는 코드입니다
        collection_name=settings.COLLECTION,  # 정책을 모아 둘 이름
        embedding_function=get_embeddings(),  # 글을 벡터로 바꿀 때 쓸 임베딩 모델
        persist_directory=settings.CHROMA_DIR,  # 파일로 저장할 폴더 (껐다 켜도 남아 있음)
    )


def load_policies(limit: int | None = None) -> list[dict]:  # 백엔드 DB에서 정책 목록을 읽어 오는 함수입니다
    engine = create_engine(settings.DATABASE_URL)  # 백엔드 DB에 접속할 준비를 하는 코드입니다
    sql = f"SELECT {', '.join(POLICY_COLUMNS)} FROM policies ORDER BY policy_id"  # 필요한 칸만 읽는 SQL 문입니다
    if limit:  # 개수 제한이 있으면 (테스트용)
        sql += f" LIMIT {int(limit)}"  # 그 개수만큼만 읽도록 SQL에 붙입니다
    with engine.connect() as conn:  # DB에 접속해서
        return [dict(r._mapping) for r in conn.execute(text(sql))]  # 한 줄씩 dict로 바꿔 목록으로 돌려줍니다


def fingerprint(p: dict) -> str:  # 정책 내용으로 짧은 지문(해시)을 만드는 함수입니다
    return hashlib.sha1(search_text(p).encode("utf-8")).hexdigest()  # 검색용 본문이 한 글자라도 바뀌면 지문도 바뀝니다


def build_index(limit: int | None = None, batch_size: int = 50, pause: float = 1.0, echo=print) -> int:  # 정책을 벡터 DB에 저장하는 함수입니다
    store = get_store()  # 벡터 DB를 엽니다
    policies = load_policies(limit)  # 백엔드 DB에서 정책을 읽어 옵니다
    saved = store.get(include=["metadatas"])  # 벡터 DB에 이미 들어 있는 정책 번호와 정보(지문 포함)를 가져옵니다
    old = {pid: (m or {}).get("hash") for pid, m in zip(saved["ids"], saved["metadatas"])}  # {정책 번호: 저장할 때의 지문} 형태로 정리합니다
    for p in policies:  # 정책마다
        p["_hash"] = fingerprint(p)  # 지금 내용의 지문을 만들어 둡니다
    new = [p for p in policies if p["policy_id"] not in old]  # 벡터 DB에 아직 없는 새 정책입니다
    changed = [p for p in policies if p["policy_id"] in old and old[p["policy_id"]] != p["_hash"]]  # 있긴 한데 내용이 바뀐 정책입니다
    current = {p["policy_id"] for p in policies}  # 지금 DB에 있는 정책 번호들입니다
    gone = [] if limit else [pid for pid in old if pid not in current]  # DB에서 사라진 정책입니다 (일부만 넣는 테스트 때는 건드리지 않음)
    echo(f"전체 {len(policies)}개 → 새 정책 {len(new)}개, 바뀐 정책 {len(changed)}개, 사라진 정책 {len(gone)}개")  # 진행 상황을 출력합니다

    if changed or gone:  # 바뀌었거나 사라진 정책이 있으면
        store.delete(ids=[p["policy_id"] for p in changed] + gone)  # 예전 내용을 벡터 DB에서 지웁니다 (바뀐 건 아래에서 새로 넣음)
    todo = new + changed  # 이번에 임베딩해서 넣을 정책입니다 (안 바뀐 정책은 건너뛰어서 비용이 안 듦)

    for i in range(0, len(todo), batch_size):  # 정책을 50개씩 묶어서 처리합니다
        chunk = todo[i : i + batch_size]  # 이번에 넣을 50개입니다
        docs = [  # 50개를 벡터 DB용 문서로 바꿉니다
            Document(page_content=search_text(p), metadata={"policy_id": p["policy_id"], "name": p["name"] or "", "hash": p["_hash"]})  # 본문 + 정책 번호·이름·지문 정보
            for p in chunk
        ]
        for attempt in range(3):  # 실패하면 최대 3번까지 시도합니다
            try:  # 저장을 시도해 보고
                store.add_documents(docs, ids=[p["policy_id"] for p in chunk])  # 임베딩해서 벡터 DB에 저장하는 코드입니다
                break  # 성공하면 재시도 반복을 빠져나옵니다
            except Exception as e:  # 무료 한도 초과 같은 오류가 나면
                wait = 20 * (attempt + 1)  # 20초, 40초, 60초로 점점 길게 기다립니다
                echo(f"  오류: {e} → {wait}초 뒤 다시 시도")  # 오류 내용을 출력합니다
                time.sleep(wait)  # 기다립니다
        else:  # 3번 다 실패했으면
            raise RuntimeError("임베딩 저장에 계속 실패했습니다. 잠시 뒤 다시 실행하면 이어서 합니다.")  # 멈추고 안내합니다
        echo(f"  저장 {min(i + batch_size, len(todo))} / {len(todo)}")  # 몇 개까지 저장했는지 출력합니다
        time.sleep(pause)  # 무료 한도를 지키려고 1초 쉽니다
    return len(todo)  # 이번에 새로 넣은 개수를 돌려줍니다


def rank_ids(query: str, candidate_ids: list[str]) -> list[str]:  # 후보 정책을 사용자 문장과 비슷한 순서로 정렬하는 함수입니다
    if not query.strip() or not candidate_ids:  # 상황 문장이 없거나 후보가 없으면
        return list(candidate_ids)  # 정렬하지 않고 그대로 돌려줍니다
    store = get_store()  # 벡터 DB를 엽니다
    vector = get_embeddings().embed_query(query)  # 문장을 숫자(벡터)로 딱 한 번만 바꿉니다 (예전엔 500개 묶음마다 다시 바꿔서 느렸음)
    scored: list[tuple[float, str]] = []  # (거리 점수, 정책 번호)를 모아 둘 목록입니다
    for i in range(0, len(candidate_ids), 500):  # 후보가 많을 수 있어서 500개씩 나눠 검색합니다
        chunk = candidate_ids[i : i + 500]  # 이번에 검색할 후보 500개입니다
        res = store._collection.query(  # 정책 본문은 빼고 '번호와 거리'만 받아 오는 빠른 검색입니다 (순서만 필요해서)
            query_embeddings=[vector], n_results=len(chunk), where={"policy_id": {"$in": chunk}}, include=["distances"]  # 미리 바꿔 둔 벡터로 후보 안에서만 찾고, 거리만 받습니다
        )
        scored += list(zip(res["distances"][0], res["ids"][0]))  # (거리, 정책 번호)를 모읍니다 (벡터 DB의 id가 정책 번호와 같음)
    scored.sort(key=lambda x: x[0])  # 거리가 가까운(점수가 작은) 순서로 정렬합니다
    ranked = [pid for _, pid in scored]  # 정렬된 정책 번호만 뽑습니다
    seen = set(ranked)  # 이미 정렬된 번호를 기록합니다
    return ranked + [pid for pid in candidate_ids if pid not in seen]  # 벡터 DB에 없던 후보는 맨 뒤에 붙여서 돌려줍니다


def names_by_ids(ids: list[str]) -> dict[str, str]:  # 정책 번호 목록으로 {번호: 이름}을 돌려주는 함수입니다 (정렬 보정용)
    if not ids:  # 번호가 없으면
        return {}  # 빈 결과
    got = get_store().get(ids=list(ids), include=["metadatas"])  # 벡터 DB에 저장해 둔 이름을 바로 꺼냅니다 (DB 조회보다 빠름)
    return {pid: (m or {}).get("name", "") for pid, m in zip(got["ids"], got["metadatas"])}  # {번호: 이름}으로 정리합니다


def search(query: str, k: int = 3) -> list[str]:  # 챗봇용: 질문과 비슷한 정책 번호를 k개 찾는 함수입니다
    return [d.metadata["policy_id"] for d in get_store().similarity_search(query, k=k)]  # 비슷한 문서를 찾아서 정책 번호만 돌려줍니다


def load_by_ids(ids: list[str]) -> list[dict]:  # 정책 번호 목록으로 DB에서 정책 내용을 읽는 함수입니다 (챗봇용)
    if not ids:  # 번호가 하나도 없으면
        return []  # 빈 목록을 돌려줍니다
    cols = POLICY_COLUMNS + ["documents_text", "apply_method", "screening_method", "etc", "ref_url"]  # 챗봇 답변에 필요한 칸까지 읽습니다
    engine = create_engine(settings.DATABASE_URL)  # 백엔드 DB에 접속할 준비를 합니다
    marks = ", ".join(f":id{i}" for i in range(len(ids)))  # SQL에 번호를 안전하게 넣기 위한 자리표시(:id0, :id1 …)를 만듭니다
    sql = text(f"SELECT {', '.join(cols)} FROM policies WHERE policy_id IN ({marks})")  # 해당 번호의 정책만 읽는 SQL 문입니다
    with engine.connect() as conn:  # DB에 접속해서
        rows = {r.policy_id: dict(r._mapping) for r in conn.execute(sql, {f"id{i}": v for i, v in enumerate(ids)})}  # 결과를 {번호: 정책} 형태로 만듭니다
    return [rows[i] for i in ids if i in rows]  # 처음 받은 번호 순서대로 정책을 돌려줍니다
