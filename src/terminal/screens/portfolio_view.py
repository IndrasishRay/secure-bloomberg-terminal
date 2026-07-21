from __future__ import annotations

import asyncio
from typing import Any, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from textual.widgets import Static, Button, Input, Label

from src.market import market_data
from src.portfolio import TradingManager
from src.terminal.widgets.portfolio_panel import PortfolioPanel
from src.terminal.widgets.status_bar import StatusBar
from src.terminal.widgets.stock_ticker import StockTicker


COMMON_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM"]


class PortfolioView(Screen):
    DEFAULT_CSS = """
    PortfolioView {
        background: #000000;
    }
    PortfolioView #title-bar {
        height: 3;
        background: #0a0a0a;
        content-align: center middle;
        text-style: bold;
        color: #FFB000;
    }
    PortfolioView #summary-panel {
        height: 6;
        border: solid #333333;
        background: #000000;
    }
    PortfolioView #positions-panel {
        height: 1fr;
        border: solid #333333;
        background: #000000;
    }
    PortfolioView #trade-history {
        height: 8;
        border: solid #333333;
        background: #000000;
        overflow-y: auto;
    }
    PortfolioView #risk-panel {
        height: 5;
        border: solid #333333;
        background: #000000;
    }
    PortfolioView #section-header {
        background: #0a0a0a;
        color: #FFB000;
        text-style: bold;
    }
    PortfolioView Button {
        margin: 0 1;
        background: #0a0a0a;
        color: #00FF00;
        border: solid #333333;
    }
    PortfolioView Button:hover {
        border: solid #FFB000;
    }
    PortfolioView #action-buttons {
        height: 3;
        align: center middle;
    }
    """

    BINDINGS = [
        Binding("3", "goto_portfolio", "Portfolio"),
        Binding("b", "buy", "Buy"),
        Binding("s", "sell", "Sell"),
        Binding("h", "history", "History"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, portfolio_id: int = 1, **kwargs) -> None:
        super().__init__(**kwargs)
        self._portfolio_id = portfolio_id
        self._trading = TradingManager()

    def compose(self) -> ComposeResult:
        yield StockTicker(
            symbols=COMMON_SYMBOLS,
            data_provider=lambda s: market_data.get_quote(s),
        )
        yield Static(" SECURE BLOOMBERG TERMINAL  —  PORTFOLIO", id="title-bar")
        yield Static(id="summary-panel")
        yield Static(" [bold]Positions[/]", id="section-header")
        yield PortfolioPanel(id="positions-panel")
        yield Static(" [bold]Trade History[/]", id="section-header")
        yield Static(id="trade-history")
        yield Static(id="risk-panel")
        with Widget(id="action-buttons"):
            yield Button("Buy", id="buy-btn", variant="success")
            yield Button("Sell", id="sell-btn", variant="error")
            yield Button("History", id="hist-btn")
        yield StatusBar()

    def on_mount(self) -> None:
        self._ensure_portfolio()
        self._refresh()

    def _ensure_portfolio(self) -> None:
        try:
            self._trading.get_portfolio(self._portfolio_id)
        except (ValueError, Exception):
            self._trading.create_portfolio("Default Portfolio", 100000.0)

    def _refresh(self) -> None:
        asyncio.create_task(self._async_refresh())

    async def _async_refresh(self) -> None:
        loop = asyncio.get_event_loop()

        try:
            portfolio = await loop.run_in_executor(
                None, self._trading.get_portfolio, self._portfolio_id
            )
            positions = await loop.run_in_executor(
                None, self._trading.get_positions, self._portfolio_id
            )
            risk = await loop.run_in_executor(
                None, self._trading.get_risk_summary, self._portfolio_id
            )
            history = await loop.run_in_executor(
                None, self._trading.get_trade_history, self._portfolio_id
            )

            self._update_summary(portfolio)
            self.query_one(PortfolioPanel).update_data(positions)
            self._update_history(history)
            self._update_risk(risk)
        except Exception as e:
            summary = self.query_one("#summary-panel", Static)
            summary.update(f"[red]Error loading portfolio: {e}[/]")

    def _update_summary(self, portfolio: dict[str, Any]) -> None:
        text = (
            f"  [bold #FFB000]Portfolio: {portfolio.get('name', 'N/A')}[/]\n"
            f"  [#33FF33]Total Value:[/]  [#00FF00]${portfolio.get('total_value', 0):,.2f}[/]     "
            f"[#33FF33]Cash:[/]  [#00FF00]${portfolio.get('cash', 0):,.2f}[/]\n"
            f"  [#33FF33]P&L:[/]  "
        )
        pnl = portfolio.get("pnl", 0)
        if pnl >= 0:
            text += f"[green]+${pnl:,.2f}[/]"
        else:
            text += f"[red]-${abs(pnl):,.2f}[/]"
        text += (
            f"     [#33FF33]Position Value:[/]  "
            f"[#00FF00]${portfolio.get('total_position_value', 0):,.2f}[/]"
        )
        self.query_one("#summary-panel", Static).update(text)

    def _update_history(self, trades: list[dict[str, Any]]) -> None:
        if not trades:
            self.query_one("#trade-history", Static).update("[dim]  No trades yet[/]")
            return
        lines = []
        for t in trades[:10]:
            side = t.get("side", "").upper()
            color = "green" if side == "BUY" else "red"
            qty = t.get("quantity", 0)
            price = t.get("price", 0)
            sym = t.get("symbol", "")
            ts = t.get("timestamp", "")[:19]
            lines.append(
                f"  [{color}]{side}[/]  {qty:.2f}  {sym}  @ ${price:.2f}  [dim]{ts}[/]"
            )
        self.query_one("#trade-history", Static).update("\n".join(lines))

    def _update_risk(self, risk: dict[str, Any]) -> None:
        if not risk:
            return
        cb = risk.get("circuit_breaker_active", False)
        cb_str = "[red]ACTIVE[/]" if cb else "[green]OK[/]"
        text = (
            f"  [bold #FFB000]Risk Metrics[/]\n"
            f"  [#33FF33]Daily P&L:[/]  "
        )
        dpnl = risk.get("daily_pnl", 0)
        if dpnl >= 0:
            text += f"[green]+${dpnl:.2f}[/]"
        else:
            text += f"[red]-${abs(dpnl):.2f}[/]"
        text += (
            f"     [#33FF33]Circuit Breaker:[/]  {cb_str}"
            f"     [#33FF33]Consecutive Losses:[/]  {risk.get('consecutive_losses', 0)}"
        )
        self.query_one("#risk-panel", Static).update(text)

    def action_goto_portfolio(self) -> None:
        pass

    def action_buy(self) -> None:
        self.app.push_screen(PortfolioTradeDialog(self._portfolio_id, "buy", self._trading))

    def action_sell(self) -> None:
        self.app.push_screen(PortfolioTradeDialog(self._portfolio_id, "sell", self._trading))

    def action_history(self) -> None:
        asyncio.create_task(self._async_refresh())


class PortfolioTradeDialog(ModalScreen):
    DEFAULT_CSS = """
    PortfolioTradeDialog {
        align: center middle;
        background: #000000 60%;
    }
    PortfolioTradeDialog #dialog {
        width: 50;
        height: auto;
        border: solid #FFB000;
        background: #0a0a0a;
        padding: 1;
    }
    PortfolioTradeDialog Input {
        background: #000000;
        color: #00FF00;
        border: solid #333333;
    }
    PortfolioTradeDialog Label {
        color: #33FF33;
    }
    PortfolioTradeDialog Button {
        margin: 1;
    }
    PortfolioTradeDialog #result {
        color: #00FF00;
    }
    """

    def __init__(self, portfolio_id: int, side: str, trading: TradingManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self._portfolio_id = portfolio_id
        self._side = side
        self._trading = trading
        self._result_shown = False

    def compose(self) -> ComposeResult:
        with Widget(id="dialog"):
            yield Label(f" [bold #FFB000]{self._side.upper()}[/]")
            yield Label(" Symbol:")
            yield Input(placeholder="e.g. AAPL", id="sym-input")
            yield Label(" Quantity:")
            yield Input(placeholder="Number of shares", id="qty-input")
            yield Label(" Price:")
            yield Input(placeholder="Limit price", id="price-input")
            yield Static(id="result")
            with Widget():
                yield Button("Submit", id="submit-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if self._result_shown:
            self.app.pop_screen()
            return
        if event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "submit-btn":
            sym = self.query_one("#sym-input", Input).value.strip().upper()
            qty_inp = self.query_one("#qty-input", Input).value
            price_inp = self.query_one("#price-input", Input).value
            try:
                qty = float(qty_inp)
                price = float(price_inp)
                result = self._trading.execute_trade(sym, self._side, qty, price, self._portfolio_id)
                res_widget = self.query_one("#result", Static)
                if result.get("success"):
                    res_widget.update(f"[green] {result['message']}[/]")
                else:
                    res_widget.update(f"[red] {result['message']}[/]")
                self._result_shown = True
                event.button.label = "Close"
            except ValueError:
                self.query_one("#result", Static).update("[red] Invalid quantity or price[/]")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
            event.prevent_default()
