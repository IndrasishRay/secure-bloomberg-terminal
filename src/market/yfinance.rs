use crate::market::StockQuote;
use anyhow::Result;
use serde_json::Value;

pub async fn get_quote(symbol: &str) -> Result<StockQuote> {
    let url = format!("https://query1.finance.yahoo.com/v8/finance/chart/{symbol}");
    let resp = reqwest::get(&url).await?;
    let data: Value = resp.json().await?;
    let result = &data["chart"]["result"][0];
    let meta = &result["meta"];
    let quote = &result["indicators"]["quote"][0];

    let price = meta["regularMarketPrice"].as_f64().unwrap_or(0.0);
    let prev = meta["chartPreviousClose"].as_f64().unwrap_or(price);
    let open = quote["open"][0].as_f64().unwrap_or(0.0);
    let high = quote["high"][0].as_f64().unwrap_or(0.0);
    let low = quote["low"][0].as_f64().unwrap_or(0.0);
    let volume = quote["volume"][0].as_u64().unwrap_or(0);
    let change = price - prev;
    let change_pct = if prev != 0.0 {
        (change / prev) * 100.0
    } else {
        0.0
    };

    Ok(StockQuote {
        symbol: symbol.to_uppercase(),
        price: (price * 100.0).round() / 100.0,
        change: (change * 100.0).round() / 100.0,
        change_pct: (change_pct * 100.0).round() / 100.0,
        volume,
        high: (high * 100.0).round() / 100.0,
        low: (low * 100.0).round() / 100.0,
        open: (open * 100.0).round() / 100.0,
        prev_close: (prev * 100.0).round() / 100.0,
        name: symbol.to_string(),
    })
}
