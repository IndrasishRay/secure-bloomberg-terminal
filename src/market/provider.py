from abc import ABC, abstractmethod
from typing import Any


class MarketProvider(ABC):
    @abstractmethod
    def get_quote(self, symbol: str) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_history(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_market_status(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def search_symbols(self, query: str) -> list[dict[str, Any]]:
        ...
