from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import httpx

from src.market.provider import MarketProvider


class AlpacaProvider(MarketProvider):
    CACHE_DURATION = 60.0

    def __init__(
        self,
        api_key: str = "",
        secret_key: str = "",
        base_url: str = "https://paper-api.alpaca.markets",
    ) -> None:
        self._api_key = api_key
        self._secret_key = secret_key
        self._data_url = "https://data.alpaca.markets"
        self._base_url = base_url.rstrip("/")
        self._cache: dict[str, tuple[float, Any]] = {}
        self._client = httpx.Client(timeout=httpx.Timeout(15.0))

    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self._api_key,
            "APCA-API-SECRET-KEY": self._secret_key,
        }

    def _cached(self, key: str, fetcher: callable) -> Any:
        now = time.monotonic()
        if key in self._cache:
            ts, val = self._cache[key]
            if now - ts < self.CACHE_DURATION:
                return val
        val = fetcher()
        self._cache[key] = (now, val)
        return val

    def _request(self, method: str, url: str) -> dict[str, Any]:
        try:
            resp = self._client.request(method, url, headers=self._headers())
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            return {"error": f"Alpaca HTTP {exc.response.status_code}: {exc.response.text}"}
        except httpx.RequestError as exc:
            return {"error": f"Alpaca request failed: {exc}"}
        except Exception as exc:
            return {"error": str(exc)}

    def get_quote(self, symbol: str) -> dict[str, Any]:
        url = f"{self._data_url}/v2/stocks/{symbol}/quotes/latest"
        data = self._cached(f"quote:{symbol}", lambda: self._request("GET", url))

        if "error" in data:
            return {"symbol": symbol, "error": data["error"]}

        quote = data.get("quote", data)
        ask = quote.get("ap", 0) or quote.get("ask_price", 0)
        bid = quote.get("bp", 0) or quote.get("bid_price", 0)
        price = float(ask) if ask else (float(bid) if bid else 0.0)
        ask_size = quote.get("as", 0) or quote.get("ask_size", 0)
        bid_size = quote.get("bs", 0) or quote.get("bid_size", 0)
        timestamp = quote.get("t", quote.get("timestamp"))

        return {
            "symbol": symbol.upper(),
            "name": symbol.upper(),
            "price": price,
            "change": 0.0,
            "change_pct": 0.0,
            "volume": int(ask_size) + int(bid_size),
            "market_cap": None,
            "high": price,
            "low": price,
            "open": price,
            "prev_close": 0.0,
            "timestamp": timestamp,
        }

    def get_history(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> list[dict[str, Any]]:
        timeframe = self._interval_to_alpaca(interval)
        utc_now = datetime.now(timezone.utc)
        start = self._period_to_start(period, utc_now)
        end = utc_now.strftime("%Y-%m-%dT%H:%M:%SZ")
        start_s = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        url = (
            f"{self._data_url}/v2/stocks/{symbol}/bars"
            f"?timeframe={timeframe}&start={start_s}&end={end}&limit=1000"
        )

        data = self._cached(
            f"history:{symbol}:{period}:{interval}",
            lambda: self._request("GET", url),
        )

        if "error" in data:
            return [{"error": data["error"]}]

        bars = data.get("bars", [])
        records: list[dict[str, Any]] = []
        for bar in bars:
            records.append(
                {
                    "date": bar.get("t", ""),
                    "open": float(bar.get("o", 0)),
                    "high": float(bar.get("h", 0)),
                    "low": float(bar.get("l", 0)),
                    "close": float(bar.get("c", 0)),
                    "volume": int(bar.get("v", 0)),
                }
            )
        return records

    def get_market_status(self) -> dict[str, Any]:
        url = f"{self._base_url}/v2/clock"
        data = self._cached("clock", lambda: self._request("GET", url))

        if "error" in data:
            return {"is_open": False, "next_open": None, "next_close": None, "error": data["error"]}

        return {
            "is_open": bool(data.get("is_open", False)),
            "next_open": data.get("next_open"),
            "next_close": data.get("next_close"),
        }

    def search_symbols(self, query: str) -> list[dict[str, Any]]:
        url = f"{self._data_url}/v2/symbols?search={query}&limit=50"
        data = self._cached(f"search:{query}", lambda: self._request("GET", url))

        if "error" in data:
            return [{"error": data["error"]}]

        symbols = data if isinstance(data, list) else data.get("symbols", [])
        return [
            {
                "symbol": s.get("symbol", ""),
                "name": s.get("name", ""),
                "exchange": s.get("exchange", ""),
                "type": s.get("type", ""),
            }
            for s in symbols
        ]

    @staticmethod
    def _interval_to_alpaca(interval: str) -> str:
        mapping = {
            "1m": "1Min",
            "5m": "5Min",
            "15m": "15Min",
            "1d": "1Day",
            "1wk": "1Week",
            "1mo": "1Month",
        }
        return mapping.get(interval, "1Day")

    @staticmethod
    def _period_to_start(period: str, now: datetime) -> datetime:
        mapping: dict[str, Any] = {
            "1d": lambda: now.replace(hour=0, minute=0, second=0, microsecond=0),
            "5d": lambda: now - __import__("datetime").timedelta(days=5),
            "1mo": lambda: now - __import__("datetime").timedelta(days=30),
            "3mo": lambda: now - __import__("datetime").timedelta(days=90),
            "6mo": lambda: now - __import__("datetime").timedelta(days=180),
            "1y": lambda: now - __import__("datetime").timedelta(days=365),
            "2y": lambda: now - __import__("datetime").timedelta(days=730),
            "5y": lambda: now - __import__("datetime").timedelta(days=1825),
            "max": lambda: datetime(2000, 1, 1, tzinfo=timezone.utc),
        }
        return mapping.get(period, mapping["1mo"])()

    def close(self) -> None:
        self._client.close()
