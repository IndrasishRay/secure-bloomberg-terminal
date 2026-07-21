from __future__ import annotations

import time
from typing import Any

import httpx

from src.market.provider import MarketProvider


class CoinGeckoProvider(MarketProvider):
    CACHE_DURATION = 30.0
    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, Any]] = {}
        self._client = httpx.Client(timeout=httpx.Timeout(15.0))

    def _cached(self, key: str, fetcher: callable) -> Any:
        now = time.monotonic()
        if key in self._cache:
            ts, val = self._cache[key]
            if now - ts < self.CACHE_DURATION:
                return val
        val = fetcher()
        self._cache[key] = (now, val)
        return val

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        try:
            resp = self._client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            return {"error": f"CoinGecko HTTP {exc.response.status_code}: {exc.response.text}"}
        except httpx.RequestError as exc:
            return {"error": f"CoinGecko request failed: {exc}"}
        except Exception as exc:
            return {"error": str(exc)}

    def _get_list(self, path: str, params: dict[str, Any] | None = None) -> list[Any]:
        url = f"{self.BASE_URL}{path}"
        try:
            resp = self._client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def get_quote(self, symbol: str) -> dict[str, Any]:
        coin_id = symbol.lower().strip()

        def _fetch() -> dict[str, Any]:
            data = self._get(
                f"/coins/{coin_id}",
                {"localization": "false", "tickers": "false", "community_data": "false"},
            )
            if "error" in data:
                return data
            md = data.get("market_data", {})
            name: str = data.get("name", coin_id)
            return {
                "symbol": coin_id,
                "name": name,
                "price": float(md.get("current_price", {}).get("usd", 0)),
                "change": float(md.get("price_change_24h", 0)),
                "change_pct": float(md.get("price_change_percentage_24h", 0)),
                "volume": int(md.get("total_volume", {}).get("usd", 0)),
                "market_cap": md.get("market_cap", {}).get("usd"),
                "high": float(md.get("high_24h", {}).get("usd", 0)),
                "low": float(md.get("low_24h", {}).get("usd", 0)),
                "open": float(md.get("current_price", {}).get("usd", 0)),
                "prev_close": 0.0,
                "timestamp": data.get("last_updated"),
            }

        return self._cached(f"quote:{coin_id}", _fetch)

    def get_history(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> list[dict[str, Any]]:
        coin_id = symbol.lower().strip()
        days = self._period_to_days(period)

        def _fetch() -> list[dict[str, Any]]:
            data = self._get(f"/coins/{coin_id}/ohlc", {"vs_currency": "usd", "days": str(days)})
            if "error" in data:
                return [{"error": data["error"]}]
            if not isinstance(data, list):
                return []
            records: list[dict[str, Any]] = []
            for entry in data:
                if not isinstance(entry, (list, tuple)) or len(entry) < 5:
                    continue
                records.append(
                    {
                        "date": str(entry[0]),
                        "open": float(entry[1]),
                        "high": float(entry[2]),
                        "low": float(entry[3]),
                        "close": float(entry[4]),
                        "volume": 0,
                    }
                )
            return records

        return self._cached(f"history:{coin_id}:{period}", _fetch)

    def get_market_status(self) -> dict[str, Any]:
        return {"is_open": True, "next_open": None, "next_close": None, "note": "crypto markets are always open"}

    def search_symbols(self, query: str) -> list[dict[str, Any]]:
        def _fetch() -> list[dict[str, Any]]:
            data = self._get_list("/search", {"query": query})
            coins = data.get("coins", []) if isinstance(data, dict) else []
            return [
                {
                    "symbol": c.get("symbol", ""),
                    "name": c.get("name", ""),
                    "exchange": "coingecko",
                    "type": "cryptocurrency",
                }
                for c in coins[:20]
            ]

        return self._cached(f"search:{query}", _fetch)

    @staticmethod
    def _period_to_days(period: str) -> int:
        mapping = {
            "1d": 1,
            "5d": 5,
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
            "2y": 730,
            "5y": 1825,
            "max": "max",
        }
        return mapping.get(period, 30)

    def close(self) -> None:
        self._client.close()
