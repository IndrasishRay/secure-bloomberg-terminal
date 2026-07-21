from __future__ import annotations

from typing import Any, Callable, Optional

from rich.text import Text
from textual.strip import Strip
from textual.widget import Widget


class SparklineChart(Widget):
    DEFAULT_CSS = """
    SparklineChart {
        height: 5;
        background: black;
    }
    """

    BARS = "▁▂▃▄▅▆▇█"
    BRAILLE = "⣀⣄⣤⣦⣶⣷⣿"

    def __init__(
        self,
        symbol: str = "",
        data_provider: Optional[Callable[[str], list[float]]] = None,
        height: int = 5,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._symbol = symbol
        self._data_provider = data_provider
        self._chart_height = height
        self._prices: list[float] = []
        self._timer_handle = None

    @property
    def is_up(self) -> bool:
        if len(self._prices) < 2:
            return True
        return self._prices[-1] >= self._prices[0]

    def set_symbol(self, symbol: str) -> None:
        self._symbol = symbol
        self._prices = []
        self._fetch_history()
        self.refresh()

    def on_mount(self) -> None:
        self._fetch_history()
        self._timer_handle = self.set_interval(30.0, self._fetch_history)

    def _fetch_history(self) -> None:
        if self._data_provider is not None and self._symbol:
            try:
                history = self._data_provider(self._symbol)
                self._prices = [h.get("close", 0.0) for h in history if isinstance(h, dict)]
            except Exception:
                pass
        self.refresh()

    def set_prices(self, prices: list[float]) -> None:
        self._prices = prices
        self.refresh()

    def render_line(self, data: list[float], width: int) -> str:
        if not data:
            return " " * width

        n = len(data)
        if n == 1:
            return self.BARS[3] * width

        step = max(1, n // width) if n > width else 1
        sampled = data[::step][:width]
        if len(sampled) < 2:
            return self.BARS[3] * width

        mn, mx = min(sampled), max(sampled)
        rng = mx - mn if mx != mn else 1.0
        result: list[str] = []
        for v in sampled:
            idx = int(((v - mn) / rng) * (len(self.BARS) - 1))
            idx = max(0, min(idx, len(self.BARS) - 1))
            result.append(self.BARS[idx])
        return "".join(result).ljust(width, self.BARS[0])

    def render(self) -> list[Strip]:
        width = self.size.width
        if width < 4:
            return [Strip(Text(" " * width))]

        if self._symbol:
            label = f" {self._symbol} "
            header = Text(label, style="bold #FFB000")
        else:
            header = Text(" Sparkline ")
            header.stylize("#FFB000")

        line = self.render_line(self._prices, width - 2)

        color = "#00FF00" if self.is_up else "#FF0000"
        chart_line = Text(f" {line} ")
        chart_line.stylize(color)

        label_line = Text("")
        if self._prices:
            last_px = self._prices[-1]
            first_px = self._prices[0]
            chg = last_px - first_px
            pct = (chg / first_px * 100) if first_px else 0.0
            arrow = "▲" if chg >= 0 else "▼"
            info = f" ${last_px:.2f} {arrow}{abs(pct):.2f}% "
            info_text = Text(info)
            info_text.stylize(f"bold {color}")
            label_line = info_text

        total = Text.assemble(header, chart_line, label_line)
        padded = Text(" " * width).join(total.split())
        return [Strip(padded)]

    def __len__(self) -> int:
        return self._chart_height
