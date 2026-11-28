# 페르소나 테스트를 실행하고 정확도를 출력·저장하는 스크립트입니다 (실행: python -m ai.eval.run)
import json  # 결과를 파일로 저장하기 위한 모듈입니다
import re  # 정답 패턴을 확인하기 위한 정규식 모듈입니다
import time  # 걸린 시간을 재기 위한 모듈입니다
from datetime import datetime  # 결과 파일에 실행 시각을 적기 위한 모듈입니다
from pathlib import Path  # 결과 파일 경로를 다루기 위한 모듈입니다

from .. import settings  # 지금 쓰는 모델 이름을 결과에 적기 위해 설정을 가져옵니다
from ..judge import judge_policies  # 시험할 자격 판단 함수입니다
from ..service import rank_policies, understand_message  # 실제 서비스와 똑같이 정렬·조건 뽑기를 하는 함수입니다
from ..vector_store import load_by_ids, load_policies  # 정책 읽기 함수입니다
from .cases import JUDGE_CASES, MET, RANK_CASES, UNDERSTAND_CASES  # 가상 사용자와 정답입니다

OUT = Path(__file__).with_name("results")  # 결과를 저장할 폴더입니다 (ai/eval/results)


def run_judge() -> list[dict]:  # 자격 판단 시험을 돌리는 함수입니다
    rows = []  # 시험 결과를 모을 목록입니다
    for cid, profile, pid, expected, why in JUDGE_CASES:  # 시험 문제를 하나씩 꺼내서
        policy = load_by_ids([pid])[0]  # 정책 내용을 DB에서 읽고
        policy = {**policy, "rule_checks": MET, "documents": []}  # 백엔드 판정은 '충족'으로 두고 AI 판단만 시험합니다
        got = judge_policies(profile, [policy])[0]  # AI 판단 결과를 받습니다
        ok = got["eligibility"] in expected  # 정답 범위 안에 들어가면 맞은 것입니다
        danger = got["eligibility"] == "eligible" and "eligible" not in expected  # 안 되는 사람에게 '신청 가능'이라고 한 경우 (가장 위험한 오답)
        rows.append({  # 결과 한 줄을 기록합니다
            "id": cid, "policy": policy["name"], "expected": sorted(expected), "got": got["eligibility"],  # 번호, 정책, 정답, AI 답
            "ok": ok, "danger": danger, "why": why,  # 맞았는지, 위험한 오답인지, 정답 이유
            "reasons": [f"{r['result']} {r['condition']}: {r['detail']}" for r in got["reasons"] if r["condition"] not in ("나이", "지역")],  # AI가 든 이유
        })
        print(f"  {cid} {'✅' if ok else ('🚨' if danger else '❌')} {policy['name'][:20]} | 정답 {sorted(expected)} | AI {got['eligibility']}")  # 진행 상황을 출력합니다
    return rows  # 전체 결과를 돌려줍니다


def run_rank(k: int = 5) -> list[dict]:  # 정렬(의미 검색) 시험을 돌리는 함수입니다
    rows = []  # 시험 결과를 모을 목록입니다
    all_ids = [p["policy_id"] for p in load_policies()]  # 전체 정책 번호 (백엔드 필터 없이 전체를 후보로 둠)
    for cid, query, pattern, why, scored in RANK_CASES:  # 시험 문장을 하나씩 꺼내서
        found, seen = [], set()  # 고른 정책과, 이미 나온 정책 이름을 기록할 곳입니다
        for p in load_by_ids(rank_policies({"message": query}, all_ids)[: k * 4]):  # 실제 서비스와 같은 방식(조건 뽑기 + 의미 검색 + 보정)으로 정렬해서 넉넉히 가져와
            if p["name"] in seen:  # 이름이 같은 정책(지역만 다른 같은 사업)이 이미 나왔으면
                continue  # 건너뜁니다 (화면에서도 하나로 묶어 보여주는 게 맞아서 하나로 셈)
            seen.add(p["name"])  # 이름을 기록하고
            found.append(p)  # 결과에 넣습니다
            if len(found) == k:  # k개가 모이면
                break  # 그만 찾습니다
        hits = [bool(re.search(pattern, p["name"])) for p in found]  # 정책 이름이 정답 패턴에 맞는지 확인합니다
        score = sum(hits) / k if scored else None  # 위 k개 중 정답 비율입니다 (점수 없는 문제는 None)
        rows.append({"id": cid, "query": query, "score": score, "why": why,  # 번호, 문장, 점수, 설명
                     "top": [("✅ " if h else "❌ ") + p["name"] for p, h in zip(found, hits)] if scored else [p["name"] for p in found]})  # 찾은 정책
        print(f"  {cid} {'(점수 없음)' if score is None else f'{score:.0%}'} | {query}")  # 진행 상황을 출력합니다
        if not scored:  # 점수 없는 문제는
            for p in found:  # 찾은 정책을 그대로 보여 줍니다
                print(f"      - {p['name']}")  # 사람이 보고 판단하도록 출력
    return rows  # 전체 결과를 돌려줍니다


def run_understand() -> list[dict]:  # 조건 뽑기(understood) 시험을 돌리는 함수입니다
    rows = []  # 시험 결과를 모을 목록입니다
    for cid, message, expected, why in UNDERSTAND_CASES:  # 시험 문장을 하나씩 꺼내서
        got = understand_message(message)  # AI가 뽑은 조건
        checks = {}  # 칸별 정답 여부
        for field, want in expected.items():  # 정답에 적힌 칸마다
            value = got.get(field)  # AI가 뽑은 값
            checks[field] = want in (value or []) if field == "categories" else value == want  # 분야는 목록에 들어 있으면 정답, 나머지는 값이 같아야 정답
        rows.append({"id": cid, "message": message, "why": why, "expected": expected, "got": got,  # 번호, 문장, 설명, 정답, AI 결과
                     "checks": checks, "ok": all(checks.values())})  # 칸별 결과, 전부 맞았는지
        print(f"  {cid} {'✅' if all(checks.values()) else '❌'} {message} → {got.get('summary', '')} / 키워드 {got.get('keywords', [])}")  # 진행 상황 출력
    return rows  # 전체 결과를 돌려줍니다


