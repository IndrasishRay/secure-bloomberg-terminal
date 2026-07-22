use crate::db::NewsArticle;
use anyhow::Result;

pub async fn fetch_news(api_key: &str) -> Result<Vec<NewsArticle>> {
    let url = format!("https://finnhub.io/api/v1/news?category=general&token={api_key}");
    let resp = reqwest::get(&url).await?;
    let items: Vec<serde_json::Value> = resp.json().await?;

    let articles = items
        .into_iter()
        .take(30)
        .map(|item| NewsArticle {
            id: 0,
            title: item["headline"].as_str().unwrap_or("").to_string(),
            source: item["source"].as_str().unwrap_or("Finnhub").to_string(),
            url: item["url"].as_str().unwrap_or("").to_string(),
            summary: item["summary"].as_str().unwrap_or("").to_string(),
            published_at: item["datetime"].as_i64().map(|ts| {
                let dt = chrono::DateTime::from_timestamp(ts, 0).unwrap_or_default();
                dt.format("%Y-%m-%d %H:%M:%S").to_string()
            }),
        })
        .collect();

    Ok(articles)
}
