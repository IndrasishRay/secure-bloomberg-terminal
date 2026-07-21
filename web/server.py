from __future__ import annotations

import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import settings
from web.routes import admin, market, news, portfolio, research
from web.user_api import router as user_router

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, requests_per_minute: int = 100) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Any) -> JSONResponse:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = now - 60

        self._requests[client_ip] = [t for t in self._requests[client_ip] if t > window]

        if len(self._requests[client_ip]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )

        self._requests[client_ip].append(now)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> JSONResponse:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from src.storage.database import db

    db.initialize()
    app.state.db = db
    logger.info("Database initialized at %s", settings.db_path)
    yield
    logger.info("Web server shutting down")


app = FastAPI(
    title="Secure Bloomberg Terminal API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(admin.router)
app.include_router(market.router)
app.include_router(portfolio.router)
app.include_router(news.router)
app.include_router(research.router)

from web.auth import router as auth_router

app.include_router(auth_router)
app.include_router(user_router, prefix="/api")


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": "Not authenticated"})


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": "Forbidden"})


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@app.exception_handler(429)
async def too_many_requests_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again later."})


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Internal server error")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "name": "Secure Bloomberg Terminal API",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }
