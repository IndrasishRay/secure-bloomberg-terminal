from __future__ import annotations

import re
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static

from src.onboarding.user_manager import hash_password, user_manager


def validate_email(email: str) -> Optional[str]:
    if not email.strip():
        return "Email is required"
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email.strip()):
        return "Invalid email format"
    return None


def check_password_strength(password: str) -> Optional[str]:
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter"
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number"
    return None


REGISTRATION_CSS = """
RegistrationScreen {
    background: #000000;
    align: center middle;
}

RegistrationScreen #wizard-container {
    width: 50;
    height: auto;
    border: solid #333333;
    padding: 1 2;
    background: #0a0a0a;
}

RegistrationScreen #title {
    text-style: bold;
    color: #FFB000;
    content-align: center middle;
    height: 3;
}

RegistrationScreen #subtitle {
    color: #808080;
    content-align: center middle;
    height: 1;
    margin-bottom: 1;
}

RegistrationScreen Label {
    color: #00FF00;
    margin-top: 1;
}

RegistrationScreen Input {
    background: #000000;
    color: #00FF00;
    border: solid #333333;
    margin-bottom: 0;
}

RegistrationScreen Input:focus {
    border: solid #FFB000;
}

RegistrationScreen #error-msg {
    color: #FF3333;
    height: 2;
    margin-top: 0;
}

RegistrationScreen #password-hint {
    color: #808080;
    height: 1;
    text-style: italic;
}

RegistrationScreen #btn-row {
    align: center middle;
    margin-top: 1;
    height: 3;
}

RegistrationScreen Button {
    background: #0a1a0a;
    color: #00FF00;
    border: solid #006600;
    min-width: 20;
}

RegistrationScreen Button:hover {
    border: solid #FFB000;
    color: #FFB000;
}

RegistrationScreen #footer {
    color: #555555;
    content-align: center middle;
    height: 1;
    margin-top: 1;
}
"""


class RegistrationScreen(Screen):
    DEFAULT_CSS = REGISTRATION_CSS

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard-container"):
            yield Static(" SECURE BLOOMBERG TERMINAL ", id="title")
            yield Static("Create your account to begin", id="subtitle")
            yield Label("Email Address")
            yield Input(
                placeholder="you@example.com",
                id="email-input",
                type="text",
            )
            yield Static("", id="email-error", classes="error-msg")
            yield Label("Password")
            yield Input(
                placeholder="Min 8 chars, 1 uppercase, 1 number",
                id="password-input",
                type="password",
            )
            yield Static(
                "8+ characters · 1 uppercase · 1 number",
                id="password-hint",
            )
            yield Label("Confirm Password")
            yield Input(
                placeholder="Re-enter password",
                id="confirm-input",
                type="password",
            )
            yield Static("", id="error-msg")
            with Horizontal(id="btn-row"):
                yield Button("Create Account", id="submit-btn", variant="success")
            yield Static("Tab to navigate · Enter to submit", id="footer")
        yield Static("", id="error-display")

    def on_mount(self) -> None:
        self.query_one("#email-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "email-input":
            self.query_one("#password-input", Input).focus()
        elif event.input.id == "password-input":
            self.query_one("#confirm-input", Input).focus()
        elif event.input.id == "confirm-input":
            self._handle_submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-btn":
            self._handle_submit()

    def _handle_submit(self) -> None:
        email = self.query_one("#email-input", Input).value
        password = self.query_one("#password-input", Input).value
        confirm = self.query_one("#confirm-input", Input).value
        error_display = self.query_one("#error-msg", Static)

        email_err = validate_email(email)
        if email_err:
            error_display.update(f"[#FF3333]{email_err}[/]")
            return

        pw_err = check_password_strength(password)
        if pw_err:
            error_display.update(f"[#FF3333]{pw_err}[/]")
            return

        if password != confirm:
            error_display.update("[#FF3333]Passwords do not match[/]")
            return

        existing = user_manager.get_user(email)
        if existing is not None:
            error_display.update(
                "[#FF3333]An account with this email already exists[/]"
            )
            return

        pw_hash = hash_password(password)
        try:
            result = user_manager.create_user(email, pw_hash)
        except ValueError as e:
            error_display.update(f"[#FF3333]{e}[/]")
            return
        except Exception as e:
            error_display.update(
                f"[#FF3333]Registration failed: {e}[/]"
            )
            return

        from src.onboarding.email_verification import VerificationScreen

        self.app.push_screen(
            VerificationScreen(
                user_id=result["id"],
                email=result["email"],
                verification_code=result["verification_code"],
            )
        )

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
            event.prevent_default()
