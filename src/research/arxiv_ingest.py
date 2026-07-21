from __future__ import annotations

import time
from typing import Optional

import arxiv

FINANCE_CATEGORIES = ["q-fin.ST", "q-fin.PM", "q-fin.GN", "q-fin.CP", "q-fin.MF"]
ML_CATEGORIES = ["cs.LG", "cs.AI", "cs.CL", "stat.ML"]


class ArxivResearchProvider:
    def __init__(self):
        self._client = arxiv.Client(page_size=100, delay_seconds=3, num_retries=3)
        self._cache: dict[str, tuple[float, list[dict]]] = {}
        self._cache_ttl: int = 600

    def search_papers(self, query: str, max_results: int = 10) -> list[dict]:
        key = f"search:{query}:{max_results}"
        cached = self._get_from_cache(key)
        if cached is not None:
            return cached[:max_results]

        search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.SubmittedDate)
        papers = self._fetch(search)
        self._set_in_cache(key, papers)
        return papers[:max_results]

    def get_recent_finance_papers(self, limit: int = 10) -> list[dict]:
        key = f"finance:{limit}"
        cached = self._get_from_cache(key)
        if cached is not None:
            return cached[:limit]

        query = " OR ".join(f"cat:{c}" for c in FINANCE_CATEGORIES)
        search = arxiv.Search(query=query, max_results=limit, sort_by=arxiv.SortCriterion.SubmittedDate)
        papers = self._fetch(search)
        self._set_in_cache(key, papers)
        return papers[:limit]

    def get_recent_ml_papers(self, limit: int = 10) -> list[dict]:
        key = f"ml:{limit}"
        cached = self._get_from_cache(key)
        if cached is not None:
            return cached[:limit]

        cat_query = " OR ".join(f"cat:{c}" for c in ML_CATEGORIES)
        query = f"({cat_query}) AND (finance OR trading OR stock OR portfolio OR market OR risk)"
        search = arxiv.Search(query=query, max_results=limit, sort_by=arxiv.SortCriterion.SubmittedDate)
        papers = self._fetch(search)
        self._set_in_cache(key, papers)
        return papers[:limit]

    def _fetch(self, search: arxiv.Search) -> list[dict]:
        results: list[dict] = []
        for result in self._client.results(search):
            results.append(
                {
                    "title": result.title,
                    "authors": [a.name for a in result.authors],
                    "abstract": result.summary,
                    "url": result.entry_id,
                    "published": result.published.isoformat() if result.published else "",
                    "categories": list(result.categories),
                }
            )
        return results

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
