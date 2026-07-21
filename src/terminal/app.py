from __future__ import annotations

import asyncio
import logging
from typing import Optional

from textual.app import App
from textual.binding import Binding

from src.terminal.screens.market_overview import MarketOverview
from src.terminal.screens.stock_detail import StockDetail
from src.terminal.screens.portfolio_view import PortfolioView
from src.terminal.screens.news_feed_screen import NewsFeedScreen
from src.terminal.screens.research_screen import ResearchScreen

logger = logging.getLogger(__name__)

BLOOMBERG_CSS = """
Screen {
    background: #000000;
}

Screen > * {
    background: #000000;
}

Static {
    background: #000000;
    color: #00FF00;
}

Static:focus {
    background: #0a0a0a;
}

Input {
    background: #0a0a0a;
    color: #00FF00;
    border: solid #333333;
}

Input:focus {
    border: solid #FFB000;
}

Button {
    background: #0a0a0a;
    color: #00FF00;
    border: solid #333333;
}

Button:hover {
    border: solid #FFB000;
    color: #FFB000;
}

Button.success {
    background: #0a1a0a;
    color: #00FF00;
    border: solid #006600;
}

Button.error {
    background: #1a0a0a;
    color: #FF3333;
    border: solid #660000;
}

DataTable {
    background: #000000;
    color: #00FF00;
    border: solid #333333;
}

DataTable > .datatable--header {
    background: #0a0a0a;
    color: #FFB000;
}

DataTable > .datatable--cursor {
    background: #1a3a1a;
    color: #00FF00;
}

TabbedContent {
    background: #000000;
    border: solid #333333;
}

TabbedContent > .tabs {
    background: #0a0a0a;
    color: #33FF33;
}

TabbedContent > .tabs > .tab--active {
    color: #FFB000;
    text-style: bold;
}

TabPane {
    background: #000000;
}

* {
    scrollbar-color: #333333 #000000;
    scrollbar-size-vertical: 1;
}
"""


class BloombergTerminal(App):
    TITLE = "SECURE BLOOMBERG TERMINAL"
    CSS = BLOOMBERG_CSS

    BINDINGS = [
        Binding("1", "screen_market_overview", "Market Overview", priority=True),
        Binding("2", "screen_stock_detail", "Stock Detail", priority=True),
        Binding("3", "screen_portfolio", "Portfolio", priority=True),
        Binding("4", "screen_news", "News", priority=True),
        Binding("5", "screen_research", "Research", priority=True),
        Binding("q", "quit_app", "Quit", priority=True),
        Binding("slash", "search", "Search", priority=True),
        Binding("escape", "escape", "Back", priority=True),
    ]

    SCREENS = {
        "market_overview": MarketOverview,
        "stock_detail": StockDetail,
        "portfolio": PortfolioView,
        "news": NewsFeedScreen,
        "research": ResearchScreen,
    }

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._current_screen: Optional[str] = None

    def on_mount(self) -> None:
        self.push_screen("market_overview")
        self._current_screen = "market_overview"

    def action_screen_market_overview(self) -> None:
        self._switch_screen("market_overview")

    def action_screen_stock_detail(self) -> None:
        self._switch_screen("stock_detail")

    def action_screen_portfolio(self) -> None:
        self._switch_screen("portfolio")

    def action_screen_news(self) -> None:
        self._switch_screen("news")

    def action_screen_research(self) -> None:
        self._switch_screen("research")

    def action_quit_app(self) -> None:
        asyncio.create_task(self._shutdown())

    def action_search(self) -> None:
        from src.terminal.screens.market_overview import SearchInput

        def on_search(symbol: str) -> None:
            if symbol.strip():
                sd = StockDetail(symbol=symbol.strip().upper())
                self.push_screen(sd)

        self.push_screen(SearchInput(callback=on_search))

    def action_escape(self) -> None:
        if len(self.screen_stack) > 1:
            self.pop_screen()
        else:
            asyncio.create_task(self._shutdown())

    def _switch_screen(self, name: str) -> None:
        if name == self._current_screen:
            return

        screen_class = self.SCREENS.get(name)
        if screen_class:
            if name == "stock_detail":
                screen = screen_class()
            elif name == "portfolio":
                screen = screen_class(portfolio_id=1)
            else:
                screen = screen_class()

            self.switch_screen(screen)
            self._current_screen = name

    async def _shutdown(self) -> None:
        logger.info("Shutting down Bloomberg Terminal")
        self.exit()
