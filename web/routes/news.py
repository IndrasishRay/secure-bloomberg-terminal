from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.news import NewsManager
from web.auth import get_current_user

router = APIRouter(prefix="/api/news", tags=["news"])

news_manager = NewsManager()


@router.get("/headlines")
async def get_headlines(
    limit: int = Query(20, ge=1, le=100, description="Number of headlines"),
    category: str = Query("general", description="News category"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    try:
        return news_manager.get_headlines(limit)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/search")
async def search_news(
    q: str = Query("", description="Search query"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    if not q:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query parameter 'q' is required")
    try:
        return news_manager.search_news(q)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/company/{symbol}")
async def get_company_news(
    symbol: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    try:
        return news_manager.search_news(symbol)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
