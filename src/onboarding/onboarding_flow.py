from __future__ import annotations

import logging
from typing import Optional

from textual.app import App
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from src.onboarding.user_manager import user_manager

logger = logging.getLogger(__name__)

WELCOME_CSS = """
OnboardingWelcomeScreen {
    background: #000000;
    align: center middle;
}

OnboardingWelcomeScreen #wizard-container {
    width: 55;
    height: auto;
    border: solid #333333;
    padding: 1 2;
    background: #0a0a0a;
}

OnboardingWelcomeScreen #title {
    text-style: bold;
    color: #FFB000;
    content-align: center middle;
    height: 3;
}

OnboardingWelcomeScreen #tagline {
    color: #00FF00;
    content-align: center middle;
    height: 2;
}

OnboardingWelcomeScreen #description {
    color: #808080;
    height: auto;
    margin: 1 0;
}

OnboardingWelcomeScreen #features {
    color: #33FF33;
    height: auto;
    margin: 1 0;
}

OnboardingWelcomeScreen #btn-row {
    align: center middle;
    margin-top: 1;
    height: 3;
}

OnboardingWelcomeScreen Button {
    background: #0a1a0a;
    color: #00FF00;
    border: solid #006600;
    min-width: 24;
}

OnboardingWelcomeScreen Button:hover {
    border: solid #FFB000;
    color: #FFB000;
}

OnboardingWelcomeScreen .small-btn {
    background: #0a0a0a;
    color: #808080;
    border: solid #333333;
    min-width: 24;
}

OnboardingWelcomeScreen .small-btn:hover {
    color: #FFB000;
    border: solid #FFB000;
}

OnboardingWelcomeScreen #footer {
    color: #555555;
    content-align: center middle;
    height: 1;
    margin-top: 1;
}
"""


class OnboardingWelcomeScreen(Screen):
    DEFAULT_CSS = WELCOME_CSS

    def __init__(
        self,
        status: dict,
        on_complete: callable,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._status = status
        self._on_complete = on_complete

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard-container"):
            yield Static(
                " SECURE BLOOMBERG TERMINAL ", id="title"
            )
            yield Static("First-time setup required", id="tagline")
            yield Static(
                "Before you can access the terminal, we need to set up a few things:\n\n"
                "  [bold #00FF00]1.[/] Create your account\n"
                "  [bold #00FF00]2.[/] Verify your email\n"
                "  [bold #00FF00]3.[/] Add bank details\n"
                "  [bold #00FF00]4.[/] Connect a wallet\n"
                "  [bold #00FF00]5.[/] Quick tutorial\n\n"
                "Your data is encrypted and stored locally.",
                id="description",
            )
            with Horizontal(id="btn-row"):
                yield Button(
                    "Begin Setup", id="start-btn", variant="success"
                )
            yield Button("Skip (Dev Mode)", id="skip-btn", classes="small-btn")
            yield Static(
                "Tab to navigate · Enter to select", id="footer"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            from src.onboarding.registration_wizard import RegistrationScreen
            self.app.push_screen(RegistrationScreen())
        elif event.button.id == "skip-btn":
            self._on_complete(True)
            self.dismiss(True)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self._on_complete(False)
            self.dismiss(False)
            event.prevent_default()


def check_onboarding_status() -> dict:
    user_manager.initialize()

    has_any_user = False
    status = {
        "user_exists": False,
        "email_verified": False,
        "bank_set": False,
        "wallet_set": False,
        "tutorial_done": False,
        "onboarding_complete": False,
        "user_id": None,
    }

    try:
        with db._connect() as conn:
            cur = conn.execute(
                "SELECT id, email_verified FROM users ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
            if row:
                has_any_user = True
                uid = row["id"]
                status["user_id"] = uid
                status["user_exists"] = True
                status["email_verified"] = bool(row["email_verified"])

        if has_any_user:
            bank = user_manager.get_bank_details(uid)
            wallet = user_manager.get_wallet(uid)
            tutorial = user_manager.is_tutorial_completed(
                uid, "terminal_walkthrough"
            )
            status["bank_set"] = bank is not None
            status["wallet_set"] = wallet is not None
            status["tutorial_done"] = tutorial
    except Exception as e:
        logger.warning("Error checking onboarding status: %s", e)

    status["onboarding_complete"] = (
        status["email_verified"]
        and status["bank_set"]
        and status["wallet_set"]
        and status["tutorial_done"]
    )

    return status


def run_on_startup(app: App, callback: Optional[callable] = None) -> None:
    """Call from main.py after DB init. Checks onboarding and starts wizard if needed."""
    status = check_onboarding_status()

    if status["onboarding_complete"]:
        logger.info("Onboarding already complete, starting terminal")
        if callback:
            callback(True)
        return

    logger.info("Onboarding incomplete, starting wizard")
    user_id = status.get("user_id")

    if status["user_exists"] and not status["email_verified"]:
        from src.onboarding.email_verification import VerificationScreen

        user = user_manager.get_user_by_id(user_id)
        code = user_manager.get_verification_code(user_id)
        app.push_screen(
            VerificationScreen(
                user_id=user_id,
                email=user["email"] if user else "",
                verification_code=code or "",
            )
        )
        return

    if status["user_exists"] and status["email_verified"] and not status["bank_set"]:
        from src.onboarding.bank_wallet_setup import BankDetailsScreen

        app.push_screen(BankDetailsScreen(user_id=user_id))
        return

    if (
        status["user_exists"]
        and status["email_verified"]
        and status["bank_set"]
        and not status["wallet_set"]
    ):
        from src.onboarding.bank_wallet_setup import WalletSetupScreen

        app.push_screen(WalletSetupScreen(user_id=user_id))
        return

    if (
        status["user_exists"]
        and status["email_verified"]
        and status["bank_set"]
        and status["wallet_set"]
        and not status["tutorial_done"]
    ):
        from src.onboarding.tutorial_system import TutorialScreen

        app.push_screen(
            TutorialScreen(user_id=user_id)
        )
        return

    def on_complete(success: bool) -> None:
        if success:
            logger.info("Onboarding completed successfully")
        if callback:
            callback(success)

    app.push_screen(
        OnboardingWelcomeScreen(status=status, on_complete=on_complete)
    )
