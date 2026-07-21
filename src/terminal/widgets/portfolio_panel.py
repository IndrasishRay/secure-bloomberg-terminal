from __future__ import annotations

from typing import Any, Callable, Optional

from textual.containers import ScrollableContainer
from textual.widgets import DataTable, Label
from textual.widget import Widget


class PortfolioPanel(Widget):
    DEFAULT_CSS = """
    PortfolioPanel {
        height: 100%;
        background: black;
    }
    PortfolioPanel #portfolio-header {
        background: #1a1a1a;
        color: #FFB000;
        text-style: bold;
        padding: 0 1;
        height: 3;
    }
    PortfolioPanel #portfolio-summary {
        color: #00FF00;
        padding: 0 1;
    }
    PortfolioPanel #portfolio-table {
        height: 100%;
        background: black;
    }
    PortfolioPanel DataTable {
        height: 100%;
        background: black;
        color: #c0c0c0;
    }
    PortfolioPanel DataTable > .datatable--header {
        background: #1a1a1a;
        color: #FFB000;
        text-style: bold;
    }
    PortfolioPanel DataTable > .datatable--cursor {
        background: #0a3a0a;
        color: #00FF00;
    }
    """

    def __init__(
        self,
        positions_provider: Optional[Callable[[], list[dict[str, Any]]]] = None,
        summary_provider: Optional[Callable[[], dict[str, Any]]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._positions_provider = positions_provider
        self._summary_provider = summary_provider
        self._positions: list[dict[str, Any]] = []
        self._summary: dict[str, Any] = {}
        self._timer_handle = None

    def compose(self):
        yield Label(id="portfolio-header")
        yield Label(id="portfolio-summary")
        yield DataTable(id="portfolio-table")

    def on_mount(self) -> None:
        table = self.query_one("#portfolio-table", DataTable)
        table.add_columns("Symbol", "Qty", "Avg Cost", "Current", "Value", "P&L", "P&L%")
        self._refresh()
        self._timer_handle = self.set_interval(15.0, self._refresh)

    def _refresh(self) -> None:
        if self._positions_provider is not None:
            try:
                self._positions = self._positions_provider()
            except Exception:
                pass
        if self._summary_provider is not None:
            try:
                self._summary = self._summary_provider()
            except Exception:
                pass
        self._render()

    def _render(self) -> None:
        header = self.query_one("#portfolio-header", Label)
        total_value = self._summary.get("total_value", 0.0)
        cash = self._summary.get("cash", 0.0)
        total_pnl = self._summary.get("pnl", 0.0)
        is_up = total_pnl >= 0
        arrow = "▲" if is_up else "▼"
        pnl_color = "green" if is_up else "red"
        header_text = (
            f" PORTFOLIO  "
            f"[#00FF00]Total: ${total_value:,.2f}[/]  "
            f"[dim]Cash:[/] [#FFB000]${cash:,.2f}[/]  "
            f"[{pnl_color}]P&L: {arrow} ${abs(total_pnl):,.2f}[/]"
        )
        header.update(header_text)

        summary = self.query_one("#portfolio-summary", Label)
        pos_count = len(self._positions)
        summary.update(f"  Positions: {pos_count}  |  Refresh: 15s ")

        table = self.query_one("#portfolio-table", DataTable)
        table.clear()

        for pos in self._positions:
            symbol = pos.get("symbol", "")
            qty = pos.get("quantity", 0)
            avg_cost = pos.get("avg_cost", 0.0)
            current_price = pos.get("current_price", 0.0)
            value = qty * current_price
            pnl = value - (qty * avg_cost)
            pnl_pct = (pnl / (qty * avg_cost)) * 100 if qty * avg_cost else 0.0

            is_pnl_up = pnl >= 0
            arrow = "▲" if is_pnl_up else "▼"
            pnl_color = "green" if is_pnl_up else "red"

            table.add_row(
                f"[bold #FFB000]{symbol}[/]",
                f"{qty:.4f}",
                f"${avg_cost:.2f}",
                f"${current_price:.2f}",
                f"${value:.2f}",
                f"[{pnl_color}]{arrow} ${abs(pnl):.2f}[/]",
                f"[{pnl_color}]{arrow}{abs(pnl_pct):.2f}%[/]",
            )
