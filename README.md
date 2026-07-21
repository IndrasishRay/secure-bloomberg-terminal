# Secure Bloomberg Terminal Clone

A fully functional, Bloomberg-style trading terminal prototype with live market data, news feeds, portfolio management, risk guard, and research ingestion — built entirely in Python.

⚠ **This is a PROTOTYPE/DEMO only.** No real bank details, no real trading. All data stays local.

## One-Line Install

```bash
curl -sSL https://raw.githubusercontent.com/IndrasishRay/secure-bloomberg-terminal/main/install.sh | bash
```

Then:

```bash
bloomberg
```

That's it. No API keys required for basic use.

## Features

- **Bloomberg-style TUI** — Textual-based terminal with 5 screens (Market Overview, Stock Detail, Portfolio, News, Research)
- **Live Market Data** — Stocks via yfinance, Crypto via CoinGecko (no API keys needed)
- **News Aggregation** — Finnhub API + RSS feeds (Reuters, Bloomberg, CNBC, MarketWatch)
- **Paper Trading OMS** — Portfolio management with full order lifecycle
- **7-Layer Risk Guard** — Position concentration, daily loss limits, circuit breaker, price sanity, market hours, trade frequency, minimum order
- **Security** — Fernet encryption for secrets, PBKDF2 key derivation (600K iterations), key files locked to 600 perms, comprehensive audit logging
- **Research** — arXiv q-fin paper ingestion for quantitative finance research
- **Onboarding Wizard** — Email verification, bank/wallet setup, interactive tutorial (all demo/prototype)

## Quick Start (Manual)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
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
Onboarding Wizard (first-run setup)
  ├── Registration      ─── Email + password
  ├── Email Verification ─── Dev mode auto-verify
  ├── Bank/Wallet Setup ─── Dummy/prototype data
  └── Tutorial          ─── 8-step interactive walkthrough
        │
Bloomberg TUI (Textual Framework)
  ├── Market Overview  ─── Market Data Manager
  ├── Stock Detail     ─── yfinance / CoinGecko
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
├── onboarding/               # First-run wizard
│   ├── onboarding_flow.py
│   ├── registration_wizard.py
│   ├── email_verification.py
│   ├── bank_wallet_setup.py
│   ├── tutorial_system.py
│   └── user_manager.py
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
