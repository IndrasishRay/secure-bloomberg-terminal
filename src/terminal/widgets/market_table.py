from __future__ import annotations

from typing import Any, Callable, Optional

from textual.widgets import DataTable
from textual.widget import Widget


class MarketTable(Widget):
    DEFAULT_CSS = """
    MarketTable {
        height: 100%;
        background: black;
    }
    MarketTable DataTable {
        height: 100%;
        background: black;
        color: #00FF00;
    }
    MarketTable DataTable > .datatable--header {
        background: #1a1a1a;
        color: #FFB000;
        text-style: bold;
    }
    MarketTable DataTable > .datatable--cursor {
        background: #0a3a0a;
        color: #00FF00;
    }
    """

    def __init__(
        self,
        watchlist: Optional[dict[str, list[str]]] = None,
        data_provider: Optional[Callable[[str], dict[str, Any]]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._watchlist = watchlist or {
            "Tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"],
            "Finance": ["JPM", "GS", "BAC", "V", "MA"],
            "Crypto": ["BTC-USD", "ETH-USD", "SOL-USD"],
        }
        self._current_group = "Tech"
        self._data_provider = data_provider
        self._data: dict[str, dict[str, Any]] = {}
        self._timer_handle = None

    def compose(self):
        yield DataTable(id="market-table")

    def on_mount(self) -> None:
        table = self.query_one("#market-table", DataTable)
        table.add_columns("Symbol", "Last", "Change", "Change%", "Volume", "Market Cap")
        self._refresh()
        self._timer_handle = self.set_interval(10.0, self._refresh)

    def set_group(self, group: str) -> None:
        if group in self._watchlist:
            self._current_group = group
            self._refresh()

    def _refresh(self) -> None:
        symbols = self._watchlist.get(self._current_group, [])
        if self._data_provider is not None:
            for sym in symbols:
                try:
                    self._data[sym] = self._data_provider(sym)
                except Exception:
                    pass
        self._render_table()

    def _format_change(self, change: float, pct: float) -> tuple[str, str]:
        is_up = change >= 0
        arrow = "▲" if is_up else "▼"
        color = "green" if is_up else "red"
        chg_str = f"[{color}]{arrow} ${abs(change):.2f}[/]"
        pct_str = f"[{color}]{arrow}{abs(pct):.2f}%[/]"
        return chg_str, pct_str

    def _format_volume(self, vol: int) -> str:
        if vol >= 1_000_000:
            return f"{vol / 1_000_000:.1f}M"
        if vol >= 1_000:
            return f"{vol / 1_000:.1f}K"
        return str(vol)

    def _format_market_cap(self, cap: Optional[float]) -> str:
        if cap is None:
            return "N/A"
        if cap >= 1_000_000_000_000:
            return f"${cap / 1_000_000_000_000:.2f}T"
        if cap >= 1_000_000_000:
            return f"${cap / 1_000_000_000:.2f}B"
        if cap >= 1_000_000:
            return f"${cap / 1_000_000:.2f}M"
        return f"${cap:,.0f}"

    def _render_table(self) -> None:
        table = self.query_one("#market-table", DataTable)
        table.clear()

        for sym in self._watchlist.get(self._current_group, []):
            q = self._data.get(sym, {})
            price = q.get("price", 0.0)
            change = q.get("change", 0.0)
            chg_pct = q.get("change_pct", 0.0)
            volume = q.get("volume", 0)
            mcap = q.get("market_cap")

            chg_str, pct_str = self._format_change(change, chg_pct)
            table.add_row(
                f"[bold #FFB000]{sym}[/]",
                f"${price:.2f}",
                chg_str,
                pct_str,
                self._format_volume(volume),
                self._format_market_cap(mcap),
            )
