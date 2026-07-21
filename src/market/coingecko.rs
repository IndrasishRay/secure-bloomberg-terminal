use crate::market::CryptoQuote;
use anyhow::Result;
use serde_json::Value;

pub async fn get_quote(symbol: &str) -> Result<CryptoQuote> {
    let url = format!("https://api.coingecko.com/api/v3/coins/{symbol}?localization=false&tickers=false&community_data=false&developer_data=false");
    let resp = reqwest::get(&url).await?;
    let data: Value = resp.json().await?;

    let market_data = &data["market_data"];
    let price = market_data["current_price"]["usd"].as_f64().unwrap_or(0.0);
    let change_pct = market_data["price_change_percentage_24h"].as_f64().unwrap_or(0.0);
    let market_cap = market_data["market_cap"]["usd"].as_f64().unwrap_or(0.0);
    let volume = market_data["total_volume"]["usd"].as_f64().unwrap_or(0.0);
    let name = data["name"].as_str().unwrap_or(symbol).to_string();

    Ok(CryptoQuote {
        symbol: data["symbol"].as_str().unwrap_or(symbol).to_uppercase(),
        name,
        price: (price * 100.0).round() / 100.0,
        change_pct: (change_pct * 100.0).round() / 100.0,
        market_cap: (market_cap * 100.0).round() / 100.0,
        volume: (volume * 100.0).round() / 100.0,
    })
}
