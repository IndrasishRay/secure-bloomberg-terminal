pub mod coingecko;
pub mod yfinance;

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
    let symbols = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ",
    ];
    let mut quotes = Vec::new();
    for sym in &symbols {
        if let Ok(q) = get_stock_quote(sym).await {
            quotes.push(q);
        }
    }
    quotes
}

pub async fn get_top_crypto() -> Vec<CryptoQuote> {
    let symbols = [
        "bitcoin",
        "ethereum",
        "solana",
        "cardano",
        "polkadot",
        "chainlink",
        "avalanche",
        "polygon",
    ];
    let mut quotes = Vec::new();
    for sym in &symbols {
        if let Ok(q) = get_crypto_quote(sym).await {
            quotes.push(q);
        }
    }
    quotes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_stock_quote_serde_roundtrip() {
        let q = StockQuote {
            symbol: "AAPL".into(),
            price: 150.25,
            change: 1.50,
            change_pct: 1.01,
            volume: 50_000_000,
            high: 152.00,
            low: 149.00,
            open: 149.50,
            prev_close: 148.75,
            name: "Apple Inc.".into(),
        };
        let json = serde_json::to_string(&q).unwrap();
        let deserialized: StockQuote = serde_json::from_str(&json).unwrap();
        assert_eq!(q.symbol, deserialized.symbol);
        assert!((q.price - deserialized.price).abs() < 1e-10);
        assert_eq!(q.volume, deserialized.volume);
        assert_eq!(q.name, deserialized.name);
    }

    #[test]
    fn test_crypto_quote_serde_roundtrip() {
        let q = CryptoQuote {
            symbol: "BTC".into(),
            name: "Bitcoin".into(),
            price: 67_000.0,
            change_pct: 2.5,
            market_cap: 1_320_000_000_000.0,
            volume: 45_000_000_000.0,
        };
        let json = serde_json::to_string(&q).unwrap();
        let deserialized: CryptoQuote = serde_json::from_str(&json).unwrap();
        assert_eq!(q.symbol, deserialized.symbol);
        assert!((q.price - deserialized.price).abs() < 1e-10);
        assert_eq!(q.market_cap as u64, deserialized.market_cap as u64);
    }

    #[test]
    fn test_stock_quote_negative_change() {
        let q = StockQuote {
            symbol: "TSLA".into(),
            price: 200.00,
            change: -5.00,
            change_pct: -2.44,
            volume: 30_000_000,
            high: 210.00,
            low: 198.00,
            open: 208.00,
            prev_close: 205.00,
            name: "Tesla Inc.".into(),
        };
        assert!(q.change < 0.0);
        assert!(q.change_pct < 0.0);
        let json = serde_json::to_string(&q).unwrap();
        let deserialized: StockQuote = serde_json::from_str(&json).unwrap();
        assert!(deserialized.change < 0.0);
    }

    #[test]
    fn test_stock_quote_zero_values() {
        let q = StockQuote {
            symbol: "ZERO".into(),
            price: 0.0,
            change: 0.0,
            change_pct: 0.0,
            volume: 0,
            high: 0.0,
            low: 0.0,
            open: 0.0,
            prev_close: 0.0,
            name: "Zero Corp".into(),
        };
        assert_eq!(q.price, 0.0);
        assert_eq!(q.volume, 0);
    }

    #[test]
    fn test_top_stocks_list_length() {
        let symbols = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ",
        ];
        assert_eq!(symbols.len(), 10);
    }

    #[test]
    fn test_top_crypto_list_length() {
        let symbols = [
            "bitcoin",
            "ethereum",
            "solana",
            "cardano",
            "polkadot",
            "chainlink",
            "avalanche",
            "polygon",
        ];
        assert_eq!(symbols.len(), 8);
    }
}
