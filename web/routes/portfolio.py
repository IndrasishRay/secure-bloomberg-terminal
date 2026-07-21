from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.portfolio import TradingManager
from src.storage.database import db
from web.auth import get_current_user

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class TradeRequest(BaseModel):
    symbol: str = Field(..., min_length=1, description="Ticker symbol")
    side: str = Field(..., pattern="^(buy|sell)$", description="Trade side")
    quantity: float = Field(..., gt=0, description="Number of shares")


class CreatePortfolioRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Portfolio name")
    initial_cash: float = Field(100000.0, ge=0, description="Starting cash balance")


def _make_manager(request: Request, current_user: dict[str, Any]) -> TradingManager:
    ip = request.client.host if request.client else "127.0.0.1"
    username = current_user.get("username", current_user.get("sub", "system"))
    return TradingManager(user=username, ip_address=ip)


@router.get("")
async def list_portfolios(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    try:
        from src.portfolio.manager import PortfolioManager

        mgr = PortfolioManager()
        return mgr.list_portfolios()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("")
async def create_portfolio(
    body: CreatePortfolioRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        mgr = _make_manager(request, current_user)
        pid = mgr.create_portfolio(body.name, body.initial_cash)
        return {"id": pid, "name": body.name, "initial_cash": body.initial_cash}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{portfolio_id}")
async def get_portfolio(
    portfolio_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        from src.portfolio.manager import PortfolioManager

        mgr = PortfolioManager()
        return mgr.get_portfolio(portfolio_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{portfolio_id}/positions")
async def get_positions(
    portfolio_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    try:
        from src.portfolio.manager import PortfolioManager

        mgr = PortfolioManager()
        return mgr.get_positions(portfolio_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{portfolio_id}/trade")
async def execute_trade(
    portfolio_id: int,
    body: TradeRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        mgr = _make_manager(request, current_user)
        portfolio = db.get_portfolio(portfolio_id)
        if portfolio is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Portfolio {portfolio_id} not found")

        from src.market import market_data

        quote = market_data.get_quote(body.symbol.upper())
        price: float = 0.0
        if "error" not in quote:
            price = float(quote.get("price", 0.0))

        if price <= 0:
            price = 0.01

        result = mgr.execute_trade(
            symbol=body.symbol,
            side=body.side,
            quantity=body.quantity,
            price=price,
            portfolio_id=portfolio_id,
        )
        if not result.get("success"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message", "Trade rejected"))
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{portfolio_id}/trades")
async def get_trade_history(
    portfolio_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    try:
        mgr = TradingManager()
        return mgr.get_trade_history(portfolio_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{portfolio_id}/risk")
async def get_risk_summary(
    portfolio_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        mgr = TradingManager()
        summary = mgr.get_risk_summary(portfolio_id)
        if not summary:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Portfolio {portfolio_id} not found")
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
