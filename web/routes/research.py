from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.research import ResearchManager
from web.auth import get_current_user

router = APIRouter(prefix="/api/research", tags=["research"])

research_manager = ResearchManager()


@router.get("/papers")
async def get_papers(
    limit: int = Query(10, ge=1, le=50, description="Number of papers"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    try:
        return research_manager.get_recent_finance_papers(limit)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/search")
async def search_papers(
    q: str = Query("", description="Search query"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    if not q:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query parameter 'q' is required")
    try:
        return research_manager.search_papers(q)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
