from __future__ import annotations

import hashlib
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from config.settings import settings
from src.security.encryption import encrypt_value
from src.security.key_manager import KeyManager
from src.storage.database import db
from web.auth import create_access_token, get_current_user
from web.email_service import email_service

router = APIRouter(prefix="/api/user", tags=["user"])

DEV_MODE = os.environ.get("DEV_MODE", "false").lower() in ("1", "true", "yes")
_key_manager = KeyManager()
_encryption_key: bytes = _key_manager.get_encryption_key()

_verification_codes: dict[str, dict[str, Any]] = {}
_vc_lock = threading.Lock()

EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PASSWORD_MIN = 8


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=PASSWORD_MIN, description="User password")


class VerifyEmailRequest(BaseModel):
    email: str
    code: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ResendCodeRequest(BaseModel):
    email: str


class BankDetailsRequest(BaseModel):
    bank_name: str = Field(..., min_length=1)
    account_number: str = Field(..., min_length=1)
    routing_number: str = Field(..., min_length=1)
    account_type: str = Field("checking", pattern="^(checking|savings)$")


class WalletRequest(BaseModel):
    address: str = Field(..., min_length=1)
    wallet_type: str = Field("ethereum", pattern="^(ethereum|bitcoin|solana|polygon)$")


class CompleteTutorialRequest(BaseModel):
    tutorial_name: str = Field(..., min_length=1)


class TradeRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    side: str = Field(..., pattern="^(buy|sell)$")
    quantity: float = Field(..., gt=0)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _validate_email(email: str) -> None:
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")


def _validate_password(password: str) -> None:
    if len(password) < PASSWORD_MIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {PASSWORD_MIN} characters",
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain an uppercase letter")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain a lowercase letter")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain a digit")


def _get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    with db._connect() as conn:
        cur = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
        row = cur.fetchone()
        return dict(row) if row else None


