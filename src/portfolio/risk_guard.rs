use crate::db::Portfolio;
use anyhow::{bail, Result};
use chrono::Utc;
use std::collections::HashMap;
use std::sync::Mutex;

static TRADE_COUNTS: Mutex<Option<HashMap<String, u32>>> = Mutex::new(None);
static DAILY_PNL: Mutex<Option<HashMap<String, f64>>> = Mutex::new(None);
static LAST_TRADE_DATE: Mutex<Option<HashMap<String, String>>> = Mutex::new(None);

pub fn check_order(portfolio: &Portfolio, symbol: &str, quantity: f64, price: f64, side: &str) -> Result<()> {
    let total = quantity * price;
    let today = Utc::now().format("%Y-%m-%d").to_string();

    // 1. Minimum order
    if total < 1.0 {
        bail!("minimum order is $1.00");
    }

    // 2. Price sanity
    if price <= 0.0 || price > 1_000_000.0 {
        bail!("price out of range: {price:.2}");
    }

    // 3. Position concentration (buy only)
    if side == "buy" && portfolio.cash_balance > 0.0 {
        let concentration = total / portfolio.cash_balance * 100.0;
        if concentration > 40.0 {
            bail!("position would be {concentration:.0}% of portfolio (max 40%)");
        }
    }

    // 4. Daily loss limit
    {
        let mut pnl_lock = DAILY_PNL.lock().unwrap();
        let pnl = pnl_lock.get_or_insert_with(HashMap::new);
        let mut date_lock = LAST_TRADE_DATE.lock().unwrap();
        let dates = date_lock.get_or_insert_with(HashMap::new);
        let date_entry = dates.entry(symbol.to_string()).or_insert_with(|| today.clone());
        if *date_entry != today {
            pnl.insert(symbol.to_string(), 0.0);
            *date_entry = today.clone();
        }
        let entry = pnl.entry(symbol.to_string()).or_insert(0.0);
        if side == "sell" {
            let loss = (price - portfolio.cash_balance).min(0.0).abs() * quantity;
            *entry += loss;
            if *entry > portfolio.cash_balance * 0.05 {
                bail!("daily loss limit reached (5% of portfolio)");
            }
        }
    }

    // 5. Trade frequency
    {
        let mut counts_lock = TRADE_COUNTS.lock().unwrap();
        let counts = counts_lock.get_or_insert_with(HashMap::new);
        let mut date_lock = LAST_TRADE_DATE.lock().unwrap();
        let dates = date_lock.get_or_insert_with(HashMap::new);
        let date_entry = dates.entry(symbol.to_string()).or_insert_with(|| today.clone());
        if *date_entry != today {
            counts.insert(symbol.to_string(), 0);
            *date_entry = today.clone();
        }
        let count = counts.entry(symbol.to_string()).or_insert(0);
        if *count >= 10 {
            bail!("max 10 trades/day per symbol");
        }
        *count += 1;
    }

    // 6. Market hours (rough check — 9:30-16:00 ET weekdays)
    let now = Utc::now();
    let weekday = now.format("%u").to_string().parse::<u8>().unwrap_or(0);
    if weekday > 5 && cfg!(not(debug_assertions)) {
        bail!("markets closed on weekends");
    }
    let hour = now.format("%H").to_string().parse::<u8>().unwrap_or(0);
    let min = now.format("%M").to_string().parse::<u8>().unwrap_or(0);
    let minutes = (hour * 60 + min) as i32;
    let et_minutes = minutes - 300;
    if cfg!(not(debug_assertions)) && (et_minutes < 570 || et_minutes > 960) {
        bail!("markets closed (9:30-16:00 ET)");
    }

    // 7. Circuit breaker: prevent orders if portfolio is down >20% from initial
    // Uses a simple static tracker for demo purposes
    {
        use std::sync::OnceLock;
        static INITIAL_CAPITAL: OnceLock<f64> = OnceLock::new();
        let initial = INITIAL_CAPITAL.get_or_init(|| portfolio.cash_balance);
        let current = portfolio.cash_balance;
        if *initial > 0.0 && current < *initial * 0.8 {
            bail!("circuit breaker: portfolio down >20% from initial capital");
        }
    }

    Ok(())
}
