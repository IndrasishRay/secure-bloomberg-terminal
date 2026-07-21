from __future__ import annotations

import hashlib
import hmac
import json
import os
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", os.urandom(32).hex())
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))

AUTH_USERNAME: str = os.environ.get("AUTH_USERNAME", "admin")
AUTH_PASSWORD: str = os.environ.get("AUTH_PASSWORD", "admin")

security = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _b64encode(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return urlsafe_b64decode(data)


def _sign(header_b64: str, payload_b64: str) -> str:
    sig = hmac.new(
        SECRET_KEY.encode(),
        f"{header_b64}.{payload_b64}".encode(),
        hashlib.sha256,
    ).digest()
    return _b64encode(sig)


def create_access_token(data: dict[str, Any]) -> str:
    header = {"alg": ALGORITHM, "typ": "JWT"}
    payload: dict[str, Any] = {
        **data,
        "exp": (datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp(),
        "iat": datetime.now(timezone.utc).timestamp(),
    }
    header_b64 = _b64encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    sig_b64 = _sign(header_b64, payload_b64)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_token(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format")
    header_b64, payload_b64, sig_b64 = parts
    expected = _sign(header_b64, payload_b64)
    if not hmac.compare_digest(expected.encode(), sig_b64.encode()):
        raise ValueError("Invalid token signature")
    payload_raw = _b64decode(payload_b64)
    payload: dict[str, Any] = json.loads(payload_raw)
    exp = payload.get("exp", 0)
    if exp < datetime.now(timezone.utc).timestamp():
        raise ValueError("Token expired")
    return payload


def get_token_from_request(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:]
    cookie = request.cookies.get("access_token")
    if cookie:
        return cookie
    return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict[str, Any]:
    token: Optional[str] = None
    if credentials:
        token = credentials.credentials
    if not token:
        token = get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return decode_token(token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, response: Response) -> LoginResponse:
    if body.username != AUTH_USERNAME or body.password != AUTH_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": body.username, "username": body.username})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return LoginResponse(access_token=token, username=body.username)


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(key="access_token", httponly=True, secure=True, samesite="lax")
    return {"message": "Logged out"}


@router.get("/me")
async def me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "username": current_user.get("username", current_user.get("sub", "unknown")),
        "sub": current_user.get("sub"),
    }