def _ensure_users_table() -> None:
    with db._connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                email_verified INTEGER NOT NULL DEFAULT 0,
                bank_name TEXT DEFAULT '',
                account_number_encrypted TEXT DEFAULT '',
                routing_number TEXT DEFAULT '',
                account_type TEXT DEFAULT 'checking',
                wallet_address TEXT DEFAULT '',
                wallet_type TEXT DEFAULT '',
                tutorial_completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )"""
        )


_ensure_users_table()


def _compute_onboarding(user: dict[str, Any]) -> dict[str, Any]:
    email_verified = bool(user.get("email_verified", 0))
    bank_set = bool(user.get("bank_name")) and bool(user.get("account_number_encrypted"))
    wallet_set = bool(user.get("wallet_address"))
    tutorial_completed = bool(user.get("tutorial_completed", 0))
    steps = [not email_verified, not bank_set, not wallet_set, not tutorial_completed]
    steps_remaining = sum(steps)
    return {
        "email_verified": email_verified,
        "bank_set": bank_set,
        "wallet_set": wallet_set,
        "tutorial_completed": tutorial_completed,
        "steps_remaining": steps_remaining,
    }


@router.post("/register")
async def register(body: RegisterRequest, request: Request) -> dict[str, Any]:
    _validate_email(body.email)
    _validate_password(body.password)

    email_key = body.email.lower().strip()

    existing = _get_user_by_email(email_key)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    password_hash = _hash_password(body.password)
    with db._lock, db._connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email_key, password_hash),
        )
        user_id = cur.lastrowid

    code = email_service.generate_verification_code()
    with _vc_lock:
        _verification_codes[email_key] = {
            "code": code,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=settings.verification_code_expiry_minutes),
        }

    email_service.send_verification_email(email_key, code)

    result: dict[str, Any] = {
        "user_id": user_id,
        "message": "Verification code sent",
    }
    if DEV_MODE:
        result["verification_code"] = code

    ip = request.client.host if request.client else "127.0.0.1"
    db.create_audit_log("user.register", user=email_key, details=f"User registered", ip_address=ip)
    return result


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest) -> dict[str, Any]:
    email_key = body.email.lower().strip()

    user = _get_user_by_email(email_key)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.get("email_verified"):
        return {"message": "Email already verified"}

    with _vc_lock:
        stored = _verification_codes.get(email_key)

    if not stored:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No verification code found. Request a new one.")

    if datetime.now(timezone.utc) > stored["expires_at"]:
        with _vc_lock:
            _verification_codes.pop(email_key, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code expired. Request a new one.")

    if stored["code"] != body.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")

    with db._lock, db._connect() as conn:
        conn.execute(
            "UPDATE users SET email_verified = 1, updated_at = datetime('now') WHERE email = ?",
            (email_key,),
        )

    with _vc_lock:
        _verification_codes.pop(email_key, None)

    email_service.send_welcome_email(email_key)
    return {"message": "Email verified successfully"}


@router.post("/login")
async def login(body: LoginRequest) -> dict[str, Any]:
    email_key = body.email.lower().strip()

    user = _get_user_by_email(email_key)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    password_hash = _hash_password(body.password)
    if user["password_hash"] != password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token({"sub": email_key, "email": email_key, "user_id": user["id"]})
    onboarding = _compute_onboarding(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
        },
        "onboarding_status": onboarding,
    }


@router.post("/resend-code")
async def resend_code(body: ResendCodeRequest) -> dict[str, Any]:
    email_key = body.email.lower().strip()

    user = _get_user_by_email(email_key)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.get("email_verified"):
        return {"message": "Email already verified"}

    code = email_service.generate_verification_code()
    with _vc_lock:
        _verification_codes[email_key] = {
            "code": code,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=settings.verification_code_expiry_minutes),
        }

    email_service.send_verification_email(email_key, code)

    result: dict[str, Any] = {"message": "Verification code resent"}
    if DEV_MODE:
        result["verification_code"] = code
    return result


@router.get("/profile")
async def get_profile(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    email = current_user.get("email", "")
    user = _get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "email": user["email"],
        "email_verified": bool(user["email_verified"]),
        "bank_set": bool(user["bank_name"]) and bool(user["account_number_encrypted"]),
        "wallet_set": bool(user["wallet_address"]),
        "tutorial_completed": bool(user["tutorial_completed"]),
    }


@router.put("/bank-details")
async def set_bank_details(body: BankDetailsRequest, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    email = current_user.get("email", "")
    user = _get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.get("email_verified"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email must be verified before setting bank details")

    encrypted_account = encrypt_value(body.account_number, _encryption_key)

    with db._lock, db._connect() as conn:
        conn.execute(
            """UPDATE users
               SET bank_name = ?, account_number_encrypted = ?, routing_number = ?, account_type = ?, updated_at = datetime('now')
               WHERE email = ?""",
            (body.bank_name, encrypted_account, body.routing_number, body.account_type, email),
        )

    return {"message": "Bank details saved successfully"}


@router.put("/wallet")
async def set_wallet(body: WalletRequest, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    email = current_user.get("email", "")
    user = _get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    with db._lock, db._connect() as conn:
        conn.execute(
            "UPDATE users SET wallet_address = ?, wallet_type = ?, updated_at = datetime('now') WHERE email = ?",
            (body.address, body.wallet_type, email),
        )

    return {"message": "Wallet saved successfully"}


@router.get("/onboarding-status")
async def get_onboarding_status(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    email = current_user.get("email", "")
    user = _get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _compute_onboarding(user)


@router.post("/complete-tutorial")
async def complete_tutorial(body: CompleteTutorialRequest, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    email = current_user.get("email", "")
    user = _get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    with db._lock, db._connect() as conn:
        conn.execute(
            "UPDATE users SET tutorial_completed = 1, updated_at = datetime('now') WHERE email = ?",
            (email,),
        )

    user_after = _get_user_by_email(email)
    onboarding = _compute_onboarding(user_after)

    steps = ["email_verified", "bank_set", "wallet_set", "tutorial_completed"]
    remaining = [s for s in steps if not onboarding.get(s, False)]
    next_step = remaining[0] if remaining else "all_complete"

    return {
        "tutorial_completed": True,
        "next_step": next_step,
    }


@router.get("/portfolio")
async def get_user_portfolio(current_user: dict[str, Any] = Depends(get_current_user)) -> Any:
    portfolios = db.list_portfolios()
    if not portfolios:
        return {"portfolios": [], "total_value": 0.0}

    result = []
    for p in portfolios:
        positions = db.get_positions_by_portfolio(p.id)
        total_position_value = sum(pos.current_value for pos in positions)
        result.append({
            "id": p.id,
            "name": p.name,
            "cash_balance": p.cash_balance,
            "positions_value": round(total_position_value, 2),
            "total_value": round(p.cash_balance + total_position_value, 2),
            "positions": [
                {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "avg_cost": pos.avg_cost,
                    "current_value": pos.current_value,
                }
                for pos in positions
            ],
        })

    total = sum(r["total_value"] for r in result)
    return {"portfolios": result, "total_value": round(total, 2)}


@router.post("/trade")
async def execute_trade(body: TradeRequest, request: Request, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    email = current_user.get("email", "")
    user = _get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    portfolios = db.list_portfolios()
    if not portfolios:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No portfolio found. Create one first.")

    portfolio = portfolios[0]
    symbol = body.symbol.upper()
    side = body.side
    quantity = body.quantity

    from src.market import market_data

    quote = market_data.get_quote(symbol)
    price: float = 0.0
    if "error" not in quote:
        price = float(quote.get("price", 0.0))
    if price <= 0:
        price = 0.01

    position = db.get_position_by_symbol(portfolio.id, symbol)

    if side == "sell":
        if not position or position.quantity < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient {symbol} shares. Held: {position.quantity if position else 0}, Requested: {quantity}",
            )

    total_cost = round(quantity * price, 2)

    if side == "buy":
        if portfolio.cash_balance < total_cost:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient cash. Balance: ${portfolio.cash_balance:.2f}, Required: ${total_cost:.2f}",
            )

    trade = db.create_trade(portfolio.id, symbol, side, quantity, price)

    if side == "buy":
        new_cash = round(portfolio.cash_balance - total_cost, 2)
        if position:
            new_qty = round(position.quantity + quantity, 6)
            new_avg = round(((position.avg_cost * position.quantity) + total_cost) / new_qty, 2)
            new_value = round(price * new_qty, 2)
            db.update_position(position.id, new_qty, new_avg, new_value)
        else:
            db.create_position(portfolio.id, symbol, quantity, price)
        ip = request.client.host if request.client else "127.0.0.1"
        db.create_audit_log("trade.execute", user=email, details=f"Buy {quantity} {symbol} @ ${price}", ip_address=ip)
    else:
        new_qty = round(position.quantity - quantity, 6)
        new_cash = round(portfolio.cash_balance + total_cost, 2)
        if new_qty <= 0:
            db.delete_position(position.id)
        else:
            new_value = round(price * new_qty, 2)
            db.update_position(position.id, new_qty, position.avg_cost, new_value)
        ip = request.client.host if request.client else "127.0.0.1"
        db.create_audit_log("trade.execute", user=email, details=f"Sell {quantity} {symbol} @ ${price}", ip_address=ip)

    db.update_portfolio_cash(portfolio.id, new_cash)

    return {
        "success": True,
        "trade_id": trade.id,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
        "total": total_cost,
        "remaining_cash": new_cash,
    }
