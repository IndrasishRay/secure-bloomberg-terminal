from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Callable, Optional

from src.storage.database import db
from src.storage.models import Trade

PriceProvider = Callable[[str], Optional[float]]


class RiskGuard:
    def __init__(self, price_provider: Optional[PriceProvider] = None) -> None:
        self._price_provider = price_provider
        self._daily_pnl: dict[int, float] = defaultdict(float)
        self._daily_loss_limit: float = 0.05
        self._max_position_concentration: float = 0.25
        self._min_order_value: float = 10.0
        self._price_deviation_threshold: float = 10.0
        self._trade_frequency_window: float = 60.0
        self._max_trades_per_window: int = 10
        self._circuit_breaker_threshold: int = 3
        self._consecutive_losses: dict[int, int] = defaultdict(int)
        self._circuit_broken: dict[int, bool] = defaultdict(bool)
        self._trade_timestamps: dict[int, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
        self._last_reset_date: Optional[str] = None

    def set_price_provider(self, provider: PriceProvider) -> None:
        self._price_provider = provider

    def check_trade(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        portfolio_id: int,
    ) -> tuple[bool, str]:
        self._check_daily_reset()

        portfolio = db.get_portfolio(portfolio_id)
        if portfolio is None:
            return False, f"Portfolio {portfolio_id} not found"

        side = side.lower()
        if side not in ("buy", "sell"):
            return False, f"Invalid side '{side}'; must be 'buy' or 'sell'"

        if quantity <= 0:
            return False, "Quantity must be positive"
        if price <= 0:
            return False, "Price must be positive"

        order_value = round(quantity * price, 2)

        if self._circuit_broken[portfolio_id]:
            return (
                False,
                "Circuit breaker is active. Trading halted for this portfolio.",
            )

        ok, msg = self._check_market_hours()
        if not ok:
            return False, msg

        ok, msg = self._check_min_order_size(order_value)
        if not ok:
            return False, msg

        ok, msg = self._check_trade_frequency(portfolio_id)
        if not ok:
            return False, msg

        ok, msg = self._check_price_sanity(symbol, price, portfolio_id)
        if not ok:
            return False, msg

        ok, msg = self._check_position_concentration(
            symbol, side, quantity, price, portfolio_id
        )
        if not ok:
            return False, msg

        ok, msg = self._check_daily_loss(portfolio_id, side)
        if not ok:
            return False, msg

        return True, "Trade approved"

    def _check_min_order_size(self, order_value: float) -> tuple[bool, str]:
        if order_value < self._min_order_value:
            return (
                False,
                f"Order value ${order_value:.2f} below minimum ${self._min_order_value:.2f}",
            )
        return True, ""

    def _check_trade_frequency(
        self, portfolio_id: int
    ) -> tuple[bool, str]:
        now = time.time()
        window_start = now - self._trade_frequency_window
        timestamps = self._trade_timestamps[portfolio_id]

        recent_trades = sum(
            1 for ts in timestamps if ts > window_start
        )

        if recent_trades >= self._max_trades_per_window:
            return (
                False,
                f"Trade frequency limit reached: "
                f"{recent_trades} trades in last 60s (max {self._max_trades_per_window})",
            )
        return True, ""

    def _check_price_sanity(
        self,
        symbol: str,
        price: float,
        portfolio_id: int,
    ) -> tuple[bool, str]:
        trades = db.get_trades_by_portfolio(portfolio_id)
        symbol_trades = [
            t
            for t in trades
            if t.symbol == symbol.upper()
        ]

        if len(symbol_trades) < 2:
            return True, ""

        recent_prices = [t.price for t in symbol_trades[-5:]]
        avg_price = sum(recent_prices) / len(recent_prices)

        if price > avg_price * self._price_deviation_threshold:
            return (
                False,
                f"Price ${price:.2f} is {price/avg_price:.1f}x above "
                f"recent average ${avg_price:.2f}",
            )
        if avg_price > 0 and price < avg_price / self._price_deviation_threshold:
            return (
                False,
                f"Price ${price:.2f} is {avg_price/price:.1f}x below "
                f"recent average ${avg_price:.2f}",
            )

        return True, ""

    def _check_position_concentration(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        portfolio_id: int,
    ) -> tuple[bool, str]:
        if side != "buy":
            return True, ""

        portfolio = db.get_portfolio(portfolio_id)
        positions = db.get_positions_by_portfolio(portfolio_id)
        current_position_value = sum(p.current_value for p in positions)
        total_value = portfolio.cash_balance + current_position_value

        existing = db.get_position_by_symbol(portfolio_id, symbol)
        existing_value = (
            existing.quantity * existing.avg_cost if existing else 0.0
        )
        new_value = existing_value + (quantity * price)

        concentration = new_value / total_value if total_value > 0 else 1.0

        if concentration > self._max_position_concentration:
            return (
                False,
                f"Position would be {concentration:.1%} of portfolio "
                f"(max {self._max_position_concentration:.0%})",
            )
        return True, ""

    def _check_daily_loss(
        self,
        portfolio_id: int,
        side: str,
    ) -> tuple[bool, str]:
        max_loss = self._daily_loss_limit
        current_loss_ratio = abs(self._daily_pnl[portfolio_id])

        portfolio = db.get_portfolio(portfolio_id)
        positions = db.get_positions_by_portfolio(portfolio_id)
        total_position_value = sum(p.current_value for p in positions)
        total_value = portfolio.cash_balance + total_position_value
        loss_threshold = total_value * max_loss if total_value > 0 else 0

        if current_loss_ratio >= loss_threshold > 0:
            return (
                False,
                f"Daily loss limit reached: ${current_loss_ratio:.2f} "
                f"(limit ${loss_threshold:.2f})",
            )
        return True, ""

    def _check_market_hours(self) -> tuple[bool, str]:
        now = datetime.now(timezone.utc)
        weekday = now.weekday()
        hour = now.hour
        minute = now.minute
        current_minutes = hour * 60 + minute

        if weekday >= 5:
            return False, "Markets are closed on weekends"

        open_time = 9 * 60 + 30
        close_time = 16 * 60

        if current_minutes < open_time or current_minutes >= close_time:
            return False, "Outside market hours (9:30 AM - 4:00 PM ET)"

        return True, ""

    _last_reset_date: Optional[str] = None

    def _check_daily_reset(self) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._last_reset_date is not None and self._last_reset_date != today:
            self.reset_daily_limits()
        self._last_reset_date = today

    def reset_daily_limits(self) -> None:
        self._daily_pnl.clear()
        self._trade_timestamps.clear()
        self._last_reset_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def record_trade_result(
        self,
        portfolio_id: int,
        side: str,
        quantity: float,
        price: float,
        success: bool,
    ) -> None:
        self._trade_timestamps[portfolio_id].append(time.time())

        if success:
            avg_price = self._estimate_entry_price(portfolio_id)
            trade_pnl = 0.0
            if side == "sell":
                trade_pnl = quantity * (price - avg_price)
            self._daily_pnl[portfolio_id] += trade_pnl

            if trade_pnl < 0:
                self._consecutive_losses[portfolio_id] += 1
            else:
                self._consecutive_losses[portfolio_id] = 0

            if (
                self._consecutive_losses[portfolio_id]
                >= self._circuit_breaker_threshold
            ):
                self._circuit_broken[portfolio_id] = True
                db.create_audit_log(
                    action="risk.circuit_breaker",
                    user="system",
                    details=(
                        f"portfolio_id={portfolio_id} "
                        f"reason={self._circuit_breaker_threshold} consecutive losses"
                    ),
                )

    def _estimate_entry_price(self, portfolio_id: int) -> float:
        positions = db.get_positions_by_portfolio(portfolio_id)
        if not positions:
            trades = db.get_trades_by_portfolio(portfolio_id)
            buy_trades = [t for t in trades if t.side == "buy"]
            if buy_trades:
                return buy_trades[-1].price
            return 0.0
        total_cost = sum(p.quantity * p.avg_cost for p in positions)
        total_qty = sum(p.quantity for p in positions)
        return total_cost / total_qty if total_qty > 0 else 0.0

    def reset_circuit_breaker(self, portfolio_id: int) -> None:
        self._circuit_broken[portfolio_id] = False
        self._consecutive_losses[portfolio_id] = 0
        db.create_audit_log(
            action="risk.circuit_reset",
            user="system",
            details=f"portfolio_id={portfolio_id} circuit breaker reset",
        )

    def get_risk_summary(self, portfolio_id: int) -> dict:
        portfolio = db.get_portfolio(portfolio_id)
        if portfolio is None:
            return {}

        positions = db.get_positions_by_portfolio(portfolio_id)
        total_position_value = sum(p.current_value for p in positions)
        total_value = portfolio.cash_balance + total_position_value

        return {
            "portfolio_id": portfolio_id,
            "portfolio_value": round(total_value, 2),
            "daily_pnl": round(self._daily_pnl[portfolio_id], 2),
            "daily_loss_limit": f"{self._daily_loss_limit:.0%}",
            "max_position_concentration": f"{self._max_position_concentration:.0%}",
            "circuit_breaker_active": self._circuit_broken[portfolio_id],
            "consecutive_losses": self._consecutive_losses[portfolio_id],
            "recent_trade_count": len(self._trade_timestamps[portfolio_id]),
        }


risk_guard = RiskGuard()
