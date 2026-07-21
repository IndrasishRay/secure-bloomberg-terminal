from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Optional

from textual.widget import Widget
from rich.text import Text


class StatusBar(Widget):
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: #0a0a0a;
        layer: overlay;
        dock: bottom;
    }
    """

    def __init__(
        self,
        portfolio_value_provider: Optional[Callable[[], float]] = None,
        market_status_provider: Optional[Callable[[], dict[str, Any]]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._portfolio_value = 0.0
        self._portfolio_value_provider = portfolio_value_provider
        self._market_status_provider = market_status_provider
        self._market_open = False
        self._connected = True
        self._last_update: str = ""
        self._tick = 0
        self._timer_handle = None

    def on_mount(self) -> None:
        self._update()
        self._timer_handle = self.set_interval(2.0, self._update)

    def on_click(self) -> None:
        self._update()

    def set_connection_status(self, connected: bool) -> None:
        self._connected = connected
        self.refresh()

    def _update(self) -> None:
        self._tick += 1
        now = datetime.now()
        self._last_update = now.strftime("%H:%M:%S")

        if self._portfolio_value_provider is not None:
            try:
                self._portfolio_value = self._portfolio_value_provider()
            except Exception:
                pass

        if self._market_status_provider is not None:
            try:
                status = self._market_status_provider()
                self._market_open = bool(status.get("is_open", False))
            except Exception:
                pass

        self.refresh()

    def render(self) -> Text:
        blink = self._tick % 4 < 2
        conn_color = "#00FF00" if self._connected else "#FF0000"
        conn_symbol = "●" if self._connected else "○"
        conn_blink = "" if blink else " "

        mkt_color = "#00FF00" if self._market_open else "#FFB000"
        mkt_label = "OPEN" if self._market_open else "CLOSED"

        parts = [
            (f"[{conn_color}]{conn_symbol}{conn_blink}[/] ", ""),
            (f"[{mkt_color}]MARKET: {mkt_label}[/] ", ""),
            ("[#808080]|[/] ", ""),
            ("[dim]Portfolio:[/] ", ""),
            (f"[#00FF00]${self._portfolio_value:,.2f}[/] ", ""),
            ("[#808080]|[/] ", ""),
            ("[dim]Last:[/] ", ""),
            (f"[#808080]{self._last_update}[/] ", ""),
            ("[#808080]|[/] ", ""),
            ("[dim]Q:quit[/] ", ""),
            ("[dim]R:refresh[/] ", ""),
            ("[dim]S:search[/] ", ""),
            ("[dim]? :help[/] ", ""),
        ]

        result = Text()
        for text, _ in parts:
            result.append(text)
        return result
