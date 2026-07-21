from __future__ import annotations

import re

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static

from src.onboarding.user_manager import user_manager

BANK_CSS = """
BankDetailsScreen {
    background: #000000;
    align: center middle;
}

BankDetailsScreen #wizard-container {
    width: 50;
    height: auto;
    border: solid #333333;
    padding: 1 2;
    background: #0a0a0a;
}

BankDetailsScreen #title {
    text-style: bold;
    color: #FFB000;
    content-align: center middle;
    height: 3;
}

BankDetailsScreen #subtitle {
    color: #808080;
    content-align: center middle;
    height: 1;
    margin-bottom: 1;
}

BankDetailsScreen Label {
    color: #00FF00;
    margin-top: 1;
}

BankDetailsScreen Input {
    background: #000000;
    color: #00FF00;
    border: solid #333333;
    margin-bottom: 0;
}

BankDetailsScreen Input:focus {
    border: solid #FFB000;
}

BankDetailsScreen Select {
    background: #000000;
    color: #00FF00;
    border: solid #333333;
    margin-bottom: 0;
}

BankDetailsScreen Select:focus {
    border: solid #FFB000;
}

BankDetailsScreen Select > .select-current {
    color: #00FF00;
}

BankDetailsScreen Select > .select-list {
    background: #0a0a0a;
    border: solid #333333;
}

BankDetailsScreen #error-msg {
    color: #FF3333;
    height: 2;
    margin-top: 0;
}

BankDetailsScreen #btn-row {
    align: center middle;
    margin-top: 1;
    height: 3;
}

BankDetailsScreen Button {
    background: #0a1a0a;
    color: #00FF00;
    border: solid #006600;
    min-width: 20;
}

BankDetailsScreen Button:hover {
    border: solid #FFB000;
    color: #FFB000;
}

BankDetailsScreen #footer {
    color: #555555;
    content-align: center middle;
    height: 1;
    margin-top: 1;
}
"""

WALLET_CSS = """
WalletSetupScreen {
    background: #000000;
    align: center middle;
}

WalletSetupScreen #wizard-container {
    width: 50;
    height: auto;
    border: solid #333333;
    padding: 1 2;
    background: #0a0a0a;
}

WalletSetupScreen #title {
    text-style: bold;
    color: #FFB000;
    content-align: center middle;
    height: 3;
}

WalletSetupScreen #subtitle {
    color: #808080;
    content-align: center middle;
    height: 1;
    margin-bottom: 1;
}

WalletSetupScreen Label {
    color: #00FF00;
    margin-top: 1;
}

WalletSetupScreen Input {
    background: #000000;
    color: #00FF00;
    border: solid #333333;
    margin-bottom: 0;
}

WalletSetupScreen Input:focus {
    border: solid #FFB000;
}

WalletSetupScreen Select {
    background: #000000;
    color: #00FF00;
    border: solid #333333;
    margin-bottom: 0;
}

WalletSetupScreen Select:focus {
    border: solid #FFB000;
}

WalletSetupScreen Select > .select-current {
    color: #00FF00;
}

WalletSetupScreen Select > .select-list {
    background: #0a0a0a;
    border: solid #333333;
}

WalletSetupScreen #error-msg {
    color: #FF3333;
    height: 2;
    margin-top: 0;
}

WalletSetupScreen #btn-row {
    align: center middle;
    margin-top: 1;
    height: 3;
}

WalletSetupScreen Button {
    background: #0a1a0a;
    color: #00FF00;
    border: solid #006600;
    min-width: 20;
}

WalletSetupScreen Button:hover {
    border: solid #FFB000;
    color: #FFB000;
}

WalletSetupScreen #footer {
    color: #555555;
    content-align: center middle;
    height: 1;
    margin-top: 1;
}
"""


