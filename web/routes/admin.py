from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from src.storage.database import db
from web.auth import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/health")
async def health_check() -> dict[str, Any]:
    return {"status": "healthy", "service": "Secure Bloomberg Terminal API"}


@router.get("/audit-log")
async def get_audit_log(
    limit: int = 50,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    try:
        logs = db.get_recent_audit_logs(limit)
        return [
            {
                "id": log.id,
                "action": log.action,
                "user": log.user,
                "details": log.details,
                "ip_address": log.ip_address,
                "timestamp": log.timestamp.isoformat() if log.timestamp else "",
            }
            for log in logs
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/metrics")
async def get_metrics(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        portfolios = db.list_portfolios()
        total_portfolios = len(portfolios)

        total_cash = sum(p.cash_balance for p in portfolios)
        total_positions = 0
        for p in portfolios:
            positions = db.get_positions_by_portfolio(p.id)
            total_positions += len(positions)

        audit_count = len(db.get_recent_audit_logs(1000))

        return {
            "total_portfolios": total_portfolios,
            "total_cash": round(total_cash, 2),
            "total_positions": total_positions,
            "recent_audit_entries": audit_count,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
