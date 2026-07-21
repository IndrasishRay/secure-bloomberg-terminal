from __future__ import annotations

from typing import Any

from config.settings import settings
from src.market.provider import MarketProvider


class MarketDataManager:
    def __init__(self) -> None:
        self._providers: dict[str, MarketProvider] = {}

    def _has_alpaca_keys(self) -> bool:
        return bool(settings.alpaca_api_key and settings.alpaca_secret_key)

    def _get_or_create(self, key: str, factory: callable) -> MarketProvider:
        if key not in self._providers:
            self._providers[key] = factory()
        return self._providers[key]

    def get_provider(self, asset_type: str = "stock") -> MarketProvider:
        if asset_type == "crypto":
            return self._get_or_create(
                "coingecko",
                lambda: __import__("src.market.coingecko_provider", fromlist=["CoinGeckoProvider"]).CoinGeckoProvider(),
            )
        if self._has_alpaca_keys():
            return self._get_or_create(
                "alpaca",
                lambda: __import__("src.market.alpaca_provider", fromlist=["AlpacaProvider"]).AlpacaProvider(
                    api_key=settings.alpaca_api_key,
                    secret_key=settings.alpaca_secret_key,
                    base_url=settings.alpaca_base_url,
                ),
            )
        return self._get_or_create(
            "yfinance",
            lambda: __import__("src.market.yfinance_provider", fromlist=["YFinanceProvider"]).YFinanceProvider(),
        )

    def get_quote(self, symbol: str, asset_type: str = "stock") -> dict[str, Any]:
        return self.get_provider(asset_type).get_quote(symbol)

    def get_history(
        self, symbol: str, period: str = "1mo", interval: str = "1d", asset_type: str = "stock"
    ) -> list[dict[str, Any]]:
        return self.get_provider(asset_type).get_history(symbol, period, interval)

    def get_market_status(self, asset_type: str = "stock") -> dict[str, Any]:
        return self.get_provider(asset_type).get_market_status()

    def search_symbols(self, query: str, asset_type: str = "stock") -> list[dict[str, Any]]:
        return self.get_provider(asset_type).search_symbols(query)


market_data = MarketDataManager()


__all__ = [
    "MarketProvider",
    "MarketDataManager",
    "market_data",
]
