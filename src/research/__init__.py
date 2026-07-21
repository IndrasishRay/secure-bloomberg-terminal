from __future__ import annotations

from typing import Optional

from src.research.arxiv_ingest import ArxivResearchProvider


class ResearchManager:
    def __init__(self, arxiv_provider: Optional[ArxivResearchProvider] = None):
        self.arxiv = arxiv_provider or ArxivResearchProvider()

    def search_papers(self, query: str, max_results: int = 10) -> list[dict]:
        return self.arxiv.search_papers(query, max_results)

    def get_recent_finance_papers(self, limit: int = 10) -> list[dict]:
        return self.arxiv.get_recent_finance_papers(limit)

    def get_recent_ml_papers(self, limit: int = 10) -> list[dict]:
        return self.arxiv.get_recent_ml_papers(limit)
