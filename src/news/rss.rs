use crate::db::NewsArticle;
use anyhow::Result;

const FEEDS: &[(&str, &str)] = &[
    ("Reuters", "https://www.investing.com/rss/news.rss"),
    ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories"),
];

pub async fn fetch_rss() -> Result<Vec<NewsArticle>> {
    let mut articles = Vec::new();
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .build()?;

    for &(source, url) in FEEDS {
        if let Ok(resp) = client.get(url).send().await {
            if let Ok(body) = resp.text().await {
                if let Ok(channel) = body.parse::<rss::Channel>() {
                    for item in channel.items().iter().take(10) {
                        articles.push(NewsArticle {
                            id: 0,
                            title: item.title().unwrap_or("").to_string(),
                            source: source.to_string(),
                            url: item.link().unwrap_or("").to_string(),
                            summary: item.description().unwrap_or("").to_string(),
                            published_at: item.pub_date().map(|d| d.to_string()),
                        });
                    }
                }
            }
        }
    }

    Ok(articles)
}
