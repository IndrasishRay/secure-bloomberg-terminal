from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Optional

from textual.widgets import Static
from textual.widget import Widget


class StockTicker(Widget):
    DEFAULT_CSS = """
    StockTicker {
        height: 1;
        background: black;
        color: #00FF00;
        overflow-x: auto;
        overflow-y: hidden;
    }
    """

    def __init__(
        self,
        symbols: Optional[list[str]] = None,
        data_provider: Optional[Callable[[str], dict[str, Any]]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._symbols = symbols or ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM"]
        self._data_provider = data_provider
        self._quotes: dict[str, dict[str, Any]] = {}
        self._timer_handle = None

    def compose(self):
        yield Static(id="ticker-content")

    def on_mount(self) -> None:
        self._update_quotes()
        self._timer_handle = self.set_interval(5.0, self._update_quotes)

    def _update_quotes(self) -> None:
        if self._data_provider is not None:
            for sym in self._symbols:
                try:
                    self._quotes[sym] = self._data_provider(sym)
                except Exception:
                    self._quotes[sym] = {"symbol": sym, "price": 0.0, "change": 0.0, "change_pct": 0.0}
        self._render_ticker()

    def _render_ticker(self) -> None:
        parts: list[str] = []
        for sym in self._symbols:
            q = self._quotes.get(sym, {})
            price = q.get("price", 0.0)
            change = q.get("change", 0.0)
            chg_pct = q.get("change_pct", 0.0)
            is_up = change >= 0
            arrow = "▲" if is_up else "▼"
            color = "green" if is_up else "red"
            parts.append(f"[{color}]{sym} ${price:.2f} {arrow}{abs(change):.2f} ({abs(chg_pct):.2f}%)[/]")

        text = "  |  ".join(parts)
        content = self.query_one("#ticker-content", Static)
        now = datetime.now().strftime("%H:%M:%S")
        full = f"  [bold]#Bloomberg[/]  |  {text}  |  [dim]{now}[/]  "
        content.update(full)
