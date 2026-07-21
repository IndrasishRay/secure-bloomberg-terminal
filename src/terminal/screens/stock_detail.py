from __future__ import annotations

import asyncio
from typing import Any, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from textual.widgets import Static, Input, Button, Label

from src.market import market_data
from src.terminal.widgets.sparkline import Sparkline
from src.terminal.widgets.status_bar import StatusBar
from src.terminal.widgets.stock_ticker import StockTicker


COMMON_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM"]


class StockDetail(Screen):
    DEFAULT_CSS = """
    StockDetail {
        background: #000000;
    }
    StockDetail #title-bar {
        height: 3;
        background: #0a0a0a;
        content-align: center middle;
        text-style: bold;
        color: #FFB000;
    }
    StockDetail #symbol-input {
        dock: top;
        margin: 1 2;
        background: #0a0a0a;
        color: #00FF00;
        border: solid #FFB000;
    }
    StockDetail #quote-display {
        height: 5;
        background: #000000;
        content-align: center middle;
    }
    StockDetail #quote-price {
        text-style: bold;
        color: #00FF00;
    }
    StockDetail #quote-change {
        color: #33FF33;
    }
    StockDetail #stats-grid {
        height: 7;
        background: #000000;
        border: solid #333333;
    }
    StockDetail #news-section {
        height: 1fr;
        border: solid #333333;
        background: #000000;
    }
    StockDetail #news-title {
        background: #0a0a0a;
        color: #FFB000;
        text-style: bold;
    }
    StockDetail #news-list {
        height: 1fr;
        overflow-y: auto;
    }
    StockDetail Button {
        margin: 0 1;
        background: #0a0a0a;
        color: #00FF00;
        border: solid #333333;
    }
    StockDetail Button:hover {
        border: solid #FFB000;
    }
    StockDetail #action-buttons {
        dock: bottom;
        height: 3;
        align: center middle;
    }
    """

    BINDINGS = [
        Binding("2", "goto_stock_detail", "Detail"),
        Binding("b", "buy", "Buy"),
        Binding("s", "sell", "Sell"),
        Binding("/", "focus_search", "Search"),
        Binding("q", "quit", "Quit"),
        Binding("enter", "lookup_symbol", "Lookup"),
    ]

    def __init__(self, symbol: str = "AAPL", **kwargs) -> None:
        super().__init__(**kwargs)
        self._symbol = symbol.upper()
        self._quote: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        yield StockTicker(
            symbols=COMMON_SYMBOLS,
            data_provider=lambda s: market_data.get_quote(s),
        )
        yield Static(" SECURE BLOOMBERG TERMINAL  —  STOCK DETAIL", id="title-bar")
        yield Input(
            value=self._symbol,
            placeholder="Enter symbol (e.g. AAPL)",
            id="symbol-input",
        )
        yield Static(id="quote-display")
        yield Static(id="stats-grid")
        yield Sparkline(id="sparkline")
        with Static(id="news-section"):
            yield Static(" [bold]Company News[/]", id="news-title")
            yield Static(id="news-list")
        with Widget(id="action-buttons"):
            yield Button("Buy", id="buy-btn", variant="success")
            yield Button("Sell", id="sell-btn", variant="error")
        yield StatusBar()

    def on_mount(self) -> None:
        self._refresh()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip().upper()
        if val:
            self._symbol = val
            self._refresh()

    def _refresh(self) -> None:
        asyncio.create_task(self._async_refresh())

    async def _async_refresh(self) -> None:
        loop = asyncio.get_event_loop()
        self._quote = await loop.run_in_executor(None, market_data.get_quote, self._symbol)
        self._update_display()

        try:
            history = await loop.run_in_executor(
                None, market_data.get_history, self._symbol, "1mo", "1d"
            )
            closes = [h.get("close", 0) for h in history if h.get("close")]
            self.query_one(Sparkline).set_data(closes)
        except Exception:
            pass

        self._load_news()

    def _update_display(self) -> None:
        q = self._quote
        price = q.get("price", 0)
        change = q.get("change", 0)
        chg_pct = q.get("change_pct", 0)
        high = q.get("high", 0)
        low = q.get("low", 0)
        open_ = q.get("open", 0)
        prev_close = q.get("prev_close", 0)
        volume = q.get("volume", 0)

        arrow = "▲" if change >= 0 else "▼"
        chg_color = "green" if change >= 0 else "red"

        quote_text = (
            f"[bold #FFB000]{self._symbol}[/]\n"
            f"[bold #00FF00]${price:.2f}[/]\n"
            f"[{chg_color}]{arrow} ${abs(change):.2f}  ({abs(chg_pct):.2f}%)[/]"
        )
        self.query_one("#quote-display", Static).update(quote_text)

        stats_text = (
            f"  [bold #FFB000]Key Statistics[/]\n\n"
            f"  [#33FF33]Open:[/]  [#00FF00]{open_:.2f}[/]     "
            f"[#33FF33]Prev Close:[/]  [#00FF00]{prev_close:.2f}[/]\n"
            f"  [#33FF33]Day High:[/]  [#00FF00]{high:.2f}[/]     "
            f"[#33FF33]Day Low:[/]   [#00FF00]{low:.2f}[/]\n"
            f"  [#33FF33]Volume:[/]   [#00FF00]{volume:,}[/]"
        )
        self.query_one("#stats-grid", Static).update(stats_text)

    def _load_news(self) -> None:
        loop = asyncio.get_event_loop()

        async def fetch_news():
            try:
                from src.news import NewsManager
                nm = NewsManager()
                articles = await loop.run_in_executor(None, nm.search_news, self._symbol)
                lines = []
                for a in articles[:8]:
                    title = a.get("title", "")[:100]
                    lines.append(f"  [#00FF00]•[/] [dim]{title}[/]")
                self.query_one("#news-list", Static).update("\n".join(lines) or "[dim]No news[/]")
            except Exception:
                self.query_one("#news-list", Static).update("[dim]Unable to load news[/]")

        asyncio.create_task(fetch_news())

    def action_goto_stock_detail(self) -> None:
        pass

    def action_buy(self) -> None:
        self.app.push_screen(TradeDialog(self._symbol, "buy"))

    def action_sell(self) -> None:
        self.app.push_screen(TradeDialog(self._symbol, "sell"))

    def action_focus_search(self) -> None:
        inp = self.query_one("#symbol-input", Input)
        inp.focus()

    def action_lookup_symbol(self) -> None:
        inp = self.query_one("#symbol-input", Input)
        val = inp.value.strip().upper()
        if val and val != self._symbol:
            self._symbol = val
            self._refresh()


