from __future__ import annotations

import os
import secrets

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static

from src.onboarding.user_manager import user_manager
from src.storage.database import db

VERIFICATION_CSS = """
VerificationScreen {
    background: #000000;
    align: center middle;
}

VerificationScreen #wizard-container {
    width: 50;
    height: auto;
    border: solid #333333;
    padding: 1 2;
    background: #0a0a0a;
}

VerificationScreen #title {
    text-style: bold;
    color: #FFB000;
    content-align: center middle;
    height: 3;
}

VerificationScreen #info-text {
    color: #00FF00;
    content-align: center middle;
    height: auto;
    margin-bottom: 1;
}

VerificationScreen #dev-code {
    color: #FFB000;
    content-align: center middle;
    height: 1;
    text-style: bold;
    margin-bottom: 1;
}

VerificationScreen Label {
    color: #00FF00;
    margin-top: 1;
}

VerificationScreen Input {
    background: #000000;
    color: #00FF00;
    border: solid #333333;
    text-align: center;
}

VerificationScreen Input:focus {
    border: solid #FFB000;
}

VerificationScreen #error-msg {
    color: #FF3333;
    height: 2;
    content-align: center middle;
}

VerificationScreen #btn-row {
    align: center middle;
    margin-top: 1;
    height: 3;
}

VerificationScreen Button {
    background: #0a1a0a;
    color: #00FF00;
    border: solid #006600;
    min-width: 20;
}

VerificationScreen Button:hover {
    border: solid #FFB000;
    color: #FFB000;
}

VerificationScreen #resend-btn {
    background: #0a0a0a;
    color: #808080;
    border: solid #333333;
    min-width: 20;
}

VerificationScreen #resend-btn:hover {
    color: #FFB000;
    border: solid #FFB000;
}

VerificationScreen #footer {
    color: #555555;
    content-align: center middle;
    height: 1;
    margin-top: 1;
}
"""


class VerificationScreen(Screen):
    DEFAULT_CSS = VERIFICATION_CSS

    def __init__(
        self,
        user_id: int,
        email: str,
        verification_code: str,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._user_id = user_id
        self._email = email
        self._code = verification_code
        self._dev_mode = False

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard-container"):
            yield Static(" VERIFY YOUR EMAIL ", id="title")
            yield Static(
                f"A verification code has been sent to [bold]{self._email}[/]",
                id="info-text",
            )
            dev_code = ""
            if os.environ.get("DEV_MODE", "1") == "1":
                self._dev_mode = True
                dev_code = f"[#FFB000]Dev Mode — Your code: {self._code}[/]"
            yield Static(dev_code, id="dev-code")
            yield Label("Enter 6-digit verification code")
            yield Input(
                placeholder="000000",
                id="code-input",
                type="text",
                max_length=6,
            )
            yield Static("", id="error-msg")
            with Horizontal(id="btn-row"):
                yield Button("Verify", id="verify-btn", variant="success")
            yield Button("Resend Code", id="resend-btn")
            yield Static("Tab to navigate · Enter to submit", id="footer")

    def on_mount(self) -> None:
        self.query_one("#code-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "code-input":
            self._handle_verify()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "verify-btn":
            self._handle_verify()
        elif event.button.id == "resend-btn":
            self._resend_code()

    def _handle_verify(self) -> None:
        code_input = self.query_one("#code-input", Input).value.strip()
        error_display = self.query_one("#error-msg", Static)

        if len(code_input) != 6 or not code_input.isdigit():
            error_display.update(
                "[#FF3333]Please enter a valid 6-digit code[/]"
            )
            return

        stored_code = user_manager.get_verification_code(self._user_id)
        if stored_code is None:
            error_display.update("[#FF3333]User not found[/]")
            return

        if self._dev_mode:
            user_manager.verify_email(self._user_id)
        else:
            if code_input != stored_code:
                error_display.update("[#FF3333]Invalid verification code[/]")
                return
            user_manager.verify_email(self._user_id)

        from src.onboarding.bank_wallet_setup import BankDetailsScreen

        self.app.push_screen(
            BankDetailsScreen(user_id=self._user_id)
        )

    def _resend_code(self) -> None:
        new_code = "".join(secrets.choice("0123456789") for _ in range(6))
        with db._connect() as conn:
            conn.execute(
                "UPDATE users SET verification_code = ? WHERE id = ?",
                (new_code, self._user_id),
            )
        self._code = new_code
        dev_display = self.query_one("#dev-code", Static)
        if self._dev_mode:
            dev_display.update(
                f"[#FFB000]Dev Mode — Your code: {self._code}[/]"
            )
        error_display = self.query_one("#error-msg", Static)
        error_display.update("[#00FF00]New verification code sent[/]")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
            event.prevent_default()
