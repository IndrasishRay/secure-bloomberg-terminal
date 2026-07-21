from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.market import market_data
from web.auth import get_current_user

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/quote/{symbol}")
async def get_quote(
    symbol: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        result = market_data.get_quote(symbol)
        if "error" in result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/history/{symbol}")
async def get_history(
    symbol: str,
    period: str = Query("1mo", description="Time period"),
    interval: str = Query("1d", description="Bar interval"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    try:
        return market_data.get_history(symbol, period, interval)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/search")
async def search_symbols(
    q: str = Query("", description="Search query"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    if not q:
        return []
    try:
        return market_data.search_symbols(q)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/status")
async def get_market_status(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return market_data.get_market_status()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


DEFAULT_WATCHLIST = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "SPY"]


@router.get("/watchlist")
async def get_watchlist(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for symbol in DEFAULT_WATCHLIST:
        try:
            quote = market_data.get_quote(symbol)
            if "error" not in quote:
                results.append(quote)
        except Exception:
            continue
    return results
