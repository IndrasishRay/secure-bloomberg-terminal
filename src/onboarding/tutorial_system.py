from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, ProgressBar, Static, RichLog

from src.onboarding.user_manager import user_manager

TUTORIAL_STEPS = [
    {
        "title": "Welcome to Secure Bloomberg Terminal",
        "desc": (
            "You are now inside a professional-grade financial terminal.\n\n"
            "This terminal gives you real-time market data, portfolio "
            "management, risk analysis, and research tools — all protected "
            "by enterprise-grade security.\n\n"
            "Press [bold #FFB000]SPACE[/] or [bold #FFB000]ENTER[/] to continue."
        ),
        "hint": "█  SECURE BLOOMBERG TERMINAL  —  MARKET OVERVIEW  █",
    },
    {
        "title": "Market Overview — Press [bold #00FF00]1[/]",
        "desc": (
            "Press [bold #00FF00]1[/] to view live stock data.\n\n"
            "See real-time prices, gainers, losers, and watchlists "
            "for the most active symbols including SPY, QQQ, NVDA, "
            "and more.\n\n"
            "The ticker scrolls at the top. Market status is shown "
            "in the status bar at the bottom."
        ),
        "hint": "┌─ Market Overview ──────────────────────────┐\n"
        "│  SPY $543.21 ▲  NVDA $892.45 ▲  ...  │\n"
        "└───────────────────────────────────────────┘",
    },
    {
        "title": "Stock Detail — Press [bold #00FF00]2[/]",
        "desc": (
            "Press [bold #00FF00]2[/] to search and analyze stocks.\n\n"
            "Type any symbol (e.g. AAPL, TSLA, GOOGL) to see:\n"
            "  • Current price & change\n"
            "  • Price sparkline chart\n"
            "  • Key statistics\n"
            "  • Related news\n\n"
            "You can also press [bold #FFB000]/[/] to search from any screen."
        ),
        "hint": "┌─ AAPL ─────────────────────────────────────┐\n"
        "│  $198.45  ▲ +1.23%  Volume: 45.2M      │\n"
        "│  ╱╲ ╱╲ ╱╲╱╲╱╲ ╱╲ ╱╲ ╱╲ ╱╲ ╱╲          │\n"
        "└───────────────────────────────────────────┘",
    },
    {
        "title": "Portfolio — Press [bold #00FF00]3[/]",
        "desc": (
            "Press [bold #00FF00]3[/] to manage your trades.\n\n"
            "View your portfolio's:\n"
            "  • Cash balance & positions\n"
            "  • Trade history & P&L\n"
            "  • Buy/sell stocks with real-time execution\n\n"
            "All trades are logged and audited for security."
        ),
        "hint": "┌─ Portfolio ────────────────────────────────┐\n"
        "│  Cash: $49,250.00  Positions: 3         │\n"
        "│  AAPL  10  @ $189.20  Value: $19,845    │\n"
        "└───────────────────────────────────────────┘",
    },
    {
        "title": "Risk Guard — 7 Security Checks",
        "desc": (
            "Your trades are protected by [bold #FFB000]7 security checks[/]:\n\n"
            "  1. Authentication & session validation\n"
            "  2. Input sanitization & injection prevention\n"
            "  3. Rate limiting & anomaly detection\n"
            "  4. Trade validation & circuit breakers\n"
            "  5. Encryption at rest & in transit\n"
            "  6. Audit logging & forensic trails\n"
            "  7. Real-time risk scoring\n\n"
            "Financial data is encrypted using Fernet (AES-128-CBC)."
        ),
        "hint": "█  RISK GUARD  █  All 7 checks passed  █",
    },
    {
        "title": "News — Press [bold #00FF00]4[/]",
        "desc": (
            "Press [bold #00FF00]4[/] for live financial news.\n\n"
            "Aggregated from multiple sources:\n"
            "  • Finnhub News API\n"
            "  • RSS feeds from major financial outlets\n\n"
            "Stay informed with the latest market-moving "
            "headlines."
        ),
        "hint": "┌─ Financial News ───────────────────────────┐\n"
        "│  Fed holds rates steady at 4.50%        │\n"
        "│  Tech stocks rally on earnings optimism  │\n"
        "│  Oil prices surge amid supply concerns   │\n"
        "└───────────────────────────────────────────┘",
    },
    {
        "title": "Research — Press [bold #00FF00]5[/]",
        "desc": (
            "Press [bold #00FF00]5[/] for academic finance papers.\n\n"
            "Access research from arXiv and other sources:\n"
            "  • Latest papers in quantitative finance\n"
            "  • Machine learning for trading research\n"
            "  • Economic analysis & forecasting models\n\n"
            "All papers are cached locally for offline reading."
        ),
        "hint": "┌─ Research Papers ──────────────────────────┐\n"
        "│  Deep Learning for Asset Pricing         │\n"
        "│  Transformer Models in Finance           │\n"
        "│  Risk Parity Portfolio Optimization      │\n"
        "└───────────────────────────────────────────┘",
    },
    {
        "title": "You're Ready to Trade!",
        "desc": (
            "You've completed the onboarding.\n\n"
            "Quick reference:\n"
            "  [bold #00FF00]1[/] Market Overview    [bold #00FF00]4[/] News\n"
            "  [bold #00FF00]2[/] Stock Detail       [bold #00FF00]5[/] Research\n"
            "  [bold #00FF00]3[/] Portfolio          [bold #FFB000]Q[/] Quit\n\n"
            "Press [bold #FFB000]ENTER[/] to enter the terminal."
        ),
        "hint": "█  WELCOME ABOARD  █  Happy Trading!  █",
    },
]

