from __future__ import annotations

import time
from typing import Iterator

import requests


class YouthCenterError(RuntimeError):
    pass


class YouthCenterClient:
    def __init__(self, api_key: str, base_url: str, timeout: int = 60, retries: int = 3):
        if not api_key:
            raise YouthCenterError("YOUTHCENTER_API_KEY 가 비어 있습니다. 루트 .env 를 확인하세요.")
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.retries = retries

    def fetch_page(self, page: int, size: int = 100) -> tuple[list[dict], int]:
        params = {"apiKeyNm": self.api_key, "pageNum": page, "pageSize": size, "rtnType": "json"}
        last_error = None
        for attempt in range(1, self.retries + 1):
            try:
                resp = requests.get(self.base_url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                if str(data.get("resultCode")) != "200":
                    raise YouthCenterError(f"API 오류: {data.get('resultCode')} {data.get('resultMessage')}")
                result = data.get("result") or {}
                items = result.get("youthPolicyList") or []
                total = int((result.get("pagging") or {}).get("totCount") or 0)
                return items, total
            except (requests.RequestException, ValueError, YouthCenterError) as e:
                last_error = e
                time.sleep(attempt)
        raise YouthCenterError(f"{page} 페이지 조회 실패: {last_error}")

    def iter_pages(self, size: int = 100, max_pages: int | None = None) -> Iterator[tuple[int, list[dict], int]]:
        page = 1
        fetched = 0
        while True:
            items, total = self.fetch_page(page, size)
            if not items:
                return
            fetched += len(items)
            yield page, items, total
            if fetched >= total or (max_pages and page >= max_pages):
                return
            page += 1
