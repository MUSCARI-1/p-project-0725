import json  # 결과를 보기 좋게 출력하기 위한 모듈입니다
import time  # 단계별로 걸린 시간을 재기 위한 모듈입니다

from . import settings  # 설정값(모델 이름)을 가져옵니다
from .service import answer_question, judge_policies, rank_policies  # 테스트할 AI 함수 3개를 가져옵니다
from .vector_store import load_by_ids, load_policies  # DB에서 정책을 읽는 함수를 가져옵니다

profile = {  # 테스트용 가짜 사용자 조건입니다
    "birth_date": "1999-05-12", "age": 27, "region_code": "11380", "region_name": "서울특별시 은평구",
    "marital_status": "single", "job_status": "unemployed", "education": "university_enrolled",
    "annual_income": None, "household_size": 1, "categories": [], "message": "휴학 중이고 알바하는데 월세가 부담돼요",
}

if __name__ == "__main__":  # 'python -m ai.try_it'로 직접 실행했을 때만 아래가 돌아갑니다
    print("모델:", settings.GEMINI_MODEL, "/", settings.EMBED_MODEL)  # 어떤 모델을 쓰는지 출력합니다
    ids = [p["policy_id"] for p in load_policies()]  # DB의 전체 정책 번호를 가져옵니다 (실제로는 백엔드가 조건으로 거른 후보가 들어옴)

    t = time.time()  # 1번 시작 시각을 기록합니다
    print("\n[1] rank_policies (전체 정책 중 상위 5개)")  # 1번 테스트 제목
    top = rank_policies(profile, ids)[:5]  # 상황 문장과 비슷한 순서로 정렬해서 상위 5개를 고릅니다
    for p in load_by_ids(top):  # 그 5개 정책을 읽어서
        print(" -", p["name"])  # 이름을 출력합니다
    print(f"  ⏱ {time.time() - t:.1f}초")  # 1번에 걸린 시간을 출력합니다

    t = time.time()  # 2번 시작 시각을 기록합니다

    print("\n[2] judge_policies (상위 3개)")  # 2번 테스트 제목
    policies = [{**p, "rule_checks": [], "documents": []} for p in load_by_ids(top[:3])]  # 상위 3개를 판단용 모양으로 만듭니다 (백엔드 판단은 비워 둠)
    print(json.dumps(judge_policies(profile, policies), ensure_ascii=False, indent=2))  # 자격 판단 결과를 출력합니다
    print(f"  ⏱ {time.time() - t:.1f}초")  # 2번에 걸린 시간을 출력합니다

    t = time.time()  # 3번 시작 시각을 기록합니다

    print("\n[3] answer_question")  # 3번 테스트 제목
    print(json.dumps(answer_question("월세 지원 받으려면 뭐가 필요해요?", None, []), ensure_ascii=False, indent=2))  # 챗봇 답변을 출력합니다
    print(f"  ⏱ {time.time() - t:.1f}초")  # 3번에 걸린 시간을 출력합니다

    t = time.time()  # 4번 시작 시각을 기록합니다
    print("\n[4] answer_question (애매한 질문 → 되묻기)")  # 4번 테스트 제목
    print(json.dumps(answer_question("알바 돼요?", None, []), ensure_ascii=False, indent=2))  # 뜻이 애매한 질문에 되묻는지 확인합니다
    print(f"  ⏱ {time.time() - t:.1f}초")  # 4번에 걸린 시간을 출력합니다