TUTORIAL_CSS = """
TutorialScreen {
    background: #000000;
    align: center middle;
}

TutorialScreen #wizard-container {
    width: 60;
    height: auto;
    border: solid #333333;
    padding: 1 2;
    background: #0a0a0a;
}

TutorialScreen #step-counter {
    color: #555555;
    text-style: bold;
    content-align: center middle;
    height: 1;
    margin-bottom: 1;
}

TutorialScreen #step-title {
    text-style: bold;
    color: #FFB000;
    content-align: center middle;
    height: 3;
}

TutorialScreen #step-desc {
    color: #00FF00;
    height: auto;
    margin: 1 0;
}

TutorialScreen #visual-hint {
    color: #33FF33;
    background: #000000;
    border: dashed #333333;
    height: 5;
    padding: 1;
    margin: 1 0;
}

TutorialScreen #progress {
    margin: 1 0;
}

TutorialScreen ProgressBar {
    color: #00FF00;
    background: #0a0a0a;
}

TutorialScreen ProgressBar > .progress--bar {
    color: #00FF00;
    background: #006600;
}

TutorialScreen ProgressBar > .progress--percentage {
    color: #00FF00;
}

TutorialScreen #nav-hint {
    color: #555555;
    content-align: center middle;
    height: 1;
    margin-top: 1;
}

TutorialScreen #btn-row {
    align: center middle;
    height: 3;
}

TutorialScreen Button {
    background: #0a1a0a;
    color: #00FF00;
    border: solid #006600;
    min-width: 20;
}

TutorialScreen Button:hover {
    border: solid #FFB000;
    color: #FFB000;
}
"""


class TutorialScreen(Screen):
    DEFAULT_CSS = TUTORIAL_CSS

    def __init__(
        self,
        user_id: int,
        wallet_address: str = "",
        wallet_type: str = "",
        bank_summary: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._user_id = user_id
        self._wallet_address = wallet_address
        self._wallet_type = wallet_type
        self._bank_summary = bank_summary
        self._current_step = 0
        self._total_steps = len(TUTORIAL_STEPS)

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard-container"):
            yield Static("", id="step-counter")
            yield Static("", id="step-title")
            yield RichLog(id="step-desc", highlight=True, markup=True)
            yield Static("", id="visual-hint")
            yield ProgressBar(
                total=self._total_steps,
                show_percentage=True,
                id="progress",
            )
            yield Static(
                "Press [bold #FFB000]SPACE[/] or [bold #FFB000]ENTER[/] to continue · "
                "[bold #808080]ESC[/] to skip",
                id="nav-hint",
            )

    def _render_step(self) -> None:
        step = TUTORIAL_STEPS[self._current_step]
        self.query_one("#step-counter", Static).update(
            f"[#555555]Step {self._current_step + 1} of {self._total_steps}[/]"
        )
        self.query_one("#step-title", Static).update(
            f"[bold #FFB000]{step['title']}[/]"
        )
        desc_widget = self.query_one("#step-desc", RichLog)
        desc_widget.clear()
        desc_widget.write(step["desc"])
        self.query_one("#visual-hint", Static).update(
            f"[#33FF33]{step['hint']}[/]"
        )
        progress = self.query_one("#progress", ProgressBar)
        progress.update(progress=self._current_step, total=self._total_steps)

    def on_mount(self) -> None:
        self._current_step = 0
        self._render_step()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "next-btn":
            self._advance()

    def _advance(self) -> None:
        if self._current_step < self._total_steps - 1:
            self._current_step += 1
            self._render_step()
        else:
            self._complete_onboarding()

    def _complete_onboarding(self) -> None:
        user_manager.set_tutorial_completed(
            self._user_id, "terminal_walkthrough"
        )
        self.dismiss(True)

    def on_key(self, event) -> None:
        if event.key in ("space", "enter"):
            self._advance()
            event.prevent_default()
        elif event.key == "escape":
            self._complete_onboarding()
            event.prevent_default()
