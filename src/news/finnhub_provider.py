from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

import httpx

from config.settings import settings

FINNHUB_BASE = "https://finnhub.io/api/v1"

CATEGORY_MAP = {
    "general": "general",
    "forex": "forex",
    "crypto": "crypto",
    "merger": "merger",
}


class FinnhubNewsProvider:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.finnhub_api_key
        self._cache: dict[str, tuple[float, list[dict]]] = {}
        self._cache_ttl: int = 300

    def get_market_news(self, category: str = "general") -> list[dict]:
        cat = CATEGORY_MAP.get(category, "general")
        cached = self._get_from_cache(f"market_news:{cat}")
        if cached is not None:
            return cached

        url = f"{FINNHUB_BASE}/news"
        params = {"category": cat, "token": self.api_key}
        data = self._request(url, params)
        articles = self._normalize_market_news(data)
        self._set_in_cache(f"market_news:{cat}", articles)
        return articles

    def get_company_news(
        self, symbol: str, from_date: str, to_date: str
    ) -> list[dict]:
        key = f"company_news:{symbol}:{from_date}:{to_date}"
        cached = self._get_from_cache(key)
        if cached is not None:
            return cached

        today = datetime.now().strftime("%Y-%m-%d")
        url = f"{FINNHUB_BASE}/company-news"
        params = {
            "symbol": symbol,
            "from": from_date or today,
            "to": to_date or today,
            "token": self.api_key,
        }
        data = self._request(url, params)
        articles = self._normalize_company_news(data)
        self._set_in_cache(key, articles)
        return articles

    def _request(self, url: str, params: dict) -> list[dict]:
        if not self.api_key:
            return []
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 429:
                time.sleep(1.0)
                resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    def _normalize_market_news(self, raw: list[dict]) -> list[dict]:
        result = []
        for item in raw:
            result.append(
                {
                    "title": item.get("headline", ""),
                    "summary": item.get("summary", ""),
                    "url": item.get("url", ""),
                    "source": item.get("source", "Finnhub"),
                    "datetime": item.get("datetime", 0),
                    "image_url": item.get("image", ""),
                    "related_symbols": item.get("related", "").split(",")
                    if item.get("related")
                    else [],
                }
            )
        return result

    def _normalize_company_news(self, raw: list[dict]) -> list[dict]:
        result = []
        for item in raw:
            result.append(
                {
                    "title": item.get("headline", ""),
                    "summary": item.get("summary", ""),
                    "url": item.get("url", ""),
                    "source": item.get("source", "Finnhub"),
                    "datetime": item.get("datetime", 0),
                    "image_url": item.get("image", ""),
                    "related_symbols": [item.get("symbol", "")],
                }
            )
        return result

    def _get_from_cache(self, key: str) -> Optional[list[dict]]:
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, data = entry
        if time.time() - ts > self._cache_ttl:
            del self._cache[key]
            return None
        return data

    def _set_in_cache(self, key: str, data: list[dict]) -> None:
        self._cache[key] = (time.time(), data)
