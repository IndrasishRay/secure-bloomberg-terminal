from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Callable, Optional

from textual.containers import ScrollableContainer
from textual.widgets import ListView, ListItem, Label, Input
from textual.widget import Widget
from textual.screen import Screen


class NewsDetail(Screen):
    DEFAULT_CSS = """
    NewsDetail {
        background: black;
    }
    NewsDetail #detail-container {
        padding: 1 2;
        height: 100%;
    }
    NewsDetail #detail-title {
        color: #FFB000;
        text-style: bold;
        margin-bottom: 1;
    }
    NewsDetail #detail-source {
        color: #00FF00;
        margin-bottom: 1;
    }
    NewsDetail #detail-summary {
        color: #c0c0c0;
        margin-bottom: 1;
    }
    NewsDetail #detail-time {
        color: #808080;
    }
    NewsDetail #detail-back {
        background: #1a1a1a;
        color: #FFB000;
        margin-top: 1;
        padding: 0 2;
    }
    """

    def __init__(self, article: dict[str, Any], **kwargs) -> None:
        super().__init__(**kwargs)
        self._article = article

    def compose(self):
        with ScrollableContainer(id="detail-container"):
            yield Label(self._article.get("title", ""), id="detail-title")
            yield Label(f"[SOURCE: {self._article.get('source', 'Unknown')}]", id="detail-source")
            yield Label(self._article.get("summary", "No summary available."), id="detail-summary")
            yield Label(f"Published: {self._article.get('datetime', 'Unknown')}", id="detail-time")
            yield Label("Press ESC or click to go back", id="detail-back")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()

    def on_click(self) -> None:
        self.app.pop_screen()


class NewsPanel(Widget):
    DEFAULT_CSS = """
    NewsPanel {
        height: 100%;
        background: black;
    }
    NewsPanel #news-header {
        background: #1a1a1a;
        color: #FFB000;
        text-style: bold;
        padding: 0 1;
        height: 1;
    }
    NewsPanel #news-filter {
        background: black;
        color: #00FF00;
        border: none;
        height: 1;
        margin: 0 1;
    }
    NewsPanel #news-list {
        height: 100%;
        background: black;
    }
    NewsPanel ListView {
        background: black;
    }
    NewsPanel ListItem {
        background: black;
        padding: 0 1;
    }
    NewsPanel ListItem:hover {
        background: #0a3a0a;
    }
    NewsPanel ListItem > Label {
        color: #c0c0c0;
    }
    """

    def __init__(
        self,
        news_provider: Optional[Callable[[], list[dict[str, Any]]]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._news_provider = news_provider
        self._articles: list[dict[str, Any]] = []
        self._filter_query: str = ""
        self._timer_handle = None

    def compose(self):
        yield Label(" HEADLINES ", id="news-header")
        yield Input(placeholder="Filter by symbol/query...", id="news-filter")
        yield ListView(id="news-list")

    def on_mount(self) -> None:
        self._fetch_news()
        self._timer_handle = self.set_interval(60.0, self._fetch_news)

    def _fetch_news(self) -> None:
        if self._news_provider is not None:
            try:
                self._articles = self._news_provider()
            except Exception:
                self._articles = self._articles or []
        self._render_news()

    def _time_ago(self, dt_val: Any) -> str:
        if not dt_val:
            return "unknown"
        try:
            ts = int(dt_val)
            dt = datetime.fromtimestamp(ts)
        except (ValueError, TypeError, OSError):
            return str(dt_val)
        delta = time.time() - ts
        if delta < 60:
            return "just now"
        if delta < 3600:
            return f"{int(delta // 60)}m ago"
        if delta < 86400:
            return f"{int(delta // 3600)}h ago"
        return f"{int(delta // 86400)}d ago"

    def on_input_changed(self, event: Input.Changed) -> None:
        self._filter_query = event.value.strip().upper()
        self._render_news()

    def _render_news(self) -> None:
        list_view = self.query_one("#news-list", ListView)
        list_view.clear()

        items = self._articles
        if self._filter_query:
            q = self._filter_query
            items = [
                a
                for a in items
                if q in a.get("title", "").upper()
                or q in " ".join(a.get("related_symbols", [])).upper()
            ]

        for article in items:
            title = article.get("title", "Untitled")
            source = article.get("source", "Unknown")
            dt_val = article.get("datetime")
            ago = self._time_ago(dt_val)
            text = f"[dim][{source}][/] {title} [dim]({ago})[/]"
            item = ListItem(Label(text))
            item._article = article
            list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        article = getattr(item, "_article", None)
        if article:
            self.app.push_screen(NewsDetail(article))