class TradeDialog(ModalScreen):
    DEFAULT_CSS = """
    TradeDialog {
        align: center middle;
        background: #000000 60%;
    }
    TradeDialog #dialog {
        width: 50;
        height: auto;
        border: solid #FFB000;
        background: #0a0a0a;
        padding: 1;
    }
    TradeDialog Input {
        background: #000000;
        color: #00FF00;
        border: solid #333333;
    }
    TradeDialog Label {
        color: #33FF33;
    }
    TradeDialog Button {
        margin: 1;
    }
    """

    def __init__(self, symbol: str, side: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._symbol = symbol
        self._side = side

    def compose(self) -> ComposeResult:
        with Widget(id="dialog"):
            yield Label(f" [bold #FFB000]{self._side.upper()} {self._symbol}[/]")
            yield Label(" Quantity:")
            yield Input(placeholder="Number of shares", id="qty-input")
            yield Label(" Price:")
            yield Input(placeholder="Limit price", id="price-input")
            with Widget():
                yield Button("Confirm", id="confirm-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "confirm-btn":
            qty_inp = self.query_one("#qty-input", Input)
            price_inp = self.query_one("#price-input", Input)
            try:
                qty = float(qty_inp.value)
                price = float(price_inp.value)
                self.dismiss((qty, price))
            except ValueError:
                pass

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
            event.prevent_default()
