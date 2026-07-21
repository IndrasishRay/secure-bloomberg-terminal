from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Portfolio:
    id: Optional[int] = None
    name: str = ""
    cash_balance: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Position:
    id: Optional[int] = None
    portfolio_id: int = 0
    symbol: str = ""
    quantity: float = 0.0
    avg_cost: float = 0.0
    current_value: float = 0.0


@dataclass
class Trade:
    id: Optional[int] = None
    portfolio_id: int = 0
    symbol: str = ""
    side: str = ""  # buy | sell
    quantity: float = 0.0
    price: float = 0.0
    timestamp: Optional[datetime] = None
    status: str = "pending"  # pending | filled | cancelled


@dataclass
class NewsArticle:
    id: Optional[int] = None
    title: str = ""
    source: str = ""
    url: str = ""
    summary: str = ""
    published_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None


@dataclass
class ResearchPaper:
    id: Optional[int] = None
    title: str = ""
    authors: str = ""  # comma-separated
    abstract: str = ""
    url: str = ""
    published_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None


@dataclass
class AuditLog:
    id: Optional[int] = None
    action: str = ""
    user: str = ""
    details: str = ""
    ip_address: str = ""
    timestamp: Optional[datetime] = None
