from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

import feedparser
import httpx

DEFAULT_FEEDS = {
    "Reuters": "https://www.reutersagency.com/feed/",
    "Bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
    "CNBC": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
}

FETCH_TIMEOUT = 15


class RSSNewsProvider:
    def __init__(self, feeds: Optional[dict[str, str]] = None):
        self.feeds = feeds or dict(DEFAULT_FEEDS)
        self._cache: dict[str, tuple[float, list[dict]]] = {}
        self._cache_ttl: int = 300

    def get_latest_news(self, limit: int = 20) -> list[dict]:
        cached = self._get_from_cache("latest")
        if cached is not None:
            return cached[:limit]

        all_entries: list[dict] = []
        for name, url in self.feeds.items():
            try:
                entries = self._fetch_feed(name, url)
                all_entries.extend(entries)
            except Exception:
                continue

        all_entries.sort(key=lambda x: x.get("published", ""), reverse=True)
        self._set_in_cache("latest", all_entries)
        return all_entries[:limit]

    def get_news_by_symbol(self, symbol: str) -> list[dict]:
        symbol_lower = symbol.lower()
        results: list[dict] = []
        seen_urls: set[str] = set()

        for name, url in self.feeds.items():
            try:
                entries = self._fetch_feed(name, url)
                for entry in entries:
                    text = f"{entry.get('title', '')} {entry.get('summary', '')}"
                    if symbol_lower in text.lower():
                        u = entry.get("url")
                        if u and u not in seen_urls:
                            results.append(entry)
                            seen_urls.add(u)
            except Exception:
                continue

        results.sort(key=lambda x: x.get("published", ""), reverse=True)
        return results

    def _fetch_feed(self, name: str, url: str) -> list[dict]:
        key = f"feed:{name}"
        cached = self._get_from_cache(key)
        if cached is not None:
            return cached

        try:
            with httpx.Client(timeout=FETCH_TIMEOUT, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                content = resp.text
        except Exception:
            return []

        feed = feedparser.parse(content)
        entries = self._normalize_entries(name, feed.entries)
        self._set_in_cache(key, entries)
        return entries

    def _normalize_entries(
        self, source_name: str, entries: list
    ) -> list[dict]:
        result: list[dict] = []
        for entry in entries:
            published = entry.get("published_parsed")
            published_ts = ""
            if published:
                try:
                    published_ts = datetime(
                        *published[:6], tzinfo=timezone.utc
                    ).isoformat()
                except Exception:
                    published_ts = entry.get("published", "")

            result.append(
                {
                    "title": entry.get("title", ""),
                    "summary": _get_summary(entry),
                    "url": entry.get("link", ""),
                    "source": source_name,
                    "datetime": published_ts,
                    "image_url": _get_image(entry),
                    "related_symbols": [],
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


def _get_summary(entry) -> str:
    summary = entry.get("summary", "")
    if not summary:
        summary = entry.get("description", "")
    if hasattr(entry, "content") and entry.content:
        summary = entry.content[0].get("value", summary)
    return summary


def _get_image(entry) -> str:
    media_content = entry.get("media_content")
    if media_content:
        return media_content[0].get("url", "")
    media_thumbnail = entry.get("media_thumbnail")
    if media_thumbnail:
        return media_thumbnail[0].get("url", "")
    return ""
