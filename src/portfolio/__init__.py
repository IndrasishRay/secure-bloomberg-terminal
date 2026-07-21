from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional

from src.portfolio.manager import PortfolioManager, PriceProvider
from src.portfolio.risk_guard import RiskGuard
from src.storage.database import db


class TradingManager:
    def __init__(
        self,
        price_provider: Optional[PriceProvider] = None,
        user: str = "system",
        ip_address: str = "",
    ) -> None:
        self._portfolio_manager = PortfolioManager(price_provider)
        self._risk_guard = RiskGuard(price_provider)
        self._user = user
        self._ip_address = ip_address

    def set_price_provider(self, provider: PriceProvider) -> None:
        self._portfolio_manager.set_price_provider(provider)
        self._risk_guard.set_price_provider(provider)

    def set_user(self, user: str) -> None:
        self._user = user

    def execute_trade(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        portfolio_id: int,
    ) -> dict:
        approved, reason = self._risk_guard.check_trade(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            portfolio_id=portfolio_id,
        )

        if not approved:
            db.create_audit_log(
                action="trade.rejected",
                user=self._user,
                details=(
                    f"portfolio_id={portfolio_id} symbol={symbol.upper()} "
                    f"side={side} qty={quantity} price={price} "
                    f"reason={reason}"
                ),
                ip_address=self._ip_address,
            )
            return {
                "success": False,
                "message": reason,
                "trade_id": None,
            }

        try:
            side = side.lower()
            if side == "buy":
                result = self._portfolio_manager.add_position(
                    portfolio_id, symbol, quantity, price
                )
            elif side == "sell":
                result = self._portfolio_manager.remove_position(
                    portfolio_id, symbol, quantity, price
                )
            else:
                return {
                    "success": False,
                    "message": f"Invalid side: {side}",
                    "trade_id": None,
                }

            trade_id = result.get("trade_id")

            db.create_audit_log(
                action="trade.executed",
                user=self._user,
                details=(
                    f"portfolio_id={portfolio_id} symbol={symbol.upper()} "
                    f"side={side} qty={quantity} price={price} "
                    f"trade_id={trade_id}"
                ),
                ip_address=self._ip_address,
            )

            self._risk_guard.record_trade_result(
                portfolio_id, side, quantity, price, success=True
            )

            return {
                "success": True,
                "message": f"{side.upper()} {quantity} {symbol.upper()} @ ${price:.2f}",
                "trade_id": trade_id,
                "details": result,
            }

        except (ValueError, KeyError) as e:
            db.create_audit_log(
                action="trade.failed",
                user=self._user,
                details=(
                    f"portfolio_id={portfolio_id} symbol={symbol.upper()} "
                    f"side={side} qty={quantity} price={price} error={e}"
                ),
                ip_address=self._ip_address,
            )
            return {
                "success": False,
                "message": str(e),
                "trade_id": None,
            }

    def create_portfolio(
        self, name: str, initial_cash: float = 100000.0
    ) -> int:
        return self._portfolio_manager.create_portfolio(name, initial_cash)

    def get_portfolio(self, portfolio_id: int) -> dict:
        return self._portfolio_manager.get_portfolio(portfolio_id)

    def list_portfolios(self) -> list[dict]:
        return self._portfolio_manager.list_portfolios()

    def get_positions(self, portfolio_id: int) -> list[dict]:
        return self._portfolio_manager.get_positions(portfolio_id)

    def get_portfolio_value(self, portfolio_id: int) -> float:
        return self._portfolio_manager.get_portfolio_value(portfolio_id)

    def get_risk_summary(self, portfolio_id: int) -> dict:
        return self._risk_guard.get_risk_summary(portfolio_id)

    def reset_daily_limits(self) -> None:
        self._risk_guard.reset_daily_limits()

    def reset_circuit_breaker(self, portfolio_id: int) -> None:
        self._risk_guard.reset_circuit_breaker(portfolio_id)

    def get_trade_history(self, portfolio_id: int) -> list[dict]:
        return self._portfolio_manager.get_trade_history(portfolio_id)


__all__ = [
    "PortfolioManager",
    "RiskGuard",
    "TradingManager",
    "PriceProvider",
]
