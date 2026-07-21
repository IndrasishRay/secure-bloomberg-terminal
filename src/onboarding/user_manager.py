from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime
from typing import Optional

from src.security.encryption import decrypt_value, encrypt_value
from src.security.key_manager import KeyManager
from src.storage.database import db

_key_manager = KeyManager()


def _get_key() -> bytes:
    return _key_manager.get_encryption_key()


def hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex() + ":" + key.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, key_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)
        expected = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, 100_000
        )
        return expected.hex() == key_hex
    except (ValueError, AttributeError):
        return False


CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email_verified INTEGER NOT NULL DEFAULT 0,
    verification_code TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

CREATE_BANK_DETAILS = """
CREATE TABLE IF NOT EXISTS bank_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    bank_name TEXT NOT NULL,
    account_number TEXT NOT NULL,
    routing_number TEXT NOT NULL,
    account_type TEXT NOT NULL DEFAULT 'checking',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

CREATE_WALLETS = """
CREATE TABLE IF NOT EXISTS wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    address TEXT NOT NULL,
    wallet_type TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

CREATE_TUTORIAL_PROGRESS = """
CREATE TABLE IF NOT EXISTS tutorial_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    tutorial_name TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT
)
"""

ONBOARDING_TABLES = [
    CREATE_USERS,
    CREATE_BANK_DETAILS,
    CREATE_WALLETS,
    CREATE_TUTORIAL_PROGRESS,
]


class UserManager:
    def initialize(self) -> None:
        with db._connect() as conn:
            for ddl in ONBOARDING_TABLES:
                conn.execute(ddl)

    def create_user(self, email: str, password_hash: str) -> dict:
        code = "".join(secrets.choice("0123456789") for _ in range(6))
        with db._connect() as conn:
            try:
                cur = conn.execute(
                    """INSERT INTO users (email, password_hash, verification_code)
                       VALUES (?, ?, ?)""",
                    (email.lower().strip(), password_hash, code),
                )
                uid = cur.lastrowid
            except Exception as e:
                if "UNIQUE constraint" in str(e):
                    raise ValueError("Email already exists")
                raise
        return {
            "id": uid,
            "email": email.lower().strip(),
            "verification_code": code,
        }

    def verify_email(self, user_id: int) -> None:
        with db._connect() as conn:
            conn.execute(
                "UPDATE users SET email_verified = 1 WHERE id = ?",
                (user_id,),
            )

    def get_user(self, email: str) -> Optional[dict]:
        with db._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email.lower().strip(),),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        with db._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        user = self.get_user(email)
        if user is None:
            return None
        if not verify_password(password, user["password_hash"]):
            return None
        return user

    def get_verification_code(self, user_id: int) -> Optional[str]:
        with db._connect() as conn:
            cur = conn.execute(
                "SELECT verification_code FROM users WHERE id = ?",
                (user_id,),
            )
            row = cur.fetchone()
            return row["verification_code"] if row else None

    def set_bank_details(self, user_id: int, details: dict) -> None:
        key = _get_key()
        enc_acct = encrypt_value(details["account_number"], key)
        with db._connect() as conn:
            conn.execute(
                "DELETE FROM bank_details WHERE user_id = ?",
                (user_id,),
            )
            conn.execute(
                """INSERT INTO bank_details
                   (user_id, bank_name, account_number, routing_number, account_type)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    user_id,
                    details["bank_name"],
                    enc_acct,
                    details["routing_number"],
                    details.get("account_type", "checking"),
                ),
            )

    def get_bank_details(self, user_id: int) -> Optional[dict]:
        with db._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM bank_details WHERE user_id = ?",
                (user_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            result = dict(row)
            key = _get_key()
            try:
                result["account_number"] = decrypt_value(
                    result["account_number"], key
                )
            except Exception:
                result["account_number"] = "***ENCRYPTED***"
            return result

    def set_wallet(
        self, user_id: int, wallet_address: str, wallet_type: str
    ) -> None:
        with db._connect() as conn:
            conn.execute(
                "DELETE FROM wallets WHERE user_id = ?",
                (user_id,),
            )
            conn.execute(
                """INSERT INTO wallets (user_id, address, wallet_type)
                   VALUES (?, ?, ?)""",
                (user_id, wallet_address.strip(), wallet_type),
            )

    def get_wallet(self, user_id: int) -> Optional[dict]:
        with db._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM wallets WHERE user_id = ?",
                (user_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def set_tutorial_completed(
        self, user_id: int, tutorial_name: str
    ) -> None:
        with db._connect() as conn:
            conn.execute(
                "DELETE FROM tutorial_progress WHERE user_id = ? AND tutorial_name = ?",
                (user_id, tutorial_name),
            )
            conn.execute(
                """INSERT INTO tutorial_progress
                   (user_id, tutorial_name, completed, completed_at)
                   VALUES (?, ?, 1, datetime('now'))""",
                (user_id, tutorial_name),
            )

    def is_tutorial_completed(
        self, user_id: int, tutorial_name: str
    ) -> bool:
        with db._connect() as conn:
            cur = conn.execute(
                """SELECT completed FROM tutorial_progress
                   WHERE user_id = ? AND tutorial_name = ?""",
                (user_id, tutorial_name),
            )
            row = cur.fetchone()
            return bool(row and row["completed"])

    def get_onboarding_status(self, user_id: int) -> dict:
        user = self.get_user_by_id(user_id)
        if user is None:
            return {
                "user_exists": False,
                "email_verified": False,
                "bank_set": False,
                "wallet_set": False,
                "tutorial_done": False,
                "onboarding_complete": False,
            }
        bank = self.get_bank_details(user_id)
        wallet = self.get_wallet(user_id)
        tutorial = self.is_tutorial_completed(
            user_id, "terminal_walkthrough"
        )
        return {
            "user_exists": True,
            "email_verified": bool(user["email_verified"]),
            "bank_set": bank is not None,
            "wallet_set": wallet is not None,
            "tutorial_done": tutorial,
            "onboarding_complete": (
                bool(user["email_verified"])
                and bank is not None
                and wallet is not None
                and tutorial
            ),
        }


user_manager = UserManager()
