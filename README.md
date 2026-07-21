# Secure Bloomberg Terminal Clone

A fully functional, secure Bloomberg-style trading terminal with live market data, news feeds, portfolio management, risk guard, and research ingestion — built entirely in Python.

## Features

- **Bloomberg-style TUI** — Textual-based terminal with 5 screens (Market Overview, Stock Detail, Portfolio, News, Research)
- **Live Market Data** — Stocks via yfinance/Alpaca, Crypto via CoinGecko
- **News Aggregation** — Finnhub API + RSS feeds (Reuters, Bloomberg, CNBC, MarketWatch)
- **Paper Trading OMS** — Portfolio management with full order lifecycle
- **7-Layer Risk Guard** — Position concentration, daily loss limits, circuit breaker, price sanity, market hours, trade frequency, minimum order
- **Security** — Fernet encryption for secrets, PBKDF2 key derivation (600K iterations), key files locked to 600 perms, comprehensive audit logging
- **Research** — arXiv q-fin paper ingestion for quantitative finance research

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys (Alpaca, Finnhub)
python src/main.py
```

### Key Bindings

| Key | Action |
|-----|--------|
| `1` | Market Overview |
| `2` | Stock Detail |
| `3` | Portfolio View |
| `4` | News Feed |
| `5` | Research Papers |
| `q` | Quit |
| `s` / `/` | Search |

## Architecture

```
Bloomberg TUI (Textual Framework)
  ├── Market Overview  ─── Market Data Manager
  ├── Stock Detail     ─── yfinance / Alpaca / CoinGecko
  ├── Portfolio View   ─── PortfolioManager + RiskGuard
  ├── News Feed        ─── Finnhub / RSS
  └── Research         ─── arXiv q-fin
        │
  Security Layer (encryption, audit, key management)
        │
  SQLite Storage (6 tables: portfolios, positions, trades,
                       news, research papers, audit logs)
```

## Data Sources

| Source | Type | API Key Required |
|--------|------|-----------------|
| yfinance | Stock/ETF data | No |
| Alpaca Markets | Live stocks + paper trading | Yes (free) |
| CoinGecko | Crypto data | No |
| Finnhub | News | Yes (free tier) |
| RSS Feeds | News (Reuters, Bloomberg, CNBC) | No |
| arXiv | Research papers | No |

## Project Structure

```
src/
├── main.py                   # Entry point
├── market/                   # Market data providers
│   ├── yfinance_provider.py
│   ├── alpaca_provider.py
│   └── coingecko_provider.py
├── portfolio/                # Portfolio & OMS
│   ├── manager.py
│   └── risk_guard.py
├── news/                     # News ingestion
│   ├── finnhub_provider.py
│   └── rss_provider.py
├── research/                 # arXiv research
│   └── arxiv_ingest.py
├── security/                 # Security layer
│   ├── encryption.py
│   ├── key_manager.py
│   └── audit.py
├── storage/                  # Database layer
│   ├── models.py
│   └── database.py
└── terminal/                 # Bloomberg TUI
    ├── app.py
    ├── screens/              # 5 screens
    └── widgets/              # Custom TUI widgets
```

## License

MIT
