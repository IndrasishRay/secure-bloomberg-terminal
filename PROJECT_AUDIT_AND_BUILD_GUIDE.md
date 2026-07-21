# Secure Bloomberg Terminal Clone — Project Audit & Build Guide

> **Author:** Indrasish Ray  
> **Date:** July 2026  
> **Language:** Rust (ported from Python prototype)  
> **Repository:** https://github.com/IndrasishRay/secure-bloomberg-terminal-clone  
> **Branch:** `speed`

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Audit](#2-architecture-audit)
3. [Module-by-Module Breakdown](#3-module-by-module-breakdown)
4. [Build & Run Guide](#4-build--run-guide)
5. [How to Rebuild This From Scratch](#5-how-to-rebuild-this-from-scratch)
6. [Design Decisions & Tradeoffs](#6-design-decisions--tradeoffs)
7. [Known Issues & Stubs](#7-known-issues--stubs)
8. [Roadmap](#8-roadmap)

---

## 1. Project Overview

A **Bloomberg-style trading terminal** that runs entirely in your terminal. It connects to free public APIs for stock data, crypto prices, financial news, and academic research papers. All data is stored locally in SQLite.

### Statistics

| Metric | Value |
|--------|-------|
| Rust source files | 24 files across 9 modules |
| Total lines of Rust | ~2,230 |
| Database tables | 9 |
| External API integrations | 4 (Yahoo Finance, CoinGecko, RSS, arXiv) |
| TUI screens | 5 |
| Risk checks | 7-layer system (6 active, 1 placeholder) |
| Encryption | AES-256-GCM + PBKDF2 (600K iterations) |
| Git commits | 3 |
| Branches | `master`, `speed` |

### What It Does

1. **Market Data** — Fetches real-time stock quotes (via Yahoo Finance) and crypto prices (via CoinGecko). No API key needed.
2. **News Aggregation** — Parses RSS feeds from Reuters, CNBC, and MarketWatch.
3. **Paper Trading** — A portfolio manager with buy/sell, position tracking, and trade history.
4. **Risk Guard** — 7 safety checks before every trade (concentration limits, loss limits, frequency limits, etc.).
5. **Research** — Ingests quantitative finance papers from arXiv.
6. **Security** — Encrypted key storage, password hashing, audit logging.
7. **Onboarding Wizard** — First-run setup with registration, demo bank/wallet, and interactive tutorial.

---

## 2. Architecture Audit

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│                         main.rs                             │
│  init_logger → init_db → init_crypto → onboarding → app    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                         app.rs                              │
│              crossterm raw mode + ratatui event loop        │
│                                                             │
│  ┌────────────┐  ┌───────────┐  ┌──────────┐               │
│  │ Market     │  │ Stock     │  │ Portfolio│               │
│  │ Overview   │  │ Detail    │  │ View     │               │
│  └─────┬──────┘  └─────┬─────┘  └────┬─────┘               │
│        │               │              │                     │
│  ┌─────┴──────┐  ┌─────┴─────┐  ┌────┴─────┐               │
│  │ News Feed  │  │ Research  │  │ (screens)│               │
│  └─────┬──────┘  └─────┬─────┘  └──────────┘               │
└────────┼───────────────┼────────────────────────────────────┘
         │               │
         ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│  market/       news/      research/     portfolio/          │
│  yfinance      rss        arxiv         risk_guard          │
│  coingecko     finnhub                  mod.rs              │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│                         db.rs                               │
│                 SQLite (rusqlite — bundled)                  │
└─────────────────────────────────────────────────────────────┘
```

### Module Dependency Graph (textual)

```
main.rs
 ├── app.rs
 │    ├── screens::market_overview  ──>  market
 │    ├── screens::stock_detail     ──>  market
 │    ├── screens::portfolio_view   ──>  db
 │    ├── screens::news_feed
 │    └── screens::research
 ├── db.rs
 ├── onboarding::wizard  ──>  security::encryption, db
 └── security::encryption
```

### Database Schema (9 tables)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `users` | User accounts | id, email, password_hash, verified, created_at |
| `portfolios` | Trading portfolios | id, name, cash_balance, user_id |
| `positions` | Current holdings | id, portfolio_id, symbol, quantity, cost_basis, current_value |
| `trades` | Order history | id, portfolio_id, symbol, side, quantity, price, timestamp |
| `news_articles` | Cached news | id, title, source, url, summary, published |
| `research_papers` | Cached arXiv papers | id, title, authors, abstract, url, published |
| `audit_logs` | Security events | id, action, user, details, ip, timestamp |
| `bank_details` | Dummy bank info | id, user_id, account_holder, account_number, sort_code |
| `wallets` | Crypto wallet dummy | id, user_id, wallet_address, wallet_type |

---

## 3. Module-by-Module Breakdown

### 3.1 `main.rs` (48 lines)

The entry point. Does five things in sequence:
1. Initializes `env_logger` (default: `info` level)
2. Creates data directory at `~/.local/share/bloomberg-terminal/`
3. Opens SQLite database + initializes AES-256-GCM crypto
4. Runs the onboarding wizard (stdin/stdout CLI flow)
5. Launches the TUI event loop

Notable choice: everything runs under `#[tokio::main]` so async API calls are available throughout.

### 3.2 `app.rs` (108 lines)

The TUI event loop using crossterm + ratatui:
- Enables raw mode and alternate screen
- Polls for keyboard events every 250ms
- Maintains a `current: Box<dyn Screen>` trait object for the active screen
- `switch_screen()` replaces the current screen based on `ScreenId` enum
- Has a 30-second refresh stub that currently does nothing (timer resets but no `refresh()` call)

### 3.3 `db.rs` (512 lines — largest file)

Full SQLite interface with:
- `Database::new(path)` — opens/creates DB, runs CREATE TABLE IF NOT EXISTS for all 9 tables
- CRUD for users, portfolios, positions, trades, news, papers, audit logs, bank details, wallets
- `Database` wraps `Mutex<Connection>` for interior mutability (safe to share via `Arc`)

### 3.4 `security/encryption.rs` (82 lines)

AES-256-GCM with PBKDF2 key derivation:
- On first run: generates random 32-byte key, saves to `terminal.key` with `0o600` permissions
- On subsequent runs: loads existing key file
- `encrypt()` / `decrypt()` methods are implemented but **not currently called** anywhere
- Password hashing uses PBKDF2 with 600,000 iterations

### 3.5 `security/audit.rs` (11 lines)

A tiny helper that calls `db.log_audit()`. Currently not wired into any code path.

### 3.6 `market/mod.rs` + `yfinance.rs` + `coingecko.rs` (121 lines total)

Data providers:
- **yfinance.rs**: Fetches `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}` via reqwest. Returns `StockQuote { symbol, price, change, change_percent }`.
- **coingecko.rs**: Fetches `https://api.coingecko.com/api/v3/simple/price` for crypto pairs. Returns `CryptoQuote { symbol, price, change_24h }`.
- **mod.rs**: Exports `StockQuote`, `CryptoQuote`, and top-lists functions (`get_top_stocks`, `get_top_crypto`) that return hardcoded watchlists.

### 3.7 `portfolio/mod.rs` + `risk_guard.rs` (176 lines)

The OMS (Order Management System):
- **PortfolioManager**: `buy()` / `sell()` methods that validate via risk guard, then update positions/trades in DB.
- **risk_guard.rs**: 7 sequential checks:
  1. Minimum order value (> $1.00)
  2. Price sanity (0 < price < $1M)
  3. Position concentration (buy ≤ 40% of cash)
  4. Daily loss limit (≤ 5% of cash per symbol per day)
  5. Trade frequency (≤ 10 trades/day per symbol)
  6. Market hours (weekend check active; intraday check commented out)
  7. Circuit breaker (placeholder — `// TODO`)

Uses global `static Mutex` for state tracking — single-user only.

### 3.8 `news/mod.rs` + `rss.rs` + `finnhub.rs` (81 lines)

Two news sources:
- **rss.rs**: Fetches & parses RSS/Atom feeds from Reuters, CNBC, MarketWatch using the `rss` crate. No API key needed.
- **finnhub.rs**: Finnhub REST API client — requires `finnhub_api_key` env var, not actively used.
- **mod.rs**: Currently only calls `rss::fetch_rss()`.

### 3.9 `research/mod.rs` + `arxiv.rs` (56 lines)

arXiv query client:
- Fetches `http://export.arxiv.org/api/query?search_query=cat:q-fin.*&max_results=20`
- Parses Atom XML via `quick-xml` with serde deserialization
- Returns `ResearchPaper { title, authors, abstract, url, published }`

### 3.10 `screens/` (5 files, ~650 lines total)

All screens implement the `Screen` trait:

```rust
pub trait Screen {
    fn draw(&mut self, f: &mut Frame, area: Rect);
    fn handle_key(&mut self, key: KeyEvent) -> Option<AppAction>;
}
```

| Screen | File | Lines | Description |
|--------|------|-------|-------------|
| Market Overview | `market_overview.rs` | 240 | Table of stocks + crypto with buy/sell column, search bar |
| Stock Detail | `stock_detail.rs` | 196 | Quote detail, buy/sell form (Tab to toggle), qty input |
| Portfolio View | `portfolio_view.rs` | 199 | Holdings table + trade history below |
| News Feed | `news_feed.rs` | 94 | Article list with metadata |
| Research | `research.rs` | 89 | Paper list with authors/date |

`AppAction` enum drives screen navigation:
- `Quit` — exit the TUI
- `Back` — return to Market Overview
- `SwitchScreen(ScreenId)` — navigate to any screen
- `None` — no action

### 3.11 `onboarding/wizard.rs` (182 lines)

First-run CLI wizard with 4 phases:
1. **Registration** — Creates demo user (`demo@bloomberg.local` / `Demo1234`)
2. **Bank Details** — Prompts for dummy account info (or auto-fills in demo mode)
3. **Wallet Setup** — Prompts for dummy crypto wallet address
4. **Tutorial** — 8-step interactive walkthrough (blocks on Enter)

In demo mode (no existing user), all steps auto-complete with hardcoded dummy data.

---

## 4. Build & Run Guide

### Prerequisites

- **Rust 1.75+** (install via [rustup](https://rustup.rs))
- **Git**
- A terminal that supports ANSI escape codes (almost all do)

### Quick Install (One Command)

```bash
curl -sSL https://raw.githubusercontent.com/IndrasishRay/secure-bloomberg-terminal-clone/main/install.sh | bash
bloomberg
```

The installer:
1. Installs Rust via rustup if missing
2. Clones the repo to `~/.bloomberg-terminal/`
3. Builds release binary
4. Copies to `~/.local/bin/bloomberg`

### Manual Build

```bash
git clone https://github.com/IndrasishRay/secure-bloomberg-terminal-clone.git
cd secure-bloomberg-terminal-clone
cargo build --release
./target/release/bloomberg-terminal
```

### Runtime

On first run, the terminal:
1. Creates `~/.local/share/bloomberg-terminal/terminal.db` (SQLite)
2. Creates `~/.local/share/bloomberg-terminal/terminal.key` (AES-256 key, 600 perms)
3. Runs the onboarding wizard
4. Launches the TUI with 5 screens

### Key Bindings

| Key | Screen |
|-----|--------|
| `1` | Market Overview |
| `2` | Stock Detail (select a symbol first) |
| `3` | Portfolio View |
| `4` | News Feed |
| `5` | Research Papers |
| `q` or `Esc` | Quit / Go back |
| `Tab` | Toggle Buy/Sell in Stock Detail |
| `0-9` | Quantity input |
| `Enter` | Execute trade |

---

## 5. How to Rebuild This From Scratch

This section is a step-by-step guide for someone who wants to build this exact project from nothing.

### Phase 1: Project Setup

```bash
# Create the project
cargo init secure-bloomberg-terminal-clone --name bloomberg-terminal
cd secure-bloomberg-terminal-clone

# Initialize git
git init
git add .
git commit -m "Initial commit: Secure Bloomberg Terminal Clone"
```

### Phase 2: Dependencies

Add to `Cargo.toml`:

```toml
[dependencies]
# TUI
ratatui = "0.29"              # Terminal UI framework
crossterm = "0.28"            # Raw mode, keyboard input

# Async runtime
tokio = { version = "1", features = ["full"] }

# HTTP client
reqwest = { version = "0.12", features = ["json", "rustls-tls"], default-features = false }

# Database
rusqlite = { version = "0.32", features = ["bundled"] }

# Serialization
serde = { version = "1", features = ["derive"] }
serde_json = "1"

# Time
chrono = { version = "0.4", features = ["serde"] }

# Security / crypto
sha2 = "0.10"
pbkdf2 = "0.12"
aes-gcm = "0.10"
rand = "0.8"
hex = "0.4"

# RSS / XML
rss = "2"
quick-xml = { version = "0.36", features = ["serialize"] }

# CLI / config
clap = { version = "4", features = ["derive"] }
dirs = "5"
dotenvy = "0.15"

# Error handling
anyhow = "1"
thiserror = "1"

# Logging
log = "0.4"
env_logger = "0.11"
```

### Phase 3: Database Layer (`src/db.rs`)

This is the foundation — everything else reads/writes through it.

**Key decisions:**
- Use `rusqlite` with `bundled` feature (ships its own SQLite, no system dependency)
- Wrap `Connection` in `Mutex` so it can be shared across threads via `Arc<Database>`
- Create 9 tables with `CREATE TABLE IF NOT EXISTS`
- Use `params![]` macro for safe parameterized queries

**Tables to create:**
1. `users` — id, email, password_hash, verified, created_at
2. `portfolios` — id, name, cash_balance, user_id
3. `positions` — id, portfolio_id, symbol, quantity, cost_basis, current_value
4. `trades` — id, portfolio_id, symbol, side, buy/sell, quantity, price, timestamp
5. `news_articles` — id, title, source, url, summary, published
6. `research_papers` — id, title, authors, abstract, url, published
7. `audit_logs` — id, action, user, details, ip, timestamp
8. `bank_details` — id, user_id, account_holder, account_number, sort_code
9. `wallets` — id, user_id, wallet_address, wallet_type

### Phase 4: Security Layer (`src/security/`)

Two files:

**`encryption.rs`** — AES-256-GCM + PBKDF2:
```
On first run:
  1. Generate 32 random bytes (AES-256 key)
  2. Write to terminal.key with 0o600 permissions
  3. On subsequent runs: load the key from this file

For password hashing:
  1. Generate 16-byte salt via OsRng
  2. Run PBKDF2-HMAC-SHA256 with 600,000 iterations
  3. Return salt + hash concatenated as a hex string

For data encryption (optional — not currently wired):
  1. Generate 12-byte nonce
  2. Encrypt via Aes256Gcm::encrypt()
  3. Return nonce || ciphertext (for decrypt: split first 12 bytes)
```

**`audit.rs`** — Simple wrapper around `db.log_audit()`:
```rust
pub fn log_event(db: &Database, action: &str, user: &str, details: &str) -> Result<()> {
    db.log_audit(action, user, details, "127.0.0.1")?;
    Ok(())
}
```

### Phase 5: Market Data Providers (`src/market/`)

Two providers:

**`yfinance.rs`** — Yahoo Finance REST API:
```
GET https://query1.finance.yahoo.com/v8/finance/chart/{symbol}

Response structure:
  chart.result[0].meta.regularMarketPrice
  chart.result[0].meta.previousClose  (to calculate change)

Parse into StockQuote { symbol, price, change, change_percent }
```

**`coingecko.rs`** — CoinGecko API:
```
GET https://api.coingecko.com/api/v3/simple/price?ids={id}&vs_currencies=usd&include_24hr_change=true

Response: { "bitcoin": { "usd": 50000, "usd_24h_change": 2.5 } }
```

**`mod.rs`** — Re-exports + top-lists:
- `get_top_stocks()` — calls yfinance for each symbol in a hardcoded watchlist (AAPL, MSFT, GOOGL, AMZN, etc.)
- `get_top_crypto()` — calls CoinGecko for bitcoin, ethereum, solana, etc.

### Phase 6: Portfolio / OMS (`src/portfolio/`)

**`mod.rs`** — PortfolioManager:
```rust
pub fn buy(&self, symbol, quantity, price) -> Result<Trade>
  1. risk_guard::check_order(portfolio, symbol, quantity, price, "buy")
  2. db.get_position(...)
  3. If exists: update position (avg cost, new qty)
  4. If new: create position
  5. db.update_cash(...) — deduct cost
  6. db.create_trade(...)
  7. return Trade

pub fn sell(&self, symbol, quantity, price) -> Result<Trade>
  // Same flow, but credits cash instead of debiting
```

**`risk_guard.rs`** — 7-layer validation chain:
```rust
pub fn check_order(portfolio, symbol, quantity, price, side) -> Result<()> {
    // 1. Minimum order: quantity * price >= 1.00
    // 2. Price sanity: price > 0 && price < 1_000_000
    // 3. Concentration: buy amount <= 40% of cash_balance
    // 4. Daily loss: per-symbol loss > 5% of cash? block
    // 5. Frequency: > 10 trades/symbol today? block
    // 6. Market hours: weekend? block. 9:30-16:00 ET? uncomment
    // 7. Circuit breaker: placeholder
}
```

Key detail: uses `static Mutex<HashMap>` for tracking trade counts and daily PnL across calls.

### Phase 7: News Ingestion (`src/news/`)

**`rss.rs`** — RSS feed fetcher:
```
FEEDS = [
  ("Reuters", "https://www.reutersagency.com/feed/"),
  ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
  ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories"),
]

For each feed:
  1. reqwest::get(url)
  2. Channel::read_from(<bytes>[..])
  3. Extract items: title, link, description, pub_date
  4. Return Vec<NewsArticle>
```

**`finnhub.rs`** — Alternative news API (requires key):
```
GET https://finnhub.io/api/v1/company-news?symbol={symbol}&from={date}&to={date}&token={api_key}
```

### Phase 8: Research Ingestion (`src/research/`)

**`arxiv.rs`** — arXiv API via Atom XML:
```
GET http://export.arxiv.org/api/query?search_query=cat:q-fin.*&max_results=20

Parse Atom feed with quick-xml serde:
  struct Feed { entries: Vec<Entry> }
  struct Entry { title, authors: Vec<Author>, summary, id, published }
  struct Author { name }
```

### Phase 9: TUI Screens (`src/screens/`)

Define the `Screen` trait:

```rust
pub trait Screen {
    fn draw(&mut self, f: &mut Frame, area: Rect);
    fn handle_key(&mut self, key: KeyEvent) -> Option<AppAction>;
}
```

**Common approach for each screen:**
1. Pick widget(s): `Table`, `Paragraph`, `Block`, `List`
2. Build with ratatui's builder pattern
3. Render with `f.render_widget(widget, area)`
4. On key press, map to `AppAction`

**AppAction enum:**
```rust
pub enum AppAction {
    Quit,
    Back,
    SwitchScreen(ScreenId),
    None,
}

pub enum ScreenId {
    MarketOverview,
    StockDetail(String),  // carries symbol
    Portfolio,
    News,
    Research,
}
```

### Phase 10: Onboarding Wizard (`src/onboarding/wizard.rs`)

A simple stdin/stdout CLI flow (not TUI — keeps it simple):

```
1. Registration: prompt email + password, store via db.create_user()
2. Email verification: show "code" on screen, any input = verified
3. Bank details: prompt account holder, number, sort code
4. Wallet setup: prompt wallet address + type
5. Tutorial: 8-step Enter-to-continue walkthrough
```

In demo mode (no existing user), everything auto-fills.

### Phase 11: App Loop (`src/app.rs`)

```rust
pub struct App {
    db: Arc<Database>,
    current: Box<dyn Screen>,
    portfolio_id: i64,
}

pub async fn run(&mut self) -> Result<()> {
    // 1. enable_raw_mode + EnterAlternateScreen
    // 2. Terminal::new(CrosstermBackend::new(stdout))
    // 3. Loop:
    //    a. terminal.draw(|f| self.current.draw(f, f.area()))
    //    b. event::poll(250ms) for keyboard
    //    c. On key: self.current.handle_key(key) -> AppAction
    //    d. Handle action (Quit, Back, SwitchScreen)
    // 4. On Quit: disable_raw_mode + LeaveAlternateScreen
}
```

### Phase 12: Entry Point (`src/main.rs`)

```rust
#[tokio::main]
async fn main() -> Result<()> {
    env_logger::init();
    let data_dir = dirs::data_dir().unwrap().join("bloomberg-terminal");
    let db = Arc::new(Database::new(&data_dir.join("terminal.db"))?);
    let crypto = Crypto::new(&data_dir.join("terminal.key"))?;

    if !run_onboarding(&db, &crypto)? { return Ok(()); }

    let mut app = App::new(db);
    app.run().await?;
    Ok(())
}
```

### Phase 13: Install Script (`install.sh`)

A self-contained installer that:
1. Installs Rust via rustup if missing
2. Clones the repo with `--depth=1`
3. Runs `cargo build --release`
4. Places the binary in `~/.local/bin/bloomberg`
5. Adds PATH hint if needed

---

## 6. Design Decisions & Tradeoffs

### Why Rust?
The original prototype was Python (textual + fastapi + yfinance). Rust was chosen for the rewrite because:
- **Startup time**: Python cold start is ~0.5-2s; Rust is instant (~5ms)
- **Single binary**: No `pip install`, no venv, no dependency resolution at runtime
- **Memory safety**: Zero-cost abstractions with guaranteed safety
- **Async ecosystem**: tokio + reqwest is production-grade for concurrent API calls

### Why SQLite (rusqlite)?
- Bundled (no system install needed)
- Single-file database that lives at `~/.local/share/bloomberg-terminal/terminal.db`
- Good enough for single-user prototype; would need PostgreSQL for multi-user

### Why `Mutex<Connection>` instead of `r2d2` pool?
- Single-user app; connection pooling adds complexity with zero benefit
- `Arc<Database>` shared across screens is simple and works

### Why PBKDF2 instead of argon2?
- argon2 requires a C library (or pure-Rust `argon2` crate with longer compile times)
- PBKDF2 is available directly from the `pbkdf2` crate with zero extra deps
- 600K iterations provides adequate protection for a prototype

### Why not encrypt the database?
- The `encrypt()`/`decrypt()` methods exist but are not wired in
- The key file exists and is protected at `0o600`
- On the roadmap: full database-at-rest encryption

### Why static `Mutex` globals in RiskGuard?
- Simplicity: no need to pass state through the PortfolioManager
- Limitation: single-user only. Two users would share trade counts.
- Acceptable tradeoff for a prototype.

---

## 7. Known Issues & Stubs

| Location | Issue | Impact |
|----------|-------|--------|
| `app.rs:97-100` | 30-second refresh loop is a no-op | Screens never fetch live data after initial load |
| `risk_guard.rs:84` | Market hours check is commented out | Trades allowed at any time |
| `risk_guard.rs:88` | Circuit breaker is `// TODO` | No emergency stop mechanism |
| `risk_guard.rs:45-51` | Daily loss limit may not correctly track per-symbol PnL | Loss limit may not trigger correctly |
| `screens/market_overview.rs:30` | `refresh()` never called from event loop | Market data shown as empty/static |
| `screens/stock_detail.rs:38` | `refresh()` never called | Stock detail shows no current price |
| `news/mod.rs` | Only RSS is wired; Finnhub is unused | No Finnhub news option |
| `encryption.rs` | `encrypt()`/`decrypt()` methods never called | DB contents stored as plaintext |
| `wizard.rs` | Demo user creation has logic conflict | Demo user created twice in some paths |

**Root cause**: The screens were written before the event loop was finalized. The `refresh()` methods exist on all screens but were never wired into the tick cycle. This is the #1 thing to fix.

---

## 8. Roadmap

### Short-term (MVP)
- [ ] Wire `screen.refresh()` into the TUI event loop's tick timer
- [ ] Uncomment market hours check in risk_guard.rs
- [ ] Implement circuit breaker (check for >20% portfolio drop)
- [ ] Fix daily loss limit PnL tracking
- [ ] Wire encryption into DB writes (encrypt sensitive fields)

### Medium-term
- [ ] Replace static Mutex globals with per-portfolio state
- [ ] Add charts (ratatui sparklines for price history)
- [ ] Add configuration via `clap` CLI args (API keys, data dir, etc.)
- [ ] Multi-portfolio support
- [ ] Watchlist customization

### Long-term
- [ ] WebSocket streaming for real-time prices
- [ ] Backtesting engine
- [ ] Multi-user with actual auth
- [ ] WASM build for browser-based terminal

---

## Appendix: Quick Reference

### Useful Commands

```bash
# Build
cargo build
cargo build --release

# Check (fast, no binary output)
cargo check

# Run
cargo run --release
./target/release/bloomberg-terminal

# Clean
cargo clean

# Update dependencies
cargo update

# Show dependency tree
cargo tree
```

### File Structure (Reference)

```
src/
├── main.rs                   # Entry point
├── app.rs                    # TUI event loop
├── db.rs                     # SQLite database (9 tables)
├── market/
│   ├── mod.rs                # StockQuote, CryptoQuote, top-lists
│   ├── yfinance.rs           # Yahoo Finance REST client
│   └── coingecko.rs          # CoinGecko REST client
├── portfolio/
│   ├── mod.rs                # PortfolioManager (buy/sell)
│   └── risk_guard.rs         # 7-layer risk checks
├── news/
│   ├── mod.rs                # News aggregation entry
│   ├── rss.rs                # RSS feed parser
│   └── finnhub.rs            # Finnhub API client
├── research/
│   ├── mod.rs                # Research paper re-export
│   └── arxiv.rs              # arXiv Atom feed parser
├── security/
│   ├── mod.rs                # Module declarations
│   ├── encryption.rs         # AES-256-GCM + PBKDF2
│   └── audit.rs              # Audit log helper
├── screens/
│   ├── mod.rs                # Screen trait + AppAction + ScreenId
│   ├── market_overview.rs    # Screen 1
│   ├── stock_detail.rs       # Screen 2
│   ├── portfolio_view.rs     # Screen 3
│   ├── news_feed.rs          # Screen 4
│   └── research.rs           # Screen 5
└── onboarding/
    ├── mod.rs                # Module declaration
    └── wizard.rs             # CLI setup wizard
```
