# Secure Bloomberg Terminal Clone

A fully functional, Bloomberg-style trading terminal prototype with live market data, news feeds, portfolio management, risk guard, and research ingestion — **rewritten in Rust for maximum performance**.

⚠ **This is a PROTOTYPE/DEMO only.** No real bank details, no real trading. All data stays local.

## One-Line Install

```bash
curl -sSL https://raw.githubusercontent.com/IndrasishRay/secure-bloomberg-terminal-clone/main/install.sh | bash
```

Then:

```bash
bloomberg
```

That's it. The installer handles Rust installation, compilation, and setup.

## Features

- **Bloomberg-style TUI** — ratatui-based terminal with 5 screens (Market Overview, Stock Detail, Portfolio, News, Research)
- **Live Market Data** — Stocks via yfinance REST API, Crypto via CoinGecko (no API keys needed)
- **News Aggregation** — RSS feeds (Reuters, CNBC, MarketWatch)
- **Paper Trading OMS** — Portfolio management with full order lifecycle
- **7-Layer Risk Guard** — Position concentration, daily loss limits, circuit breaker, price sanity, market hours, trade frequency, minimum order
- **Security** — AES-256-GCM encryption, PBKDF2 key derivation (600K iterations), key files locked to 600 perms, comprehensive audit logging
- **Research** — arXiv q-fin paper ingestion for quantitative finance research
- **Onboarding Wizard** — Email verification, bank/wallet setup, interactive tutorial (all demo/prototype)

## Key Bindings

| Key | Action |
|-----|--------|
| `1` | Market Overview |
| `2` | Stock Detail |
| `3` | Portfolio View |
| `4` | News Feed |
| `5` | Research Papers |
| `q` | Quit / Back |
| `/` | Search |
| `Tab` | Toggle Buy/Sell |

## Why Rust?

The original Python prototype was rewritten in Rust for:
- **Performance** — Compiled native binary, no interpreter overhead
- **Memory safety** — Zero-cost abstractions with guaranteed safety
- **Startup time** — Instant startup vs Python's cold start
- **Single binary** — No dependency hell, no venv management

## Architecture

```
Onboarding Wizard (first-run CLI setup)
  ├── Registration       ─── Email + password
  ├── Email Verification  ─── Dev mode auto-verify
  ├── Bank/Wallet Setup   ─── Dummy/prototype data
  └── Tutorial           ─── Interactive walkthrough
        │
Bloomberg TUI (ratatui/crossterm)
  ├── Market Overview   ─── yfinance + CoinGecko
  ├── Stock Detail      ─── Quote + Buy/Sell UI
  ├── Portfolio View    ─── Holdings + Trade history
  ├── News Feed         ─── RSS aggregation
  └── Research          ─── arXiv q-fin ingestion
        │
  Security Layer (AES-256-GCM, PBKDF2, audit logging)
        │
  SQLite Storage (9 tables: users, portfolios, positions,
                 trades, news, research, audit, bank, wallet)
```

## Build from Source

```bash
git clone https://github.com/IndrasishRay/secure-bloomberg-terminal-clone.git
cd secure-bloomberg-terminal-clone
cargo build --release
./target/release/bloomberg-terminal
```

## Data Sources

| Source | Type | API Key Required |
|--------|------|-----------------|
| yfinance | Stock/ETF data | No |
| CoinGecko | Crypto data | No |
| RSS Feeds | News (Reuters, CNBC, MarketWatch) | No |
| arXiv | Research papers | No |

## Project Structure

```
src/
├── main.rs                   # Entry point
├── app.rs                    # TUI app loop
├── db.rs                     # SQLite database layer
├── market/                   # Market data providers
│   ├── mod.rs
│   ├── yfinance.rs
│   └── coingecko.rs
├── portfolio/                # Portfolio & OMS
│   ├── mod.rs
│   └── risk_guard.rs
├── news/                     # News ingestion
│   ├── mod.rs
│   ├── finnhub.rs
│   └── rss.rs
├── research/                 # arXiv research
│   ├── mod.rs
│   └── arxiv.rs
├── security/                 # Security layer
│   ├── mod.rs
│   ├── encryption.rs
│   └── audit.rs
├── screens/                  # TUI screens
│   ├── mod.rs
│   ├── market_overview.rs
│   ├── stock_detail.rs
│   ├── portfolio_view.rs
│   ├── news_feed.rs
│   └── research.rs
└── onboarding/               # First-run wizard
    ├── mod.rs
    └── wizard.rs
```

## License

MIT
