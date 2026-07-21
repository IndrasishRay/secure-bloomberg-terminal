pub mod yfinance;
pub mod coingecko;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StockQuote {
    pub symbol: String,
    pub price: f64,
    pub change: f64,
    pub change_pct: f64,
    pub volume: u64,
    pub high: f64,
    pub low: f64,
    pub open: f64,
    pub prev_close: f64,
    pub name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CryptoQuote {
    pub symbol: String,
    pub name: String,
    pub price: f64,
    pub change_pct: f64,
    pub market_cap: f64,
    pub volume: f64,
}

pub async fn get_stock_quote(symbol: &str) -> anyhow::Result<StockQuote> {
    yfinance::get_quote(symbol).await
}

pub async fn get_crypto_quote(symbol: &str) -> anyhow::Result<CryptoQuote> {
    coingecko::get_quote(symbol).await
}

pub async fn get_top_stocks() -> Vec<StockQuote> {
    let symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ"];
    let mut quotes = Vec::new();
    for sym in &symbols {
        if let Ok(q) = get_stock_quote(sym).await {
            quotes.push(q);
        }
    }
    quotes
}

pub async fn get_top_crypto() -> Vec<CryptoQuote> {
    let symbols = ["bitcoin", "ethereum", "solana", "cardano", "polkadot", "chainlink", "avalanche", "polygon"];
    let mut quotes = Vec::new();
    for sym in &symbols {
        if let Ok(q) = get_crypto_quote(sym).await {
            quotes.push(q);
        }
    }
    quotes
}
