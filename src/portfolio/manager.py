from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional

from src.storage.database import db
from src.storage.models import Position, Trade


PriceProvider = Callable[[str], Optional[float]]


class PortfolioManager:
    def __init__(self, price_provider: Optional[PriceProvider] = None) -> None:
        self._price_provider = price_provider

    def set_price_provider(self, provider: PriceProvider) -> None:
        self._price_provider = provider

    def create_portfolio(
        self, name: str, initial_cash: float = 100000.0
    ) -> int:
        if not name or not name.strip():
            raise ValueError("Portfolio name cannot be empty")
        if initial_cash < 0:
            raise ValueError("Initial cash cannot be negative")
        portfolio = db.create_portfolio(name.strip(), round(initial_cash, 2))
        db.create_audit_log(
            action="portfolio.create",
            user="system",
            details=f"portfolio_id={portfolio.id} name={name} cash={initial_cash}",
        )
        return portfolio.id

    def get_portfolio(self, portfolio_id: int) -> dict:
        portfolio = db.get_portfolio(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        positions = db.get_positions_by_portfolio(portfolio_id)
        total_position_value = sum(p.current_value for p in positions)
        total_value = portfolio.cash_balance + total_position_value
        cost_basis = sum(p.quantity * p.avg_cost for p in positions)
        pnl = total_position_value - cost_basis

        return {
            "id": portfolio.id,
            "name": portfolio.name,
            "cash": round(portfolio.cash_balance, 2),
            "positions": [
                {
                    "id": p.id,
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_cost": p.avg_cost,
                    "current_value": round(p.current_value, 2),
                }
                for p in positions
            ],
            "total_position_value": round(total_position_value, 2),
            "total_value": round(total_value, 2),
            "pnl": round(pnl, 2),
            "created_at": portfolio.created_at.isoformat() if portfolio.created_at else "",
            "updated_at": portfolio.updated_at.isoformat() if portfolio.updated_at else "",
        }

    def list_portfolios(self) -> list[dict]:
        portfolios = db.list_portfolios()
        result = []
        for p in portfolios:
            positions = db.get_positions_by_portfolio(p.id)
            total_position_value = sum(pos.current_value for pos in positions)
            total_value = p.cash_balance + total_position_value
            cost_basis = sum(pos.quantity * pos.avg_cost for pos in positions)
            pnl = total_position_value - cost_basis
            result.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "cash": round(p.cash_balance, 2),
                    "position_count": len(positions),
                    "total_value": round(total_value, 2),
                    "pnl": round(pnl, 2),
                }
            )
        return result

    def add_position(
        self,
        portfolio_id: int,
        symbol: str,
        quantity: float,
        price: float,
    ) -> dict:
        portfolio = db.get_portfolio(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if price <= 0:
            raise ValueError("Price must be positive")

        cost = round(quantity * price, 2)
        if cost > portfolio.cash_balance:
            raise ValueError(
                f"Insufficient cash: need {cost}, have {portfolio.cash_balance}"
            )

        symbol = symbol.upper()
        existing = db.get_position_by_symbol(portfolio_id, symbol)

        if existing is not None:
            total_qty = existing.quantity + quantity
            total_cost = (existing.quantity * existing.avg_cost) + (quantity * price)
            new_avg = round(total_cost / total_qty, 2)
            new_value = round(total_qty * price, 2)
            db.update_position(existing.id, total_qty, new_avg, new_value)
            position_id = existing.id
        else:
            pos = db.create_position(portfolio_id, symbol, quantity, round(price, 2))
            position_id = pos.id

        new_cash = round(portfolio.cash_balance - cost, 2)
        db.update_portfolio_cash(portfolio_id, new_cash)

        trade = db.create_trade(portfolio_id, symbol, "buy", quantity, price)

        db.create_audit_log(
            action="position.add",
            user="system",
            details=(
                f"portfolio_id={portfolio_id} symbol={symbol} "
                f"qty={quantity} price={price} trade_id={trade.id}"
            ),
        )

        return {
            "position_id": position_id,
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "cost": cost,
            "remaining_cash": new_cash,
            "trade_id": trade.id,
        }

    def remove_position(
        self,
        portfolio_id: int,
        symbol: str,
        quantity: float,
        price: float,
    ) -> dict:
        portfolio = db.get_portfolio(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if price <= 0:
            raise ValueError("Price must be positive")

        symbol = symbol.upper()
        existing = db.get_position_by_symbol(portfolio_id, symbol)
        if existing is None:
            raise ValueError(f"No position found for {symbol}")
        if quantity > existing.quantity:
            raise ValueError(
                f"Cannot remove {quantity} shares, only {existing.quantity} held"
            )

        proceeds = round(quantity * price, 2)
        remaining_qty = existing.quantity - quantity

        if remaining_qty == 0:
            db.delete_position(existing.id)
        else:
            new_value = round(remaining_qty * price, 2)
            db.update_position(
                existing.id, remaining_qty, existing.avg_cost, new_value
            )

        new_cash = round(portfolio.cash_balance + proceeds, 2)
        db.update_portfolio_cash(portfolio_id, new_cash)

        trade = db.create_trade(portfolio_id, symbol, "sell", quantity, price)

        db.create_audit_log(
            action="position.remove",
            user="system",
            details=(
                f"portfolio_id={portfolio_id} symbol={symbol} "
                f"qty={quantity} price={price} trade_id={trade.id}"
            ),
        )

        return {
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "proceeds": proceeds,
            "remaining_cash": new_cash,
            "remaining_quantity": remaining_qty,
            "trade_id": trade.id,
        }

    def get_positions(self, portfolio_id: int) -> list[dict]:
        portfolio = db.get_portfolio(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        positions = db.get_positions_by_portfolio(portfolio_id)
        return [
            {
                "id": p.id,
                "portfolio_id": p.portfolio_id,
                "symbol": p.symbol,
                "quantity": p.quantity,
                "avg_cost": p.avg_cost,
                "current_value": round(p.current_value, 2),
                "unrealized_pnl": round(
                    (p.current_value - (p.quantity * p.avg_cost)), 2
                ),
            }
            for p in positions
        ]

    def get_portfolio_value(self, portfolio_id: int) -> float:
        portfolio = db.get_portfolio(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        positions = db.get_positions_by_portfolio(portfolio_id)
        total_value = portfolio.cash_balance

        for position in positions:
            if self._price_provider is not None:
                live_price = self._price_provider(position.symbol)
                if live_price is not None:
                    position.current_value = round(
                        position.quantity * live_price, 2
                    )
            total_value += position.current_value

        return round(total_value, 2)

    def get_trade_history(self, portfolio_id: int) -> list[dict]:
        trades = db.get_trades_by_portfolio(portfolio_id)
        return [
            {
                "id": t.id,
                "symbol": t.symbol,
                "side": t.side,
                "quantity": t.quantity,
                "price": t.price,
                "timestamp": t.timestamp.isoformat() if t.timestamp else "",
                "status": t.status,
            }
            for t in sorted(trades, key=lambda x: x.timestamp or datetime.min)
        ]


manager = PortfolioManager()
