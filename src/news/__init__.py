from __future__ import annotations

import time
from collections import defaultdict
from typing import Optional

from src.news.finnhub_provider import FinnhubNewsProvider
from src.news.rss_provider import RSSNewsProvider


class NewsManager:
    def __init__(self, finnhub_provider: Optional[FinnhubNewsProvider] = None):
        self.finnhub = finnhub_provider or FinnhubNewsProvider()
        self.rss = RSSNewsProvider()
        self._headline_cache: list[dict] = []
        self._last_refresh: float = 0
        self._refresh_interval: int = 300

    def get_headlines(self, limit: int = 20) -> list[dict]:
        if time.time() - self._last_refresh > self._refresh_interval:
            self._refresh_feeds()
            self._last_refresh = time.time()
        return self._headline_cache[:limit]

    def search_news(self, query: str) -> list[dict]:
        rss_results = self.rss.get_news_by_symbol(query)
        seen = {a.get("url") for a in rss_results}
        try:
            finnhub_results = self.finnhub.get_company_news(query, "", "")
            for article in finnhub_results:
                if article.get("url") not in seen:
                    rss_results.append(article)
                    seen.add(article["url"])
        except Exception:
            pass
        return rss_results

    def refresh_feeds(self) -> None:
        self._refresh_feeds()
        self._last_refresh = time.time()

    def _refresh_feeds(self) -> None:
        all_articles: list[dict] = []
        seen: set[str] = set()

        rss_articles = self.rss.get_latest_news(limit=30)
        for article in rss_articles:
            url = article.get("url")
            if url and url not in seen:
                all_articles.append(article)
                seen.add(url)

        for category in ("general", "forex", "crypto", "merger"):
            try:
                for article in self.finnhub.get_market_news(category=category):
                    url = article.get("url")
                    if url and url not in seen:
                        all_articles.append(article)
                        seen.add(url)
            except Exception:
                continue

        all_articles.sort(key=lambda x: x.get("datetime", ""), reverse=True)
        self._headline_cache = all_articles
