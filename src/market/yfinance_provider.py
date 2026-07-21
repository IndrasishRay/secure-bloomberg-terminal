from __future__ import annotations

import time
from typing import Any

import yfinance as yf

from src.market.provider import MarketProvider


class YFinanceProvider(MarketProvider):
    CACHE_DURATION = 60.0

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, Any]] = {}

    def _cached(self, key: str, fetcher: callable) -> Any:
        now = time.monotonic()
        if key in self._cache:
            ts, val = self._cache[key]
            if now - ts < self.CACHE_DURATION:
                return val
        val = fetcher()
        self._cache[key] = (now, val)
        return val

    def _parse_quote(self, ticker: yf.Ticker) -> dict[str, Any]:
        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            pass

        fast = ticker.fast_info if hasattr(ticker, "fast_info") else None

        price = None
        for attr in ("currentPrice", "regularMarketPrice", "previousClose"):
            v = info.get(attr) or (getattr(fast, attr, None) if fast else None)
            if v is not None:
                price = float(v)
                break

        prev_close = info.get("previousClose")
        if prev_close is None and fast is not None:
            prev_close = getattr(fast, "previousClose", None)
        prev_close = float(prev_close) if prev_close is not None else None

        change = info.get("regularMarketChange")
        change_pct = info.get("regularMarketChangePercent")
        if change is None and price is not None and prev_close is not None:
            change = round(price - prev_close, 2)
            change_pct = round((change / prev_close) * 100, 2) if prev_close else None

        name: str | None = info.get("longName") or info.get("shortName")
        symbol: str = info.get("symbol") or ticker.ticker or ""

        return {
            "symbol": symbol,
            "name": name or symbol,
            "price": float(price) if price is not None else 0.0,
            "change": float(change) if change is not None else 0.0,
            "change_pct": float(change_pct) if change_pct is not None else 0.0,
            "volume": int(info.get("volume") or info.get("regularMarketVolume", 0)),
            "market_cap": info.get("marketCap"),
            "high": float(info.get("dayHigh", 0) or 0),
            "low": float(info.get("dayLow", 0) or 0),
            "open": float(info.get("regularMarketOpen", 0) or 0),
            "prev_close": prev_close if prev_close is not None else 0.0,
            "timestamp": info.get("regularMarketTime"),
        }

    def get_quote(self, symbol: str) -> dict[str, Any]:
        try:
            ticker = yf.Ticker(symbol)
            return self._cached(f"quote:{symbol}", lambda: self._parse_quote(ticker))
        except Exception as exc:
            return {"symbol": symbol, "error": str(exc)}

    def get_history(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> list[dict[str, Any]]:
        key = f"history:{symbol}:{period}:{interval}"

        def _fetch() -> list[dict[str, Any]]:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                return []
            records: list[dict[str, Any]] = []
            for idx, row in df.iterrows():
                records.append(
                    {
                        "date": str(idx),
                        "open": float(row.get("Open", 0)),
                        "high": float(row.get("High", 0)),
                        "low": float(row.get("Low", 0)),
                        "close": float(row.get("Close", 0)),
                        "volume": int(row.get("Volume", 0)),
                    }
                )
            return records

        return self._cached(key, _fetch)

    def get_market_status(self) -> dict[str, Any]:
        try:
            ticker = yf.Ticker("SPY")
            info = ticker.info or {}
            cal = ticker.calendar
            is_open = info.get("regularMarketPrice") is not None
            next_open = None
            next_close = None
            if cal is not None and not cal.empty:
                try:
                    if "Ex-Dividend Date" in cal:
                        pass
                    dates = cal.index.tolist()
                    for d in dates:
                        label = str(d)
                        if "open" in label.lower():
                            next_open = str(cal[d].iloc[0]) if not cal[d].empty else None
                        elif "close" in label.lower():
                            next_close = str(cal[d].iloc[0]) if not cal[d].empty else None
                except Exception:
                    pass
            return {
                "is_open": is_open,
                "next_open": next_open,
                "next_close": next_close,
            }
        except Exception as exc:
            return {"is_open": False, "next_open": None, "next_close": None, "error": str(exc)}

    def search_symbols(self, query: str) -> list[dict[str, Any]]:
        key = f"search:{query}"

        def _fetch() -> list[dict[str, Any]]:
            try:
                results = yf.Search(query)
                quotes = getattr(results, "quotes", []) or []
                return [
                    {
                        "symbol": q.get("symbol", ""),
                        "name": q.get("shortname") or q.get("longname", ""),
                        "exchange": q.get("exchange", ""),
                        "type": q.get("typeDisp", ""),
                    }
                    for q in quotes
                ]
            except Exception:
                return []

        return self._cached(key, _fetch)