def save(judge: list[dict], rank: list[dict], seconds: float, und: list[dict] | None = None) -> Path:  # 결과를 사람이 읽기 쉬운 파일로 저장하는 함수입니다
    OUT.mkdir(exist_ok=True)  # 결과 폴더가 없으면 만듭니다
    acc = sum(r["ok"] for r in judge) / len(judge)  # 자격 판단 정확도
    danger = sum(r["danger"] for r in judge)  # 위험한 오답 수
    scored = [r["score"] for r in rank if r["score"] is not None]  # 점수가 있는 문제만 모읍니다
    p_at_k = sum(scored) / len(scored)  # 정렬 평균 점수
    und = und or []  # 조건 뽑기 결과 (없으면 빈 목록)
    fields = [v for r in und for v in r["checks"].values()]  # 칸별 정답 여부를 모두 모읍니다
    u_acc = sum(fields) / len(fields) if fields else 0  # 조건 뽑기 칸별 정확도
    stamp = datetime.now().strftime("%Y%m%d_%H%M")  # 파일 이름에 쓸 시각
    lines = [  # 결과 파일 내용입니다
        f"# 페르소나 테스트 결과 ({stamp})", "",  # 제목
        f"- 모델: `{settings.GEMINI_MODEL}` / 임베딩: `{settings.EMBED_MODEL}` / 생각 단계: `{settings.GEMINI_THINKING_LEVEL}` / 핵심 단어 덧붙이기: `{settings.RANK_USE_KEYWORDS}` / 키워드 보정: `{settings.RANK_KEYWORD_BOOST}`",  # 설정
        f"- **자격 판단 정확도: {acc:.0%}** ({sum(r['ok'] for r in judge)}/{len(judge)})",  # 정확도
        f"- **위험한 오답(안 되는데 '신청 가능'): {danger}건**",  # 위험한 오답
        f"- **정렬 정확도(같은 이름 정책은 하나로 묶은 위 5개 중, 사람이 정한 정답 비율): {p_at_k:.0%}**",  # 정렬 점수
        f"- **조건 뽑기(understood) 정확도(칸별): {u_acc:.0%}**",  # 조건 뽑기 점수
        f"- 걸린 시간: {seconds:.0f}초", "",  # 시간
        "## 자격 판단", "", "| 번호 | 정책 | 정답 | AI | 결과 | 정답 이유 | AI가 든 이유 |", "|---|---|---|---|---|---|---|",  # 표 머리
    ]
    for r in judge:  # 자격 판단 결과를 한 줄씩
        mark = "✅" if r["ok"] else ("🚨" if r["danger"] else "❌")  # 맞음/위험/틀림 표시
        lines.append(f"| {r['id']} | {r['policy']} | {', '.join(r['expected'])} | {r['got']} | {mark} | {r['why']} | {'<br>'.join(r['reasons'])} |")  # 표 한 줄
    lines += ["", "## 정렬 (의미 검색)", ""]  # 정렬 결과 제목
    for r in rank:  # 정렬 결과를 하나씩
        score = "점수 없음" if r["score"] is None else f"{r['score']:.0%}"  # 점수 표시
        lines += [f"**{r['id']} {r['query']}** — {score} ({r['why']})", *[f"- {t}" for t in r["top"]], ""]  # 문장, 점수, 찾은 정책
    lines += ["## 조건 뽑기 (understood)", "", "| 번호 | 문장 | 정답 | AI 결과 | 결과 |", "|---|---|---|---|---|"]  # 표 머리
    for r in und:  # 조건 뽑기 결과를 한 줄씩
        got = {k: r["got"].get(k) for k in ("job_status", "education", "marital_status", "categories", "keywords", "summary")}  # 보여 줄 칸만
        lines.append(f"| {r['id']} | {r['message']} | {r['expected']} | {got} | {'✅' if r['ok'] else '❌ ' + ', '.join(k for k, v in r['checks'].items() if not v)} |")  # 표 한 줄
    path = OUT / f"result_{stamp}.md"  # 저장할 파일 경로
    path.write_text("\n".join(lines), encoding="utf-8")  # 파일로 저장합니다
    (OUT / f"result_{stamp}.json").write_text(json.dumps({"judge": judge, "rank": rank, "understand": und}, ensure_ascii=False, indent=2), encoding="utf-8")  # 비교용 원본 데이터도 저장합니다
    print(f"\n자격 판단 {acc:.0%} | 위험한 오답 {danger}건 | 정렬 {p_at_k:.0%} | 조건 뽑기 {u_acc:.0%} | {seconds:.0f}초")  # 요약을 출력합니다
    return path  # 저장한 파일 경로를 돌려줍니다


if __name__ == "__main__":  # 'python -m ai.eval.run'으로 실행했을 때만 아래가 돌아갑니다
    t = time.time()  # 시작 시각
    print("[자격 판단]")  # 1부 제목
    judge = run_judge()  # 자격 판단 시험
    print("\n[조건 뽑기]")  # 2부 제목
    und = run_understand()  # 조건 뽑기 시험
    print("\n[정렬]")  # 3부 제목
    rank = run_rank()  # 정렬 시험
    print("결과 파일:", save(judge, rank, time.time() - t, und))  # 결과를 저장하고 경로를 알려 줍니다
