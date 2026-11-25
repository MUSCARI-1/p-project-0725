from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path

_FILE = Path(__file__).resolve().parents[1] / "data" / "regions.json"


@lru_cache(maxsize=1)
def load() -> list[dict]:
    return json.loads(_FILE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _parents() -> dict:
    out = {}
    for sido in load():
        for s in sido["sigungu"]:
            out[s["code"]] = s.get("parent")
            if s.get("parent"):
                out.setdefault(s["parent"], None)
    return out


def is_valid(code: str) -> bool:
    return code in _parents()


def match_codes(code: str) -> list[str]:
    # 정책이 상위 시(예: 화성시 41590)나 시도 전체(예: 30000)로 등록된 경우도 같이 찾는다
    codes = [code, code[:2] + "000"]
    parent = _parents().get(code)
    if parent:
        codes.append(parent)
    return codes


def build_from_csv(csv_path: str) -> int:
    sido, sgg = {}, {}
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = row["법정동코드"]
            if code[5:] != "00000":
                continue
            if row["시군구명"]:
                sgg[code[:5]] = row["시군구명"]
            elif code[2:] == "00000000":
                sido[code[:2]] = row["시도명"]

    def parent_of(code):
        p = code[:4] + "0"
        return p if p != code and p in sgg and sgg[code].startswith(sgg[p]) else None

    # 구가 있는 시(수원시 등)는 선택지에서 빼고 구만 남긴다
    parents = {parent_of(c) for c in sgg} - {None}
    data = []
    for sd_code, sd_name in sorted(sido.items()):
        items = []
        for c in sorted(sgg):
            if not c.startswith(sd_code) or c in parents:
                continue
            p = parent_of(c)
            if p:
                items.append({"code": c, "name": f"{sgg[p]} {sgg[c][len(sgg[p]):]}", "parent": p})
            else:
                items.append({"code": c, "name": sgg[c]})
        data.append({"code": sd_code, "name": sd_name, "sigungu": items})

    _FILE.parent.mkdir(parents=True, exist_ok=True)
    _FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    load.cache_clear()
    _parents.cache_clear()
    return sum(len(s["sigungu"]) for s in data)
