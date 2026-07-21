from __future__ import annotations

import asyncio
from typing import Any, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static, TabbedContent, TabPane

from src.news import NewsManager
from src.market import market_data
from src.terminal.widgets.news_panel import NewsPanel
from src.terminal.widgets.status_bar import StatusBar
from src.terminal.widgets.stock_ticker import StockTicker


CATEGORIES = {
    "All": None,
    "Stocks": "general",
    "Crypto": "crypto",
    "Economy": "general",
    "Research": None,
}


class NewsFeedScreen(Screen):
    DEFAULT_CSS = """
    NewsFeedScreen {
        background: #000000;
    }
    NewsFeedScreen #title-bar {
        height: 3;
        background: #0a0a0a;
        content-align: center middle;
        text-style: bold;
        color: #FFB000;
    }
    NewsFeedScreen #main-layout {
        height: 1fr;
    }
    NewsFeedScreen #headlines-panel {
        width: 60%;
        height: 100%;
        border: solid #333333;
        background: #000000;
    }
    NewsFeedScreen #detail-panel {
        width: 40%;
        height: 100%;
        border: solid #333333;
        background: #000000;
    }
    NewsFeedScreen #category-bar {
        height: 3;
        background: #0a0a0a;
    }
    NewsFeedScreen CategoryLabel {
        padding: 0 2;
        color: #33FF33;
    }
    NewsFeedScreen CategoryLabel.active {
        color: #FFB000;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("4", "goto_news", "News"),
        Binding("up", "prev_article", "Prev"),
        Binding("down", "next_article", "Next"),
        Binding("enter", "view_article", "View"),
        Binding("left", "prev_category", "Cat -"),
        Binding("right", "next_category", "Cat +"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._news_mgr = NewsManager()
        self._articles: list[dict[str, Any]] = []
        self._cat_index: int = 0
        self._cat_keys = list(CATEGORIES.keys())

    def compose(self) -> ComposeResult:
        yield StockTicker(
            symbols=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM"],
            data_provider=lambda s: market_data.get_quote(s),
        )
        yield Static(" SECURE BLOOMBERG TERMINAL  —  NEWS", id="title-bar")
        yield Static(id="category-bar")
        with Widget(id="main-layout"):
            with Widget(id="headlines-panel"):
                yield NewsPanel(id="news-panel")
            with Widget(id="detail-panel"):
                yield Static(id="article-detail")
        yield StatusBar()

    def on_mount(self) -> None:
        self._load_category()

    def _load_category(self) -> None:
        asyncio.create_task(self._async_load())

    async def _async_load(self) -> None:
        loop = asyncio.get_event_loop()
        cat = self._cat_keys[self._cat_index]
        self._update_category_bar()

        try:
            if cat == "All":
                articles = await loop.run_in_executor(None, self._news_mgr.get_headlines, 30)
            elif cat == "Research":
                from src.research import ResearchManager
                rm = ResearchManager()
                articles = await loop.run_in_executor(None, rm.get_recent_finance_papers, 15)
            else:
                cat_key = CATEGORIES[cat]
                articles = await loop.run_in_executor(
                    None, self._news_mgr.search_news, cat_key
                ) if cat_key else []
                if not articles:
                    articles = await loop.run_in_executor(None, self._news_mgr.get_headlines, 30)

            self._articles = articles
            self.query_one(NewsPanel).update_articles(articles)

            if articles:
                self._show_detail(articles[0])
        except Exception:
            self._articles = []

    def _update_category_bar(self) -> None:
        parts = []
        for i, name in enumerate(self._cat_keys):
            if i == self._cat_index:
                parts.append(f"[bold #FFB000] [{name}] [/]")
            else:
                parts.append(f"[#33FF33]  {name}  [/]")
        bar = " |".join(parts)
        self.query_one("#category-bar", Static).update(f"  CATEGORIES: {bar}")

    def _show_detail(self, article: dict[str, Any]) -> None:
        title = article.get("title", "Untitled")
        source = article.get("source", "Unknown")
        dt = article.get("datetime", "")
        summary = article.get("summary", article.get("abstract", "No content available."))
        url = article.get("url", "")
        symbols = article.get("related_symbols", [])

        text = (
            f"\n[bold #FFB000]{title}[/]\n\n"
            f"[#33FF33]Source:[/] {source}\n"
            f"[#33FF33]Date:[/]   {dt}\n"
        )
        if symbols:
            sym_str = ", ".join(s.upper() for s in symbols if s)
            text += f"[#33FF33]Related:[/] [#00FF00]{sym_str}[/]\n"
        text += f"\n[#00FF00]{summary[:800]}[/]\n"
        if url:
            text += f"\n[dim #555555]Source: {url}[/]"

        self.query_one("#article-detail", Static).update(text)

    def action_goto_news(self) -> None:
        pass

    def action_next_article(self) -> None:
        panel = self.query_one(NewsPanel)
        panel.select_next()
        art = panel._headlines.get_selected()
        if art:
            self._show_detail(art)

    def action_prev_article(self) -> None:
        panel = self.query_one(NewsPanel)
        panel.select_prev()
        art = panel._headlines.get_selected()
        if art:
            self._show_detail(art)

    def action_view_article(self) -> None:
        panel = self.query_one(NewsPanel)
        art = panel._headlines.get_selected()
        if art:
            self._show_detail(art)

    def action_next_category(self) -> None:
        self._cat_index = (self._cat_index + 1) % len(self._cat_keys)
        self._load_category()

    def action_prev_category(self) -> None:
        self._cat_index = (self._cat_index - 1) % len(self._cat_keys)
        self._load_category()
