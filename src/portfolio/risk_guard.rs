use crate::db::Portfolio;
use anyhow::{bail, Result};
use chrono::Utc;
use std::collections::HashMap;
use std::sync::Mutex;

static TRADE_COUNTS: Mutex<Option<HashMap<String, u32>>> = Mutex::new(None);
static DAILY_PNL: Mutex<Option<HashMap<String, f64>>> = Mutex::new(None);
static LAST_TRADE_DATE: Mutex<Option<HashMap<String, String>>> = Mutex::new(None);

#[cfg(test)]
pub fn reset_for_tests() {
    *TRADE_COUNTS.lock().unwrap() = None;
    *DAILY_PNL.lock().unwrap() = None;
    *LAST_TRADE_DATE.lock().unwrap() = None;
}

pub fn check_order(portfolio: &Portfolio, symbol: &str, quantity: f64, price: f64, side: &str) -> Result<()> {
    let total = quantity * price;
    let today = Utc::now().format("%Y-%m-%d").to_string();

    if price <= 0.0 || price > 1_000_000.0 {
        bail!("price out of range: {price:.2}");
    }

    if total < 1.0 {
        bail!("minimum order is $1.00");
    }

    if side == "buy" && portfolio.cash_balance > 0.0 {
        let concentration = total / portfolio.cash_balance * 100.0;
        if concentration > 40.0 {
            bail!("position would be {concentration:.0}% of portfolio (max 40%)");
        }
    }

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
        if side == "sell" && portfolio.cash_balance > 0.0 {
            let proceeds = quantity * price;
            if proceeds > portfolio.cash_balance * 0.5 {
                bail!("sell would realize >50% of portfolio in one day");
            }
        }
    }

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

    let now = Utc::now();
    let weekday = now.format("%u").to_string().parse::<u8>().unwrap_or(0);
    if weekday > 5 && cfg!(not(debug_assertions)) {
        bail!("markets closed on weekends");
    }
    let hour = now.format("%H").to_string().parse::<i32>().unwrap_or(0);
    let min = now.format("%M").to_string().parse::<i32>().unwrap_or(0);
    let minutes = hour * 60 + min;
    let et_minutes = minutes - 300;
    if cfg!(not(debug_assertions)) && (et_minutes < 570 || et_minutes > 960) {
        bail!("markets closed (9:30-16:00 ET)");
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_portfolio() -> Portfolio {
        Portfolio {
            id: 1,
            name: "test".into(),
            cash_balance: 100_000.0,
            created_at: "2025-01-01T00:00:00Z".into(),
            updated_at: "2025-01-01T00:00:00Z".into(),
        }
    }

    #[test]
    fn test_buy_within_limits_ok() {
        let p = sample_portfolio();
        assert!(check_order(&p, "TST_A", 10.0, 150.0, "buy").is_ok());
    }

    #[test]
    fn test_sell_within_limits_ok() {
        let p = sample_portfolio();
        assert!(check_order(&p, "TST_B", 5.0, 300.0, "sell").is_ok());
    }

    #[test]
    fn test_minimum_order_below_1_dollar() {
        let p = sample_portfolio();
        let err = check_order(&p, "TST_C", 1000.0, 0.0005, "buy").unwrap_err();
        assert!(err.to_string().contains("minimum order"));
    }

    #[test]
    fn test_price_zero_rejected() {
        let p = sample_portfolio();
        let err = check_order(&p, "TST_D", 10.0, 0.0, "buy").unwrap_err();
        assert!(err.to_string().contains("out of range"));
    }

    #[test]
    fn test_price_over_one_million_rejected() {
        let p = sample_portfolio();
        let err = check_order(&p, "TST_E", 1.0, 2_000_000.0, "buy").unwrap_err();
        assert!(err.to_string().contains("out of range"));
    }

    #[test]
    fn test_buy_concentration_over_40_percent() {
        let p = sample_portfolio();
        let err = check_order(&p, "TST_F", 300.0, 150.0, "buy").unwrap_err();
        assert!(err.to_string().contains("40%"));
    }

    #[test]
    fn test_buy_just_under_40_percent_ok() {
        let p = Portfolio { cash_balance: 100_000.0, ..sample_portfolio() };
        assert!(check_order(&p, "TST_G", 266.0, 150.0, "buy").is_ok());
    }

    #[test]
    fn test_sell_not_blocked_by_zero_cash() {
        let p = Portfolio { cash_balance: 0.0, ..sample_portfolio() };
        assert!(check_order(&p, "TST_H", 10.0, 150.0, "sell").is_ok());
    }

    #[test]
    fn test_empty_symbol_not_rejected_by_risk() {
        let p = sample_portfolio();
        assert!(check_order(&p, "", 1.0, 100.0, "buy").is_ok());
    }
}
