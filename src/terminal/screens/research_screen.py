from __future__ import annotations

import asyncio
from typing import Any, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static, Input

from src.market import market_data
from src.research import ResearchManager
from src.terminal.widgets.status_bar import StatusBar
from src.terminal.widgets.stock_ticker import StockTicker


PAGE_SIZE = 10


class ResearchScreen(Screen):
    DEFAULT_CSS = """
    ResearchScreen {
        background: #000000;
    }
    ResearchScreen #title-bar {
        height: 3;
        background: #0a0a0a;
        content-align: center middle;
        text-style: bold;
        color: #FFB000;
    }
    ResearchScreen #search-box {
        dock: top;
        margin: 1 2;
        background: #0a0a0a;
        color: #00FF00;
        border: solid #FFB000;
    }
    ResearchScreen #main-layout {
        height: 1fr;
    }
    ResearchScreen #paper-list {
        width: 55%;
        height: 100%;
        border: solid #333333;
        background: #000000;
        overflow-y: auto;
    }
    ResearchScreen #paper-detail {
        width: 45%;
        height: 100%;
        border: solid #333333;
        background: #000000;
        padding: 1;
    }
    ResearchScreen #pagination {
        height: 3;
        background: #0a0a0a;
    }
    """

    BINDINGS = [
        Binding("5", "goto_research", "Research"),
        Binding("up", "prev_paper", "Prev"),
        Binding("down", "next_paper", "Next"),
        Binding("enter", "view_paper", "View"),
        Binding("n", "next_page", "PgDn"),
        Binding("p", "prev_page", "PgUp"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._research = ResearchManager()
        self._papers: list[dict[str, Any]] = []
        self._all_papers: list[dict[str, Any]] = []
        self._selected: int = 0
        self._page: int = 0
        self._query: str = ""

    def compose(self) -> ComposeResult:
        yield StockTicker(
            symbols=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM"],
            data_provider=lambda s: market_data.get_quote(s),
        )
        yield Static(" SECURE BLOOMBERG TERMINAL  —  RESEARCH", id="title-bar")
        yield Input(
            placeholder="Search papers (e.g. 'reinforcement learning finance')...",
            id="search-box",
        )
        with Widget(id="main-layout"):
            yield Static(id="paper-list")
            yield Static(id="paper-detail")
        yield Static(id="pagination")
        yield StatusBar()

    def on_mount(self) -> None:
        self._load_papers()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._query = event.value.strip()
        self._page = 0
        self._selected = 0
        self._load_papers()

    def _load_papers(self) -> None:
        asyncio.create_task(self._async_load())

    async def _async_load(self) -> None:
        loop = asyncio.get_event_loop()
        try:
            if self._query:
                papers = await loop.run_in_executor(
                    None, self._research.search_papers, self._query, 50
                )
            else:
                papers = await loop.run_in_executor(
                    None, self._research.get_recent_finance_papers, 50
                )
            self._all_papers = papers
            self._page = 0
            self._selected = 0
            self._paginate()
        except Exception as e:
            self.query_one("#paper-list", Static).update(f"[red]Error: {e}[/]")

    def _paginate(self) -> None:
        start = self._page * PAGE_SIZE
        end = start + PAGE_SIZE
        self._papers = self._all_papers[start:end]
        self._render_list()
        if self._papers:
            self._show_detail(self._papers[0])
        self._update_pagination()

    def _render_list(self) -> None:
        if not self._papers:
            self.query_one("#paper-list", Static).update("[dim]  No papers found[/]")
            return
        lines = []
        for i, p in enumerate(self._papers):
            title = p.get("title", "Untitled")[:90]
            published = str(p.get("published", ""))[:10]
            authors = p.get("authors", [])
            author_str = (authors[0][:25] + "...") if len(authors) > 1 else (authors[0][:25] if authors else "Unknown")
            indicator = "▸" if i == self._selected else " "
            style = "bold #FFB000" if i == self._selected else "#00FF00"
            lines.append(
                f"  [{style}]{indicator} [{style}]{title}[/]\n"
                f"    [#33FF33]{author_str}[/]  [dim]{published}[/]"
            )
        self.query_one("#paper-list", Static).update("\n\n".join(lines))

    def _show_detail(self, paper: dict[str, Any]) -> None:
        title = paper.get("title", "Untitled")
        authors = paper.get("authors", [])
        abstract = paper.get("abstract", "No abstract available.")
        published = paper.get("published", "")
        url = paper.get("url", "")
        categories = paper.get("categories", [])

        cat_str = ", ".join(categories[:5]) if categories else ""
        author_str = ", ".join(authors[:5])
        if len(authors) > 5:
            author_str += f" et al."

        text = (
            f"[bold #FFB000]{title}[/]\n\n"
            f"[#33FF33]Authors:[/] [#00FF00]{author_str}[/]\n"
            f"[#33FF33]Published:[/] {published}\n"
        )
        if cat_str:
            text += f"[#33FF33]Categories:[/] [#00FF00]{cat_str}[/]\n"
        text += f"\n[#00FF00]{abstract[:600]}[/]"
        if len(abstract) > 600:
            text += "\n[dim]...[truncated][/]"
        if url:
            text += f"\n\n[dim #555555]{url}[/]"

        self.query_one("#paper-detail", Static).update(text)

    def _update_pagination(self) -> None:
        total = len(self._all_papers)
        current = self._page + 1
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE if total else 1
        self.query_one("#pagination", Static).update(
            f"  [#33FF33]Page {current}/{total_pages}[/]  "
            f"[dim]({total} results)[/]  "
            f"[dim]  n:next  p:prev[/]"
        )

    def action_goto_research(self) -> None:
        pass

    def action_next_paper(self) -> None:
        if self._papers and self._selected < len(self._papers) - 1:
            self._selected += 1
            self._render_list()
            self._show_detail(self._papers[self._selected])

    def action_prev_paper(self) -> None:
        if self._selected > 0:
            self._selected -= 1
            self._render_list()
            self._show_detail(self._papers[self._selected])

    def action_view_paper(self) -> None:
        if self._papers and self._selected < len(self._papers):
            self._show_detail(self._papers[self._selected])

    def action_next_page(self) -> None:
        if (self._page + 1) * PAGE_SIZE < len(self._all_papers):
            self._page += 1
            self._selected = 0
            self._paginate()

    def action_prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._selected = 0
            self._paginate()