class BankDetailsScreen(Screen):
    DEFAULT_CSS = BANK_CSS

    def __init__(self, user_id: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self._user_id = user_id

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard-container"):
            yield Static(" BANK DETAILS [PROTOTYPE] ", id="title")
            yield Static(
                "[italic #FFB000]This is a prototype — use dummy data only![/]",
                id="subtitle",
            )
            yield Label("Bank Name (any name)")
            yield Input(
                placeholder="e.g. Demo Bank",
                id="bank-name-input",
            )
            yield Label("Account Number (any number)")
            yield Input(
                placeholder="Any account number (stored locally, encrypted)",
                id="account-number-input",
                type="password",
            )
            yield Label("Routing Number (any 9 digits)")
            yield Input(
                placeholder="e.g. 123456789",
                id="routing-number-input",
            )
            yield Label("Account Type")
            yield Select(
                options=[
                    ("Checking", "checking"),
                    ("Savings", "savings"),
                    ("Demo", "demo"),
                ],
                id="account-type-select",
                prompt="Select account type",
            )
            yield Static("", id="error-msg")
            with Horizontal(id="btn-row"):
                yield Button("Continue", id="submit-btn", variant="success")
            yield Static("Tab to navigate · Enter to submit", id="footer")

    def on_mount(self) -> None:
        self.query_one("#bank-name-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        mapping = {
            "bank-name-input": "account-number-input",
            "account-number-input": "routing-number-input",
        }
        next_id = mapping.get(event.input.id)
        if next_id:
            self.query_one(f"#{next_id}", Input).focus()
        elif event.input.id == "routing-number-input":
            self.query_one("#account-type-select", Select).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-btn":
            self._handle_submit()

    def _handle_submit(self) -> None:
        bank_name = self.query_one("#bank-name-input", Input).value.strip()
        acct_num = self.query_one("#account-number-input", Input).value.strip()
        routing = self.query_one("#routing-number-input", Input).value.strip()
        acct_type = self.query_one("#account-type-select", Select).value
        error_display = self.query_one("#error-msg", Static)

        if not bank_name:
            error_display.update("[#FF3333]Bank name is required[/]")
            return
        if not acct_num:
            error_display.update("[#FF3333]Account number is required[/]")
            return
        if not routing:
            error_display.update("[#FF3333]Routing number is required[/]")
            return
        if routing and not re.match(r"^\d{3,}$", routing):
            error_display.update(
                "[#FF3333]Routing number should be digits[/]"
            )
            return

        user_manager.set_bank_details(self._user_id, {
            "bank_name": bank_name,
            "account_number": acct_num,
            "routing_number": routing,
            "account_type": acct_type or "checking",
        })

        self.app.push_screen(
            WalletSetupScreen(user_id=self._user_id)
        )

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
            event.prevent_default()


class WalletSetupScreen(Screen):
    DEFAULT_CSS = WALLET_CSS

    def __init__(self, user_id: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self._user_id = user_id

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard-container"):
            yield Static(" WALLET SETUP [PROTOTYPE] ", id="title")
            yield Static(
                "[italic #FFB000]This is a prototype — dummy data only![/]",
                id="subtitle",
            )
            yield Label("Wallet Address (any address)")
            yield Input(
                placeholder="0x... or any dummy address",
                id="wallet-address-input",
            )
            yield Label("Wallet Type")
            yield Select(
                options=[
                    ("MetaMask", "metamask"),
                    ("Phantom", "phantom"),
                    ("Demo", "demo"),
                ],
                id="wallet-type-select",
                prompt="Select wallet type",
            )
            yield Static("", id="error-msg")
            with Horizontal(id="btn-row"):
                yield Button("Continue", id="submit-btn", variant="success")
            yield Static("Tab to navigate · Enter to submit", id="footer")

    def on_mount(self) -> None:
        self.query_one("#wallet-address-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "wallet-address-input":
            self.query_one("#wallet-type-select", Select).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-btn":
            self._handle_submit()

    def _handle_submit(self) -> None:
        address = self.query_one(
            "#wallet-address-input", Input
        ).value.strip()
        wallet_type = self.query_one(
            "#wallet-type-select", Select
        ).value
        error_display = self.query_one("#error-msg", Static)

        if not address:
            error_display.update("[#FF3333]Wallet address is required[/]")
            return
        if len(address) < 3:
            error_display.update(
                "[#FF3333]Wallet address is too short[/]"
            )
            return

        user_manager.set_wallet(
            self._user_id, address, wallet_type or "other"
        )

        bank = user_manager.get_bank_details(self._user_id)
        bank_summary = (
            f"Bank: [bold]{bank['bank_name']}[/] "
            f"({bank['account_type']})"
        )

        from src.onboarding.tutorial_system import TutorialScreen

        self.app.push_screen(
            TutorialScreen(
                user_id=self._user_id,
                wallet_address=address,
                wallet_type=wallet_type or "other",
                bank_summary=bank_summary,
            )
        )

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
            event.prevent_default()
