from __future__ import annotations

from typing import Optional

from textual.widgets import Static

BARS = "▁▂▃▄▅▆▇█"


class Sparkline(Static):
    DEFAULT_CSS = """
    Sparkline {
        height: 3;
        background: #000000;
        color: #00FF00;
    }
    """

    def __init__(self, data: Optional[list[float]] = None, height: int = 3, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data = data or []
        self._chart_height = height

    def set_data(self, data: list[float]) -> None:
        self._data = data
        self._render()

    def _render(self) -> None:
        if not self._data:
            self.update("[dim]no data[/]")
            return

        n = len(self._data)
        if n < 2:
            self.update(f"[#00FF00]{self._data[0]:.2f}[/]")
            return

        mn = min(self._data)
        mx = max(self._data)
        rng = mx - mn if mx != mn else 1.0

        lines: list[str] = []
        step = max(1, n // 80)
        sampled = self._data[::step]

        for row in range(self._chart_height - 1, -1, -1):
            threshold = mn + (rng * row / (self._chart_height - 1)) if self._chart_height > 1 else mn
            next_threshold = mn + (rng * (row + 1) / (self._chart_height - 1)) if self._chart_height > 1 else mx
            bar_row: list[str] = []
            for val in sampled:
                if val >= next_threshold:
                    bar_row.append("[bold #00FF00]█[/]")
                elif val >= threshold:
                    idx = int((val - threshold) / (next_threshold - threshold) * 7) if next_threshold > threshold else 0
                    bar_row.append(f"[#33FF33]{BARS[min(idx, 7)]}[/]")
                else:
                    bar_row.append("[#0a3a0a]░[/]")
            lines.append("".join(bar_row))

        self.update("\n".join(lines))
