from __future__ import annotations

import asyncio
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Optional

from config.settings import settings
from src.storage.models import (
    AuditLog,
    NewsArticle,
    Portfolio,
    Position,
    ResearchPaper,
    Trade,
)

CREATE_PORTFOLIO = """
CREATE TABLE IF NOT EXISTS portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cash_balance REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

CREATE_POSITION = """
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id),
    symbol TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 0.0,
    avg_cost REAL NOT NULL DEFAULT 0.0,
    current_value REAL NOT NULL DEFAULT 0.0
)
"""

CREATE_TRADE = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('buy','sell')),
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','filled','cancelled'))
)
"""

CREATE_NEWS_ARTICLE = """
CREATE TABLE IF NOT EXISTS news_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    published_at TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

CREATE_RESEARCH_PAPER = """
CREATE TABLE IF NOT EXISTS research_papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '',
    abstract TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    published_at TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

CREATE_AUDIT_LOG = """
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    user TEXT NOT NULL DEFAULT '',
    details TEXT NOT NULL DEFAULT '',
    ip_address TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

CREATE_TABLES = [
    CREATE_PORTFOLIO,
    CREATE_POSITION,
    CREATE_TRADE,
    CREATE_NEWS_ARTICLE,
    CREATE_RESEARCH_PAPER,
    CREATE_AUDIT_LOG,
]


def _row_to_portfolio(row: sqlite3.Row) -> Portfolio:
    return Portfolio(
        id=row["id"],
        name=row["name"],
        cash_balance=row["cash_balance"],
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def _row_to_position(row: sqlite3.Row) -> Position:
    return Position(
        id=row["id"],
        portfolio_id=row["portfolio_id"],
        symbol=row["symbol"],
        quantity=row["quantity"],
        avg_cost=row["avg_cost"],
        current_value=row["current_value"],
    )


def _row_to_trade(row: sqlite3.Row) -> Trade:
    return Trade(
        id=row["id"],
        portfolio_id=row["portfolio_id"],
        symbol=row["symbol"],
        side=row["side"],
        quantity=row["quantity"],
        price=row["price"],
        timestamp=_parse_dt(row["timestamp"]),
        status=row["status"],
    )


def _row_to_news_article(row: sqlite3.Row) -> NewsArticle:
    return NewsArticle(
        id=row["id"],
        title=row["title"],
        source=row["source"],
        url=row["url"],
        summary=row["summary"],
        published_at=_parse_dt(row["published_at"]),
        fetched_at=_parse_dt(row["fetched_at"]),
    )


def _row_to_research_paper(row: sqlite3.Row) -> ResearchPaper:
    return ResearchPaper(
        id=row["id"],
        title=row["title"],
        authors=row["authors"],
        abstract=row["abstract"],
        url=row["url"],
        published_at=_parse_dt(row["published_at"]),
        fetched_at=_parse_dt(row["fetched_at"]),
    )


def _row_to_audit_log(row: sqlite3.Row) -> AuditLog:
    return AuditLog(
        id=row["id"],
        action=row["action"],
        user=row["user"],
        details=row["details"],
        ip_address=row["ip_address"],
        timestamp=_parse_dt(row["timestamp"]),
    )


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


class Database:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or settings.db_path
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        async with self._connect() as conn:
            for ddl in CREATE_TABLES:
                conn.execute(ddl)

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # Portfolio

    async def create_portfolio(self, portfolio: Portfolio) -> int:
        async with self._lock, self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO portfolios (name, cash_balance) VALUES (?, ?)",
                (portfolio.name, portfolio.cash_balance),
            )
            return cur.lastrowid

    async def get_portfolio(self, portfolio_id: int) -> Optional[Portfolio]:
        async with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM portfolios WHERE id = ?", (portfolio_id,)
            )
            row = cur.fetchone()
            return _row_to_portfolio(row) if row else None

    async def get_all_portfolios(self) -> list[Portfolio]:
        async with self._connect() as conn:
            cur = conn.execute("SELECT * FROM portfolios ORDER BY id")
            return [_row_to_portfolio(r) for r in cur.fetchall()]

    async def update_portfolio(self, portfolio: Portfolio) -> None:
        async with self._lock, self._connect() as conn:
            conn.execute(
                """UPDATE portfolios
                   SET name = ?, cash_balance = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                (portfolio.name, portfolio.cash_balance, portfolio.id),
            )

    async def delete_portfolio(self, portfolio_id: int) -> None:
        async with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM portfolios WHERE id = ?", (portfolio_id,))

    # Position

    async def create_position(self, position: Position) -> int:
        async with self._lock, self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO positions
                   (portfolio_id, symbol, quantity, avg_cost, current_value)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    position.portfolio_id,
                    position.symbol,
                    position.quantity,
                    position.avg_cost,
                    position.current_value,
                ),
            )
            return cur.lastrowid

    async def get_positions_for_portfolio(self, portfolio_id: int) -> list[Position]:
        async with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM positions WHERE portfolio_id = ? ORDER BY symbol",
                (portfolio_id,),
            )
            return [_row_to_position(r) for r in cur.fetchall()]

    async def update_position(self, position: Position) -> None:
        async with self._lock, self._connect() as conn:
            conn.execute(
                """UPDATE positions
                   SET quantity = ?, avg_cost = ?, current_value = ?
                   WHERE id = ?""",
                (position.quantity, position.avg_cost, position.current_value, position.id),
            )

    async def delete_position(self, position_id: int) -> None:
        async with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))

    # Trade

    async def create_trade(self, trade: Trade) -> int:
        async with self._lock, self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO trades
                   (portfolio_id, symbol, side, quantity, price, status)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    trade.portfolio_id,
                    trade.symbol,
                    trade.side,
                    trade.quantity,
                    trade.price,
                    trade.status,
                ),
            )
            return cur.lastrowid

    async def get_trades_for_portfolio(self, portfolio_id: int) -> list[Trade]:
        async with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM trades WHERE portfolio_id = ? ORDER BY timestamp DESC",
                (portfolio_id,),
            )
            return [_row_to_trade(r) for r in cur.fetchall()]

    async def update_trade_status(self, trade_id: int, status: str) -> None:
        async with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE trades SET status = ? WHERE id = ?",
                (status, trade_id),
            )

    # NewsArticle

    async def create_news_article(self, article: NewsArticle) -> int:
        async with self._lock, self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO news_articles
                   (title, source, url, summary, published_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (article.title, article.source, article.url, article.summary, article.published_at),
            )
            return cur.lastrowid

    async def get_recent_news(self, limit: int = 50) -> list[NewsArticle]:
        async with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM news_articles ORDER BY published_at DESC LIMIT ?",
                (limit,),
            )
            return [_row_to_news_article(r) for r in cur.fetchall()]

    # ResearchPaper

    async def create_research_paper(self, paper: ResearchPaper) -> int:
        async with self._lock, self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO research_papers
                   (title, authors, abstract, url, published_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (paper.title, paper.authors, paper.abstract, paper.url, paper.published_at),
            )
            return cur.lastrowid

    async def get_recent_papers(self, limit: int = 50) -> list[ResearchPaper]:
        async with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM research_papers ORDER BY published_at DESC LIMIT ?",
                (limit,),
            )
            return [_row_to_research_paper(r) for r in cur.fetchall()]

    # AuditLog

    async def create_audit_log(self, log: AuditLog) -> int:
        async with self._lock, self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO audit_logs
                   (action, user, details, ip_address)
                   VALUES (?, ?, ?, ?)""",
                (log.action, log.user, log.details, log.ip_address),
            )
            return cur.lastrowid

    async def get_recent_audit_logs(self, limit: int = 100) -> list[AuditLog]:
        async with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [_row_to_audit_log(r) for r in cur.fetchall()]
