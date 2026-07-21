from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static, TabbedContent, TabPane, Input

from src.market import market_data
from src.terminal.widgets.market_table import MarketTable
from src.terminal.widgets.sparkline import Sparkline
from src.terminal.widgets.status_bar import StatusBar
from src.terminal.widgets.stock_ticker import StockTicker


WATCH_SYMBOLS = ["SPY", "QQQ", "DIA", "IWM", "VIX"]
GAINER_SYMBOLS = ["NVDA", "META", "AMD", "AVGO", "PLTR"]
LOSER_SYMBOLS = ["INTC", "DIS", "BA", "PFE", "WBD"]


class MarketOverview(Screen):
    DEFAULT_CSS = """
    MarketOverview {
        background: #000000;
    }
    MarketOverview #title-bar {
        height: 3;
        background: #0a0a0a;
        content-align: center middle;
        text-style: bold;
        color: #FFB000;
    }
    MarketOverview #main-content {
        height: 1fr;
    }
    MarketOverview #market-ticker {
        height: 1;
    }
    MarketOverview TabPane {
        background: #000000;
    }
    MarketOverview TabbedContent {
        border: solid #333333;
        background: #000000;
    }
    MarketOverview TabbedContent > .tabs {
        background: #0a0a0a;
        color: #33FF33;
    }
    MarketOverview TabbedContent > .tabs > .tab--active {
        color: #FFB000;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("1", "goto_overview", "Overview"),
        Binding("s", "search_symbols", "Search"),
        Binding("/", "search_symbols", "Search"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield StockTicker(
            symbols=WATCH_SYMBOLS + GAINER_SYMBOLS + LOSER_SYMBOLS,
            data_provider=lambda s: market_data.get_quote(s),
            id="market-ticker",
        )
        yield Static(" SECURE BLOOMBERG TERMINAL  —  MARKET OVERVIEW", id="title-bar")
        with Widget(id="main-content"):
            yield MarketTable(id="market-table")
            with TabbedContent(initial="tab_gainers"):
                with TabPane("Gainers", id="tab_gainers"):
                    yield MarketTable(id="gainers-table")
                with TabPane("Losers", id="tab_losers"):
                    yield MarketTable(id="losers-table")
        yield StatusBar(id="status-bar")

    def on_mount(self) -> None:
        self._load_data()

    def _load_data(self) -> None:
        asyncio.create_task(self._async_load())

    async def _async_load(self) -> None:
        loop = asyncio.get_event_loop()
        watch_data: list[dict[str, Any]] = []
        gainer_data: list[dict[str, Any]] = []
        loser_data: list[dict[str, Any]] = []

        async def fetch_quote(sym: str) -> dict[str, Any]:
            return await loop.run_in_executor(None, market_data.get_quote, sym)

        for sym in WATCH_SYMBOLS:
            watch_data.append(await fetch_quote(sym))
        for sym in GAINER_SYMBOLS:
            gainer_data.append(await fetch_quote(sym))
        for sym in LOSER_SYMBOLS:
            loser_data.append(await fetch_quote(sym))

        gainer_data.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
        loser_data.sort(key=lambda x: x.get("change_pct", 0))

        self.query_one("#market-table", MarketTable).update_data(watch_data)
        self.query_one("#gainers-table", MarketTable).update_data(gainer_data)
        self.query_one("#losers-table", MarketTable).update_data(loser_data)

    def action_goto_overview(self) -> None:
        pass

    def action_search_symbols(self) -> None:
        def on_input(submitted: str) -> None:
            if submitted.strip():
                from src.terminal.screens.stock_detail import StockDetail
                self.app.push_screen(StockDetail(symbol=submitted.strip().upper()))
        self.app.push_screen(SearchInput(callback=on_input))


class SearchInput(Screen):
    DEFAULT_CSS = """
    SearchInput {
        background: #000000;
    }
    SearchInput Input {
        dock: top;
        margin: 1;
        background: #0a0a0a;
        color: #00FF00;
        border: solid #FFB000;
    }
    """

    def __init__(self, callback: callable, **kwargs) -> None:
        super().__init__(**kwargs)
        self._callback = callback

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Enter symbol to search...")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._callback(event.value)
        self.app.pop_screen()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
            event.prevent_default()
